import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.logging import JSONFormatter, reset_log_context, set_log_context
from app.db.database import Base, get_db
from app.db.models import Student
from app.main import app
from app.models.audit_log import AuditLog
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.job_execution import JobExecution
from app.services.metrics_service import JobMetricsService, MetricsService
from app.services.chat_service import process_chat
from app.tools.exceptions import ToolExecutionError
from app.tools.base import BaseTool
from app.tools.registry import ToolRegistry
from scripts.validate_production import validate_endpoint, validate_rate_limit


class PhaseGTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.student = Student(name="Phase G Student", email="phase-g@example.com")
        self.db.add(self.student)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_job_metrics_include_rate_duration_and_active_counts(self):
        self.db.add_all([
            JobExecution(job_name="ok", status="SUCCESS", duration_seconds=2.0),
            JobExecution(job_name="bad", status="FAILED", duration_seconds=4.0),
            JobExecution(job_name="running", status="RUNNING"),
        ])
        self.db.commit()

        result = JobMetricsService.summarize(self.db)
        self.assertEqual(result["active"], 1)
        self.assertEqual(result["success_rate"], 0.5)
        self.assertEqual(result["failure_rate"], 0.5)
        self.assertEqual(result["average_duration_seconds"], 3.0)

    def test_metrics_summary_counts_persisted_entities_and_audit_events(self):
        session = ChatSession(student_id=self.student.id, title="session")
        self.db.add(session)
        self.db.flush()
        self.db.add(ChatMessage(session_id=session.id, role="user", content="content"))
        self.db.add(AuditLog(event_type="TOOL_EXECUTION", resource_type="tool", action="execute", student_id=self.student.id, metadata_json={"success": True}))
        self.db.commit()

        result = MetricsService.summary(self.db)
        self.assertEqual(result["total_users"], 1)
        self.assertEqual(result["total_sessions"], 1)
        self.assertEqual(result["total_chat_messages"], 1)
        self.assertEqual(result["total_tool_executions"], 1)

    def test_chat_audit_references_messages_without_copying_content(self):
        director = Mock()
        director.process_message.return_value = {
            "answer": "A private answer.",
            "agent_used": "director",
            "tool_used": None,
            "metadata": {},
        }
        process_chat(self.db, self.student.id, "A private question", director=director)

        events = self.db.query(AuditLog).all()
        self.assertEqual(
            {event.event_type for event in events},
            {"CHAT_SESSION_CREATED", "CHAT_MESSAGE_SUBMITTED", "CHAT_AGENT_SELECTED"},
        )
        self.assertTrue(all("content" not in event.metadata_json for event in events))

    def test_health_liveness_does_not_require_dependencies(self):
        client = TestClient(app)
        response = client.get("/health/live")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "alive"})

    def test_health_readiness_reports_unhealthy_dependencies(self):
        with patch("app.api.routes.health.dependency_status", return_value={"database": "error"}):
            response = TestClient(app).get("/health/ready")
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json()["ready"])

    def test_admin_metrics_endpoint_requires_configured_token(self):
        original = settings.METRICS_ADMIN_TOKEN
        settings.METRICS_ADMIN_TOKEN = "test-admin-token"
        try:
            def override_get_db():
                yield self.db

            app.dependency_overrides[get_db] = override_get_db
            client = TestClient(app)
            self.assertEqual(client.get("/api/metrics/summary").status_code, 403)
            response = client.get("/api/metrics/summary", headers={"X-Admin-Token": "test-admin-token"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["total_users"], 1)
        finally:
            settings.METRICS_ADMIN_TOKEN = original
            app.dependency_overrides.clear()

    def test_tool_execution_audit_runs_once_per_concurrent_call(self):
        class ConcurrentTool(BaseTool):
            name = "concurrent-test"
            async def execute(self, payload):
                await asyncio.sleep(0)
                return {"ok": True}

        registry = ToolRegistry([ConcurrentTool()])
        with patch("app.tools.registry.AuditLogService.record_event_isolated", return_value=True) as audit:
            async def run():
                await asyncio.gather(*[
                    registry.execute_tool_async("concurrent-test", {"student_id": self.student.id})
                    for _ in range(4)
                ])

            asyncio.run(run())
        self.assertEqual(audit.call_count, 4)
        self.assertTrue(all(call.kwargs["metadata_json"]["success"] for call in audit.call_args_list))

    def test_failed_tool_execution_is_audited(self):
        class FailedTool(BaseTool):
            name = "failed-test"
            async def execute(self, payload):
                raise RuntimeError("tool failed")

        registry = ToolRegistry([FailedTool()])
        with patch("app.tools.registry.AuditLogService.record_event_isolated", return_value=True) as audit:
            with self.assertRaises(ToolExecutionError):
                asyncio.run(registry.execute_tool_async("failed-test", {"student_id": self.student.id}))
        metadata = audit.call_args.kwargs["metadata_json"]
        self.assertFalse(metadata["success"])
        self.assertEqual(metadata["error_type"], "RuntimeError")

    def test_concurrent_chat_requests_keep_sessions_and_answers_isolated(self):
        with TemporaryDirectory() as directory:
            concurrent_engine = create_engine(f"sqlite:///{directory}/chat.db")
            Base.metadata.create_all(concurrent_engine)
            with Session(concurrent_engine) as setup_db:
                student = Student(name="Concurrent Student", email="concurrent-chat@example.com")
                setup_db.add(student)
                setup_db.commit()
                student_id = student.id

            def submit(message):
                with Session(concurrent_engine) as db:
                    director = Mock()
                    director.process_message.return_value = {
                        "answer": f"answer:{message}",
                        "agent_used": "director",
                        "tool_used": None,
                        "metadata": {},
                    }
                    return process_chat(db, student_id, message, director=director)

            try:
                with ThreadPoolExecutor(max_workers=2) as executor:
                    responses = list(executor.map(submit, ("first", "second")))
                self.assertEqual({response.answer for response in responses}, {"answer:first", "answer:second"})
                self.assertEqual(len({response.session_id for response in responses}), 2)
            finally:
                concurrent_engine.dispose()

    def test_logging_context_and_production_validation_primitives(self):
        tokens = set_log_context("request-1", "correlation-1")
        try:
            record = logging.LogRecord("test", logging.INFO, __file__, 1, "test", (), None)
            encoded = JSONFormatter().format(record)
        finally:
            reset_log_context(tokens)
        self.assertIn('"request_id": "request-1"', encoded)
        self.assertIn('"correlation_id": "correlation-1"', encoded)
        self.assertTrue(validate_rate_limit("30/minute"))
        self.assertFalse(validate_rate_limit("30/fortnight"))

    def test_production_validator_rejects_http_success_without_readiness(self):
        response = Mock()
        response.status = 200
        response.read.return_value = b'{"status":"not_ready","ready":false}'
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        with patch("scripts.validate_production.urlopen", return_value=response):
            self.assertFalse(validate_endpoint("http://localhost", "/health/ready")[0])


if __name__ == "__main__":
    unittest.main()