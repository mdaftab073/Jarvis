import logging
import time
from datetime import datetime, timedelta
from threading import Event, Thread
from typing import Any, Callable

import httpx
import requests
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.jobs.base import JobDefinition
from app.models.job_execution import JobExecution
from app.services.audit_log_service import AuditLogService
from app.services.time_service import utc_now_naive


logger = logging.getLogger(__name__)
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 60
_JOB_HANDLERS: dict[str, JobDefinition] = {}
job_registry: "JobRegistry"
_tasks_loaded = False

_PUBLIC_PDF_PROCESSING_ERRORS = {
    "Material not found": "The uploaded material could not be found.",
    "No text could be extracted from PDF": (
        "No readable text could be extracted from this PDF, even after OCR."
    ),
    "No chunks could be created from PDF": (
        "The extracted PDF text was too short to index."
    ),
    "OCR for scanned PDFs requires PyMuPDF and Tesseract.": (
        "OCR is not configured for scanned PDFs. Install PyMuPDF and Tesseract."
    ),
    (
        "OCR failed for scanned PDF pages. Verify Tesseract and its "
        "English language data are installed."
    ): "OCR failed. Verify that Tesseract and its English language data are installed.",
}


def _job_error_message(job_name: str, error: Exception) -> str:
    if job_name == "process_pdf_material":
        return _PUBLIC_PDF_PROCESSING_ERRORS.get(str(error), type(error).__name__)
    return type(error).__name__


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
            max_retries=MAX_RETRIES,
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)
        logger.info("Job queued: job_id=%s name=%s student_id=%s", execution.id, name, student_id)
        AuditLogService.record_event_isolated(
            event_type="JOB_QUEUED",
            resource_type="job_execution",
            resource_id=execution.id,
            action="enqueue",
            student_id=student_id,
            metadata_json={"job_name": name},
        )
        return execution

    def claim_next_job(self) -> int | None:
        self._ensure_jobs()
        with SessionLocal() as db:
            execution = (
                db.query(JobExecution)
                .filter(JobExecution.status == "PENDING")
                .order_by(JobExecution.created_at, JobExecution.id)
                .with_for_update(skip_locked=True)
                .first()
            )
            if execution is None:
                return None
            now = utc_now_naive()
            execution.status = "RUNNING"
            execution.started_at = now
            execution.last_heartbeat = now
            execution.queue_time_seconds = max(
                0.0,
                (now - execution.created_at).total_seconds(),
            )
            db.commit()
            logger.info("Worker claimed job: job_id=%s name=%s", execution.id, execution.job_name)
            return execution.id

    def execute_job(self, job_id: int) -> dict:
        return self._execute_job(job_id, claimed=False)

    def execute_claimed_job(self, job_id: int) -> dict:
        return self._execute_job(job_id, claimed=True)

    def _execute_job(self, job_id: int, claimed: bool) -> dict:
        self._ensure_jobs()
        with SessionLocal() as db:
            execution = db.query(JobExecution).filter_by(id=job_id).with_for_update().first()
            if execution is None:
                raise ValueError("Job execution not found")
            if execution.status in {"SUCCESS", "FAILED"} or (
                execution.status == "RUNNING" and not claimed
            ):
                return self.serialize(execution)
            definition = self._definitions.get(execution.job_name)
            if definition is None:
                execution.status = "FAILED"
                execution.error_message = "Job handler is not registered"
                execution.completed_at = datetime.utcnow()
                execution.finished_at = execution.completed_at
                execution.last_heartbeat = execution.completed_at
                db.commit()
                return self.serialize(execution)
            if execution.status != "RUNNING":
                execution.status = "RUNNING"
                execution.started_at = datetime.utcnow()
                execution.last_heartbeat = execution.started_at
                execution.queue_time_seconds = max(
                    0.0,
                    (execution.started_at - execution.created_at).total_seconds(),
                )
            db.commit()
            job_name = execution.job_name
            payload = dict(execution.payload_json or {})
            max_retries = execution.max_retries

        started = time.perf_counter()
        while True:
            heartbeat_stop = Event()
            heartbeat_thread = Thread(
                target=self._heartbeat_loop,
                args=(job_id, heartbeat_stop),
                daemon=True,
            )
            try:
                self._heartbeat(job_id)
                heartbeat_thread.start()
                result = definition.handler(payload)
                heartbeat_stop.set()
                heartbeat_thread.join()
                with SessionLocal() as db:
                    execution = db.query(JobExecution).filter_by(id=job_id).first()
                    if execution is None:
                        raise ValueError("Job execution disappeared while running")
                    execution.status = "SUCCESS"
                    execution.result_json = result if isinstance(result, (dict, list, str, int, float, bool)) else {"result": str(result)}
                    execution.completed_at = datetime.utcnow()
                    execution.finished_at = execution.completed_at
                    execution.last_heartbeat = execution.finished_at
                    execution.duration_seconds = round(time.perf_counter() - started, 4)
                    execution.error_message = None
                    execution.error_details = None
                    db.commit()
                    db.refresh(execution)
                    logger.info("Job completed: job_id=%s name=%s", job_id, job_name)
                    AuditLogService.record_event_isolated(
                        event_type="JOB_COMPLETED",
                        resource_type="job_execution",
                        resource_id=job_id,
                        action="complete",
                        student_id=execution.student_id,
                        metadata_json={"job_name": job_name, "duration_seconds": execution.duration_seconds, "status": "SUCCESS"},
                    )
                    return self.serialize(execution)
            except Exception as error:
                heartbeat_stop.set()
                if heartbeat_thread.is_alive():
                    heartbeat_thread.join()
                logger.exception("Job attempt failed: job_id=%s name=%s", job_id, job_name)
                retry_scheduled = False
                with SessionLocal() as db:
                    execution = db.query(JobExecution).filter_by(id=job_id).first()
                    if execution is None:
                        raise
                    retryable = _is_retryable_failure(error)
                    if retryable and execution.retry_count < max_retries:
                        execution.retry_count += 1
                        retry_number = execution.retry_count
                        execution.last_heartbeat = datetime.utcnow()
                        db.commit()
                        delay = RETRY_BACKOFF_SECONDS * (2 ** (retry_number - 1))
                        retry_scheduled = True
                        logger.warning(
                            "Retrying job: job_id=%s name=%s retry=%s/%s delay_seconds=%s",
                            job_id,
                            job_name,
                            retry_number,
                            max_retries,
                            delay,
                        )
                    else:
                        execution.status = "FAILED"
                        execution.error_message = _job_error_message(job_name, error)
                        execution.completed_at = datetime.utcnow()
                        execution.finished_at = execution.completed_at
                        execution.last_heartbeat = execution.finished_at
                        execution.duration_seconds = round(time.perf_counter() - started, 4)
                        execution.error_details = {
                            "type": type(error).__name__,
                            "message": str(error)[:500],
                        }
                        db.commit()
                        db.refresh(execution)
                        AuditLogService.record_event_isolated(
                            event_type="JOB_FAILED",
                            resource_type="job_execution",
                            resource_id=job_id,
                            action="fail",
                            student_id=execution.student_id,
                            metadata_json={
                                "job_name": job_name,
                                "error_type": type(error).__name__,
                                "duration_seconds": execution.duration_seconds,
                            },
                        )
                        return self.serialize(execution)
                if retry_scheduled:
                    time.sleep(delay)

    def _heartbeat(self, job_id: int) -> None:
        with SessionLocal() as db:
            execution = db.query(JobExecution).filter_by(id=job_id).first()
            if execution is not None and execution.status == "RUNNING":
                execution.last_heartbeat = datetime.utcnow()
                db.commit()

    def _heartbeat_loop(self, job_id: int, stop: Event) -> None:
        while not stop.wait(30):
            try:
                self._heartbeat(job_id)
            except Exception:
                logger.exception("Could not update job heartbeat: job_id=%s", job_id)

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
            "finished_at": execution.finished_at,
            "last_heartbeat": execution.last_heartbeat,
            "ended_at": execution.finished_at or execution.completed_at,
            "queue_time_seconds": execution.queue_time_seconds,
            "duration_seconds": execution.duration_seconds,
            "retry_count": execution.retry_count,
            "max_retries": execution.max_retries,
            "error_message": execution.error_message,
            "error_details": execution.error_details,
        }

    def _ensure_jobs(self) -> None:
        global _tasks_loaded
        if self is job_registry and not _tasks_loaded:
            from app.jobs.tasks import analytics, pdf_processing, reminders  # noqa: F401

            for definition in _JOB_HANDLERS.values():
                self.register_job(definition.name, definition.handler, definition.description)
            _tasks_loaded = True


