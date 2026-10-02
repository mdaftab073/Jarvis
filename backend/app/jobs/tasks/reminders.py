from app.db.database import SessionLocal
from app.db.models import Student
from app.jobs.registry import register_job
from app.services.notification_service import generate_alerts
from app.services.reminder_service import generate_reminders


@register_job("generate_reminders", "Generate reminders from upcoming deadlines.")
def generate_reminder_job(payload: dict) -> dict:
    with SessionLocal() as db:
        if payload.get("all_students"):
            student_ids = [student_id for (student_id,) in db.query(Student.id).all()]
        else:
            student_ids = [int(payload["student_id"])]
        generated = 0
        alerts = 0
        for student_id in student_ids:
            generated += len(generate_reminders(db, student_id))
            alerts += len(generate_alerts(db, student_id))
        return {"students_processed": len(student_ids), "reminders_generated": generated, "alerts_generated": alerts}


@register_job("generate_student_alerts", "Generate academic notifications for one student.")
def generate_student_alerts(payload: dict) -> dict:
    with SessionLocal() as db:
        created = generate_alerts(db, int(payload["student_id"]))
        return {"student_id": int(payload["student_id"]), "alerts_generated": len(created)}