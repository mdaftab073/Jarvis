from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.db.models import AttendanceRecord, DeadlineItem, StudentAcademicProfile, StudentNotification
from app.services.time_service import utc_now_naive


def create_notification(db: Session, student_id: int, title: str, message: str, notification_type: str = "INFO") -> StudentNotification:
    item = StudentNotification(student_id=student_id, title=title, message=message, notification_type=notification_type)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_notifications(db: Session, student_id: int, unread_only: bool = False) -> list[StudentNotification]:
    query = db.query(StudentNotification).filter_by(student_id=student_id)
    if unread_only:
        query = query.filter(StudentNotification.read.is_(False))
    return query.order_by(StudentNotification.created_at.desc()).all()


def mark_notification_read(db: Session, notification_id: int) -> StudentNotification | None:
    item = db.query(StudentNotification).filter_by(id=notification_id).first()
    if item is not None:
        item.read = True
        db.commit()
        db.refresh(item)
    return item


def generate_alerts(db: Session, student_id: int, now: datetime | None = None) -> list[StudentNotification]:
    now = now or utc_now_naive()
    alerts = []
    existing = {
        (item.title, item.message)
        for item in list_notifications(db, student_id, unread_only=False)
    }
    profile = db.query(StudentAcademicProfile).filter_by(student_id=student_id).first()
    if profile:
        low = db.query(AttendanceRecord).filter(
            AttendanceRecord.academic_profile_id == profile.id,
            AttendanceRecord.attendance_percentage < 75,
        ).all()
        for record in low:
            message = f"Subject {record.subject_id} attendance is {record.attendance_percentage:.1f}%."
            if ("Attendance warning", message) not in existing:
                alerts.append(create_notification(db, student_id, "Attendance warning", message, "WARNING"))
        due = db.query(DeadlineItem).filter(
            DeadlineItem.academic_profile_id == profile.id,
            DeadlineItem.is_completed.is_(False),
            DeadlineItem.due_date >= now,
            DeadlineItem.due_date <= now + timedelta(days=3),
        ).all()
        for item in due:
            message = f"{item.title} is due {item.due_date.isoformat()}."
            if ("Upcoming deadline", message) not in existing:
                alerts.append(create_notification(db, student_id, "Upcoming deadline", message, "REMINDER"))
    return alerts
