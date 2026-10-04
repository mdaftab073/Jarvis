from datetime import timedelta

from sqlalchemy import func

from app.core.config import settings
from app.db.database import SessionLocal
from app.models.job_execution import JobExecution
from app.models.worker_heartbeat import WorkerHeartbeat
from app.services.time_service import utc_now_naive


def record_worker_heartbeat(worker_id: str) -> None:
    with SessionLocal() as db:
        now = utc_now_naive()
        heartbeat = db.query(WorkerHeartbeat).filter_by(worker_id=worker_id).first()
        if heartbeat is None:
            heartbeat = WorkerHeartbeat(worker_id=worker_id, last_heartbeat=now)
            db.add(heartbeat)
        else:
            heartbeat.last_heartbeat = now
        db.commit()


def get_worker_health() -> dict:
    with SessionLocal() as db:
        last_heartbeat = db.query(func.max(WorkerHeartbeat.last_heartbeat)).scalar()
        pending_jobs = db.query(func.count(JobExecution.id)).filter(
            JobExecution.status == "PENDING"
        ).scalar()

    heartbeat_timeout = max(settings.WORKER_HEARTBEAT_INTERVAL_SECONDS * 3, 60)
    healthy = (
        last_heartbeat is not None
        and last_heartbeat >= utc_now_naive() - timedelta(seconds=heartbeat_timeout)
    )
    return {
        "status": "healthy" if healthy else "unhealthy",
        "last_heartbeat": last_heartbeat.isoformat() if last_heartbeat else None,
        "pending_jobs": pending_jobs,
    }
