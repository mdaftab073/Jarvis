import unittest
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from fastapi import APIRouter

from app.api.rate_limit import limiter
from app.api.student_scope import require_student_scope
from app.core.config import settings
from app.db.database import Base
from app.db.database import get_db
from app.db.models import Course, Student, Subject
from app.jobs.registry import JobRegistry
from app.models.job_execution import JobExecution
from app.services import file_service
from app.services.job_service import get_job_status
from app.main import app as api_app
from app.api.routes.flashcards import list_decks
from app.jobs.scheduler import scheduler, start_scheduler, stop_scheduler


class PhaseFTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.student = Student(name="Job Owner", email="phasef@example.com")
        self.other = Student(name="Other Owner", email="phasef-other@example.com")
        self.db.add_all([self.student, self.other])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_job_success_failure_tracking_and_owner_scoped_status(self):
        registry = JobRegistry()
        execution_count = []

        def succeed(payload):
            execution_count.append(payload["value"])
            return {"value": payload["value"]}

        registry.register_job("phasef.success", succeed)
        registry.register_job("phasef.failure", lambda _payload: (_ for _ in ()).throw(RuntimeError("secret")))
        with patch("app.jobs.registry.SessionLocal", side_effect=lambda: Session(self.engine)):
            success = registry.create_execution(self.db, "phasef.success", {"value": 7}, self.student.id)
            success_result = registry.execute_job(success.id)
            failed = registry.create_execution(self.db, "phasef.failure", {}, self.student.id)
            failure_result = registry.execute_job(failed.id)
        self.assertEqual(success_result["status"], "SUCCESS")
        self.assertEqual(success_result["result_json"], {"value": 7})
        self.assertIsNotNone(success_result["started_at"])
        self.assertIsNotNone(success_result["completed_at"])
        self.assertEqual(failure_result["status"], "FAILED")
        self.assertEqual(failure_result["error_message"], "RuntimeError")
        self.assertNotIn("secret", failure_result["error_message"])
        self.assertIsNotNone(get_job_status(self.db, success.id, self.student.id))
        self.assertIsNone(get_job_status(self.db, success.id, self.other.id))
        running = JobExecution(job_name="phasef.success", status="RUNNING", student_id=self.student.id, payload_json={"value": 99})
        self.db.add(running)
        self.db.commit()
        with patch("app.jobs.registry.SessionLocal", side_effect=lambda: Session(self.engine)):
            registry.execute_job(running.id)
        self.assertEqual(execution_count, [7])

    def test_upload_rejects_wrong_mime_bad_signature_and_oversize(self):
        with TemporaryDirectory() as directory:
            original_dir = file_service.UPLOAD_DIR
            file_service.UPLOAD_DIR = Path(directory)
            valid = SimpleNamespace(filename="../notes.pdf", content_type="application/pdf", file=BytesIO(b"%PDF-1.7\nbody"))
            saved = file_service.save_uploaded_file(valid, self.student.id)
            self.assertTrue(Path(saved).is_file())
            self.assertEqual(Path(saved).name, f"{Path(saved).stem}.pdf")

            wrong_mime = SimpleNamespace(filename="notes.pdf", content_type="text/plain", file=BytesIO(b"%PDF-1.7"))
            with self.assertRaises(HTTPException) as wrong_type_error:
                file_service.save_uploaded_file(wrong_mime, self.student.id)
            self.assertEqual(wrong_type_error.exception.status_code, 400)

            invalid = SimpleNamespace(filename="fake.pdf", content_type="application/pdf", file=BytesIO(b"not a pdf"))
            with self.assertRaises(HTTPException) as invalid_error:
                file_service.save_uploaded_file(invalid, self.student.id)
            self.assertEqual(invalid_error.exception.status_code, 400)

            with patch.object(settings, "MAX_UPLOAD_SIZE_BYTES", 8):
                oversized = SimpleNamespace(filename="large.pdf", content_type="application/pdf", file=BytesIO(b"%PDF-1.7 more bytes"))
                with self.assertRaises(HTTPException) as size_error:
                    file_service.save_uploaded_file(oversized, self.student.id)
            self.assertEqual(size_error.exception.status_code, 413)
            file_service.UPLOAD_DIR = original_dir

    def test_strict_student_mode_requires_a_trusted_principal(self):
        request = Request({
            "type": "http", "method": "GET", "path": "/api/test", "headers": [],
            "query_string": b"", "server": ("test", 80), "client": ("test", 1),
            "scheme": "http", "state": {},
        })
        with patch.object(settings, "REQUIRE_AUTHENTICATED_STUDENT", True):
            with self.assertRaises(HTTPException) as unauthenticated:
                require_student_scope(self.student.id, request, self.db)
            self.assertEqual(unauthenticated.exception.status_code, 401)
            request.state.student_id = self.student.id
            self.assertEqual(require_student_scope(self.student.id, request, self.db), self.student.id)
            with self.assertRaises(HTTPException) as cross_student:
                require_student_scope(self.other.id, request, self.db)
            self.assertEqual(cross_student.exception.status_code, 403)

    def test_slowapi_limit_returns_429(self):
        test_router = APIRouter()

        @test_router.get("/limited")
        @limiter.limit("1/minute")
        def limited(request: Request):
            return PlainTextResponse("ok")

        app = FastAPI()
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        app.add_middleware(SlowAPIMiddleware)
        app.include_router(test_router)
        client = TestClient(app, client=("phase-f-rate-limit", 5511))
        self.assertEqual(client.get("/limited").status_code, 200)
        self.assertEqual(client.get("/limited").status_code, 429)

    def test_scheduler_lifecycle_starts_and_stops_cleanly(self):
        with patch.object(settings, "BACKGROUND_JOBS_ENABLED", True):
            start_scheduler()
            self.assertTrue(scheduler.running)
            stop_scheduler()
            self.assertFalse(scheduler.running)

    def test_job_status_api_is_student_scoped(self):
        execution = JobExecution(
            job_name="refresh_analytics",
            status="SUCCESS",
            student_id=self.student.id,
            payload_json={},
            result_json={"students_refreshed": 1},
        )
        self.db.add(execution)
        self.db.commit()

        def override_get_db():
            yield self.db

        api_app.dependency_overrides[get_db] = override_get_db
        try:
            client = TestClient(api_app, client=("phase-f-job-status", 5512))
            own = client.get(f"/api/jobs/{execution.id}", params={"student_id": self.student.id})
            other = client.get(f"/api/jobs/{execution.id}", params={"student_id": self.other.id})
            self.assertEqual(own.status_code, 200)
            self.assertEqual(own.json()["status"], "SUCCESS")
            self.assertEqual(other.status_code, 404)
        finally:
            api_app.dependency_overrides.clear()

    def test_flashcard_subject_access_rejects_another_students_scope(self):
        subject = Subject(name="Owned", course=Course(name="CS", student=self.student))
        self.db.add(subject)
        self.db.commit()
        request = Request({
            "type": "http", "method": "GET", "path": "/api/flashcards/decks", "headers": [],
            "query_string": b"", "server": ("test", 80), "client": ("test", 1),
            "scheme": "http", "state": {"student_id": self.other.id},
        })
        with self.assertRaises(HTTPException) as denied:
            list_decks(subject_id=subject.id, request=request, db=self.db)
        self.assertEqual(denied.exception.status_code, 403)

    def test_pdf_upload_queues_processing_and_rejects_subject_scope_mismatch(self):
        subject = Subject(name="Owned", course=Course(name="CS", student=self.student))
        self.db.add(subject)
        self.db.commit()

        def override_get_db():
            yield self.db

        api_app.dependency_overrides[get_db] = override_get_db
        queued = SimpleNamespace(
            id=71,
            job_name="process_pdf_material",
            status="PENDING",
            student_id=self.student.id,
            result_json=None,
            created_at=None,
            started_at=None,
            completed_at=None,
            error_message=None,
        )
        try:
            client = TestClient(api_app, client=("phase-f-pdf-upload", 5513))
            with patch("app.api.routes.study_materials.save_uploaded_file", return_value="uploads/mock.pdf"), patch(
                "app.api.routes.study_materials.enqueue_job", return_value=queued
            ):
                response = client.post(
                    "/api/materials/upload",
                    data={"title": "Notes", "subject_id": str(subject.id), "student_id": str(self.student.id)},
                    files={"file": ("notes.pdf", b"%PDF-1.7 content", "application/pdf")},
                )
            self.assertEqual(response.status_code, 202)
            self.assertEqual(response.json()["processing_job_id"], 71)
            mismatch = client.post(
                "/api/materials/upload",
                data={"title": "Notes", "subject_id": str(subject.id), "student_id": str(self.other.id)},
                files={"file": ("notes.pdf", b"%PDF-1.7 content", "application/pdf")},
            )
            self.assertEqual(mismatch.status_code, 403)
        finally:
            api_app.dependency_overrides.clear()


if __name__ == "__main__":
    unittest.main()