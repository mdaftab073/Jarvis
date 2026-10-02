from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.jobs.registry import execute_registered_job, get_job_registry
from app.models.job_execution import JobExecution


def enqueue_job(
    db: Session,
    background_tasks: BackgroundTasks,
    job_name: str,
    payload: dict,
    student_id: int | None = None,
) -> JobExecution:
    execution = get_job_registry().create_execution(db, job_name, payload, student_id)
    background_tasks.add_task(execute_registered_job, execution.id)
    return execution


def get_job_status(db: Session, job_id: int, student_id: int) -> JobExecution | None:
    return db.query(JobExecution).filter_by(id=job_id, student_id=student_id).first()


def get_job_execution(db: Session, job_id: int) -> JobExecution | None:
    return db.query(JobExecution).filter_by(id=job_id).first()