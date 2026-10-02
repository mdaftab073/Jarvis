import logging
from datetime import datetime
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.jobs.base import JobDefinition
from app.models.job_execution import JobExecution


logger = logging.getLogger(__name__)
_JOB_HANDLERS: dict[str, JobDefinition] = {}
job_registry: "JobRegistry"
_tasks_loaded = False


def register_job(name: str, description: str = ""):
    def decorator(handler: Callable[[dict[str, Any]], Any]):
        if name in _JOB_HANDLERS:
            raise ValueError(f"Job already registered: {name}")
        _JOB_HANDLERS[name] = JobDefinition(name=name, handler=handler, description=description)
        return handler

    return decorator


class JobRegistry:
    def __init__(self):
        self._definitions: dict[str, JobDefinition] = {}

    def register_job(self, name: str, handler: Callable[[dict[str, Any]], Any], description: str = "") -> None:
        if not name:
            raise ValueError("Registered jobs must define a name")
        if name in self._definitions:
            raise ValueError(f"Job already registered: {name}")
        self._definitions[name] = JobDefinition(name, handler, description)

    def create_execution(
        self,
        db: Session,
        name: str,
        payload: dict[str, Any] | None = None,
        student_id: int | None = None,
    ) -> JobExecution:
        self._ensure_jobs()
        if name not in self._definitions:
            raise KeyError(f"Job not registered: {name}")
        execution = JobExecution(
            job_name=name,
            status="PENDING",
            student_id=student_id,
            payload_json=payload or {},
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)
        logger.info("Job queued: job_id=%s name=%s student_id=%s", execution.id, name, student_id)
        return execution

    def execute_job(self, job_id: int) -> dict:
        self._ensure_jobs()
        with SessionLocal() as db:
            execution = db.query(JobExecution).filter_by(id=job_id).with_for_update().first()
            if execution is None:
                raise ValueError("Job execution not found")
            if execution.status in {"RUNNING", "SUCCESS", "FAILED"}:
                return self.serialize(execution)
            definition = self._definitions.get(execution.job_name)
            if definition is None:
                execution.status = "FAILED"
                execution.error_message = "Job handler is not registered"
                execution.completed_at = datetime.utcnow()
                db.commit()
                return self.serialize(execution)
            execution.status = "RUNNING"
            execution.started_at = datetime.utcnow()
            db.commit()
            job_name = execution.job_name
            payload = dict(execution.payload_json or {})

        try:
            result = definition.handler(payload)
            with SessionLocal() as db:
                execution = db.query(JobExecution).filter_by(id=job_id).first()
                if execution is None:
                    raise ValueError("Job execution disappeared while running")
                execution.status = "SUCCESS"
                execution.result_json = result if isinstance(result, (dict, list, str, int, float, bool)) else {"result": str(result)}
                execution.completed_at = datetime.utcnow()
                execution.error_message = None
                db.commit()
                db.refresh(execution)
                logger.info("Job completed: job_id=%s name=%s", job_id, job_name)
                return self.serialize(execution)
        except Exception as error:
            logger.exception("Job failed: job_id=%s name=%s", job_id, job_name)
            with SessionLocal() as db:
                execution = db.query(JobExecution).filter_by(id=job_id).first()
                if execution is None:
                    raise
                execution.status = "FAILED"
                execution.error_message = type(error).__name__
                execution.completed_at = datetime.utcnow()
                db.commit()
                db.refresh(execution)
                return self.serialize(execution)

    def list_jobs(self) -> list[dict[str, str]]:
        self._ensure_jobs()
        return [
            {"name": definition.name, "description": definition.description}
            for definition in self._definitions.values()
        ]

    @staticmethod
    def serialize(execution: JobExecution) -> dict:
        return {
            "id": execution.id,
            "job_name": execution.job_name,
            "status": execution.status,
            "student_id": execution.student_id,
            "payload_json": execution.payload_json,
            "result_json": execution.result_json,
            "created_at": execution.created_at,
            "started_at": execution.started_at,
            "completed_at": execution.completed_at,
            "error_message": execution.error_message,
        }

    def _ensure_jobs(self) -> None:
        global _tasks_loaded
        if self is job_registry and not _tasks_loaded:
            from app.jobs.tasks import analytics, mis_sync, pdf_processing, reminders  # noqa: F401

            for definition in _JOB_HANDLERS.values():
                self.register_job(definition.name, definition.handler, definition.description)
            _tasks_loaded = True


job_registry = JobRegistry()


def get_job_registry() -> JobRegistry:
    job_registry._ensure_jobs()
    return job_registry


def execute_registered_job(job_id: int) -> dict:
    return get_job_registry().execute_job(job_id)