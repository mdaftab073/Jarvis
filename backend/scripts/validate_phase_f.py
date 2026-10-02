from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from io import BytesIO

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.rate_limit import limiter
from app.api.student_scope import require_student_scope
from app.core.config import settings
from app.db.database import Base
from app.db.models import Student
from app.jobs.registry import get_job_registry
from app.models.job_execution import JobExecution
from app.services import file_service


def main():
    required_jobs = {"process_pdf_material", "sync_mis_resource", "generate_reminders", "generate_student_alerts", "refresh_analytics"}
    registered = {job["name"] for job in get_job_registry().list_jobs()}
    missing = required_jobs - registered
    if missing:
        raise SystemExit(f"Missing job handlers: {', '.join(sorted(missing))}")
    if "job_executions" not in Base.metadata.tables:
        raise SystemExit("JobExecution table is not registered")
    if limiter is None or not settings.CHAT_RATE_LIMIT or not settings.RAG_RATE_LIMIT:
        raise SystemExit("Rate limiter is not configured")

    from app.jobs.registry import JobRegistry
    from unittest.mock import patch

    engine = create_engine("sqlite://")
    Student.__table__.create(engine)
    JobExecution.__table__.create(engine)
    registry = JobRegistry()
    registry.register_job("validation.noop", lambda payload: {"ok": payload.get("ok", True)})
    with Session(engine) as db:
        student = Student(name="Validation Student", email="phase-f-validation@example.com")
        db.add(student)
        db.commit()
        execution = registry.create_execution(db, "validation.noop", {"ok": True}, student.id)
        with patch("app.jobs.registry.SessionLocal", side_effect=lambda: Session(engine)):
            result = registry.execute_job(execution.id)
        if result["status"] != "SUCCESS" or result["result_json"] != {"ok": True}:
            raise SystemExit("Background job execution failed")
        if not callable(require_student_scope):
            raise SystemExit("Student ownership guard is unavailable")
        from app.services.job_service import get_job_status

        if get_job_status(db, execution.id, student.id) is None:
            raise SystemExit("Job ownership lookup failed")
    engine.dispose()

    with TemporaryDirectory() as directory:
        original = file_service.UPLOAD_DIR
        file_service.UPLOAD_DIR = Path(directory)
        try:
            uploaded = SimpleNamespace(
                filename="validation.pdf",
                content_type="application/pdf",
                file=BytesIO(b"%PDF-1.7\nvalidation"),
            )
            stored = file_service.save_uploaded_file(uploaded, 1)
            if not Path(stored).is_file():
                raise SystemExit("PDF validation/storage failed")
        except HTTPException as error:
            raise SystemExit(f"PDF validation failed: {error.detail}") from error
        finally:
            file_service.UPLOAD_DIR = original

    print(f"Phase F validation passed: {len(registered)} jobs, job model, upload validation, rate limiter")


if __name__ == "__main__":
    main()