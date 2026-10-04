import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.database import Base
import app.db.models  # noqa: F401
from app.jobs.registry import JobRegistry, recover_stale_jobs
from app.jobs.worker_state import get_worker_health
from app.models.job_execution import JobExecution
from app.models.worker_heartbeat import WorkerHeartbeat
from app.workers.job_worker import JobWorker


class JobWorkerTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.registry = JobRegistry()
        self.registry.register_job("worker.test", lambda payload: payload)
        self.session_patcher = patch(
            "app.jobs.registry.SessionLocal",
            side_effect=lambda: Session(self.engine),
        )
        self.audit_patcher = patch("app.jobs.registry.AuditLogService.record_event_isolated")
        self.session_patcher.start()
        self.audit_patcher.start()

    def tearDown(self):
        self.audit_patcher.stop()
        self.session_patcher.stop()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_worker_startup_resumes_pending_jobs(self):
        completed = []

        def handle(payload):
            completed.append(payload["value"])
            worker.request_shutdown()
            return {"processed": payload["value"]}

        self.registry.register_job("worker.startup", handle)
        execution = self.registry.create_execution(
            self.db,
            "worker.startup",
            {"value": 17},
        )
        worker = JobWorker(self.registry, poll_interval_seconds=0.01)

        with (
            patch("app.workers.job_worker.recover_stale_jobs", return_value=0),
            patch("app.workers.job_worker.record_worker_heartbeat"),
        ):
            worker.run()

        self.db.refresh(execution)
        self.assertEqual(completed, [17])
        self.assertEqual(execution.status, "SUCCESS")
        self.assertEqual(execution.result_json, {"processed": 17})

    def test_stale_running_jobs_are_requeued_or_failed_by_retry_count(self):
        stale_retry = JobExecution(
            job_name="worker.test",
            status="RUNNING",
            payload_json={},
            started_at=datetime.utcnow() - timedelta(hours=2),
            last_heartbeat=datetime.utcnow() - timedelta(hours=2),
            retry_count=1,
            max_retries=3,
        )
        stale_exhausted = JobExecution(
            job_name="worker.test",
            status="RUNNING",
            payload_json={},
            started_at=datetime.utcnow() - timedelta(hours=2),
            last_heartbeat=datetime.utcnow() - timedelta(hours=2),
            retry_count=3,
            max_retries=3,
        )
        self.db.add_all([stale_retry, stale_exhausted])
        self.db.commit()

        self.assertEqual(recover_stale_jobs(timeout_minutes=30), 2)

        self.db.refresh(stale_retry)
        self.db.refresh(stale_exhausted)
        self.assertEqual(stale_retry.status, "PENDING")
        self.assertEqual(stale_retry.retry_count, 2)
        self.assertIsNone(stale_retry.finished_at)
        self.assertEqual(stale_exhausted.status, "FAILED")
        self.assertIsNotNone(stale_exhausted.finished_at)

    def test_worker_executes_claimed_queued_job(self):
        values = []
        self.registry.register_job("worker.test.exec", lambda payload: values.append(payload))
        execution = self.registry.create_execution(
            self.db,
            "worker.test.exec",
            {"value": 5},
        )
        worker = JobWorker(self.registry)

        self.assertTrue(worker.run_once())
        self.db.refresh(execution)
        self.assertEqual(values, [{"value": 5}])
        self.assertEqual(execution.status, "SUCCESS")
        self.assertFalse(worker.run_once())

    def test_retry_lifecycle_survives_worker_dispatch(self):
        calls = []

        def retry_once(_payload):
            calls.append(1)
            if len(calls) == 1:
                raise TimeoutError("temporary failure")
            return {"ok": True}

        self.registry.register_job("worker.retry", retry_once)
        execution = self.registry.create_execution(self.db, "worker.retry", {})
        worker = JobWorker(self.registry)

        with patch("app.jobs.registry.time.sleep"):
            self.assertTrue(worker.run_once())

        self.db.refresh(execution)
        self.assertEqual(execution.status, "SUCCESS")
        self.assertEqual(execution.retry_count, 1)
        self.assertEqual(len(calls), 2)

    def test_job_claiming_does_not_return_a_claimed_job_twice(self):
        first = self.registry.create_execution(self.db, "worker.test", {"value": 1})
        second = self.registry.create_execution(self.db, "worker.test", {"value": 2})

        first_claim = self.registry.claim_next_job()
        second_claim = self.registry.claim_next_job()
        third_claim = self.registry.claim_next_job()

        self.assertEqual({first_claim, second_claim}, {first.id, second.id})
        self.assertIsNone(third_claim)

    def test_worker_health_reports_latest_heartbeat_and_pending_jobs(self):
        self.db.add(
            WorkerHeartbeat(
                worker_id="test-worker",
                last_heartbeat=datetime.utcnow(),
            )
        )
        self.registry.create_execution(self.db, "worker.test", {})

        with patch(
            "app.jobs.worker_state.SessionLocal",
            side_effect=lambda: Session(self.engine),
        ):
            health = get_worker_health()

        self.assertEqual(health["status"], "healthy")
        self.assertIsNotNone(health["last_heartbeat"])
        self.assertEqual(health["pending_jobs"], 1)

    def test_shutdown_signal_finishes_the_current_job(self):
        completed = []
        worker = JobWorker(self.registry, poll_interval_seconds=0.01)

        class InFlightRegistry:
            def claim_next_job(self):
                return 123

            def execute_claimed_job(self, job_id):
                completed.append(job_id)
                worker.request_shutdown()

        worker.registry = InFlightRegistry()
        with (
            patch("app.workers.job_worker.recover_stale_jobs", return_value=0),
            patch("app.workers.job_worker.record_worker_heartbeat"),
        ):
            worker.run()

        self.assertEqual(completed, [123])
        self.assertTrue(worker._stop_event.is_set())


if __name__ == "__main__":
    unittest.main()
