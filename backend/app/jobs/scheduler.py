import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings


logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler(timezone="UTC")


def _enqueue_and_run(job_name: str, payload: dict | None = None) -> None:
    from app.db.database import SessionLocal
    from app.jobs.registry import get_job_registry

    with SessionLocal() as db:
        get_job_registry().create_execution(db, job_name, payload or {})


def start_scheduler() -> None:
    if not settings.BACKGROUND_JOBS_ENABLED or scheduler.running:
        return
    from app.jobs.registry import get_job_registry

    get_job_registry()
    scheduler.add_job(
        _enqueue_and_run,
        "interval",
        id="reminder_generation",
        args=["generate_reminders", {"all_students": True}],
        seconds=settings.REMINDER_JOB_INTERVAL_SECONDS,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        _enqueue_and_run,
        "interval",
        id="analytics_refresh",
        args=["refresh_analytics", {"all_students": True}],
        seconds=settings.ANALYTICS_JOB_INTERVAL_SECONDS,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info("Background scheduler started")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")