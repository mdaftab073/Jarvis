from sqlalchemy.orm import Session

from app.jobs.registry import get_job_registry
from app.models.job_execution import JobExecution


def enqueue_job(
    db: Session,
    job_name: str,
    payload: dict,
    student_id: int | None = None,
) -> JobExecution:
    return get_job_registry().create_execution(db, job_name, payload, student_id)


def get_job_status(db: Session, job_id: int, student_id: int) -> JobExecution | None:
    return db.query(JobExecution).filter_by(id=job_id, student_id=student_id).first()


def get_job_execution(db: Session, job_id: int) -> JobExecution | None:
    return db.query(JobExecution).filter_by(id=job_id).first()