job_registry = JobRegistry()


def _is_retryable_failure(error: Exception) -> bool:
    causes = []
    pending = [error]
    seen = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        causes.append(current)
        if current.__cause__ is not None:
            pending.append(current.__cause__)
        if current.__context__ is not None:
            pending.append(current.__context__)

    if any(isinstance(cause, FileNotFoundError) for cause in causes):
        return False
    for cause in causes:
        if isinstance(
            cause,
            (
                ConnectionError,
                TimeoutError,
                requests.ConnectionError,
                requests.Timeout,
                httpx.NetworkError,
                httpx.TimeoutException,
            ),
        ):
            return True
        if isinstance(cause, requests.HTTPError):
            status_code = cause.response.status_code if cause.response else None
            if status_code == 429 or status_code is not None and status_code >= 500:
                return True
        if isinstance(cause, httpx.HTTPStatusError):
            status_code = cause.response.status_code
            if status_code == 429 or status_code >= 500:
                return True
    return False


def recover_stale_jobs(timeout_minutes: int = 30) -> int:
    cutoff = utc_now_naive() - timedelta(minutes=timeout_minutes)
    with SessionLocal() as db:
        stale_jobs = (
            db.query(JobExecution)
            .filter(
                JobExecution.status == "RUNNING",
                (
                    (JobExecution.last_heartbeat < cutoff)
                    | (
                        JobExecution.last_heartbeat.is_(None)
                        & (JobExecution.started_at < cutoff)
                    )
                ),
            )
            .with_for_update(skip_locked=True)
            .all()
        )
        recovered_at = utc_now_naive()
        for execution in stale_jobs:
            exhausted = execution.retry_count >= execution.max_retries
            if not exhausted:
                execution.retry_count += 1
                execution.status = "PENDING"
                execution.started_at = None
                execution.completed_at = None
                execution.finished_at = None
            else:
                execution.status = "FAILED"
                execution.completed_at = recovered_at
                execution.finished_at = recovered_at
            execution.error_message = "Job was interrupted after its heartbeat timed out"
            execution.error_details = {"type": "JobTimeout"}
            execution.last_heartbeat = recovered_at
        db.commit()
        if stale_jobs:
            logger.warning(
                "Recovered stale jobs: count=%s timeout_minutes=%s",
                len(stale_jobs),
                timeout_minutes,
            )
        return len(stale_jobs)


def get_job_registry() -> JobRegistry:
    job_registry._ensure_jobs()
    return job_registry


def execute_registered_job(job_id: int) -> dict:
    return get_job_registry().execute_job(job_id)