from datetime import timedelta

from app.db.database import SessionLocal
from app.db.models import MISAccount
from app.jobs.registry import register_job
from app.services.mis_sync_service import sync_attendance, sync_profile, sync_results, sync_timetable
from app.services.connector_service import run_sync_job
from app.services.time_service import utc_now_naive


@register_job("sync_mis_resource", "Synchronize one SVNIT MIS resource for a student.")
def sync_mis_resource(payload: dict) -> dict:
    student_id = int(payload["student_id"])
    resource = payload["resource"]
    dispatch = {
        "profile": sync_profile,
        "attendance": sync_attendance,
        "results": sync_results,
        "timetable": sync_timetable,
    }
    if resource not in dispatch:
        raise ValueError("Unsupported MIS sync resource")
    try:
        with SessionLocal() as db:
            profile, count = dispatch[resource](db, student_id)
            account = db.query(MISAccount).filter_by(student_id=student_id).first()
            if account is not None:
                account.last_sync_at = utc_now_naive()
                account.status = "READY"
                db.commit()
            return {"student_id": student_id, "resource": resource, "records_processed": count, "updated_at": profile.updated_at.isoformat()}
    except Exception:
        with SessionLocal() as db:
            account = db.query(MISAccount).filter_by(student_id=student_id).first()
            if account is not None:
                account.status = "ERROR"
                db.commit()
        raise


@register_job("scheduled_mis_sync", "Run scheduled profile, attendance, and result synchronization for enabled MIS accounts.")
def scheduled_mis_sync(_payload: dict) -> dict:
    from app.jobs.registry import execute_registered_job, get_job_registry

    now = utc_now_naive()
    with SessionLocal() as db:
        accounts = db.query(MISAccount).filter(
            MISAccount.enabled.is_(True),
            MISAccount.sync_interval_minutes.is_not(None),
        ).all()
        due_students = {
            account.student_id
            for account in accounts
            if (account.last_sync_at or account.created_at)
            + timedelta(minutes=account.sync_interval_minutes)
            <= now
        }
        student_ids = sorted(due_students)
    completed = 0
    failures = 0
    for student_id in student_ids:
        for resource in ("profile", "attendance", "results"):
            try:
                with SessionLocal() as db:
                    execution = get_job_registry().create_execution(
                        db,
                        "sync_mis_resource",
                        {"student_id": student_id, "resource": resource},
                        student_id,
                    )
                result = execute_registered_job(execution.id)
                if result["status"] == "SUCCESS":
                    completed += 1
                else:
                    failures += 1
            except Exception:
                failures += 1
    return {"students": len(student_ids), "resources_succeeded": completed, "resources_failed": failures}


@register_job("run_connector_sync", "Run a previously queued connector sync and preserve legacy connector history.")
def run_connector_sync(payload: dict) -> dict:
    return run_sync_job(int(payload["sync_job_id"]))