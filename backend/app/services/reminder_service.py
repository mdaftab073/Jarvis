from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.db.models import DeadlineItem, Reminder, StudentAcademicProfile
from app.services.time_service import normalize_utc_naive, utc_now_naive


def create_reminder(db: Session, student_id: int, title: str, trigger_time: datetime) -> Reminder:
    trigger_time = normalize_utc_naive(trigger_time)
    reminder = Reminder(student_id=student_id, title=title, trigger_time=trigger_time)
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


def update_reminder(db: Session, reminder_id: int, fields: dict) -> Reminder | None:
    reminder = db.query(Reminder).filter_by(id=reminder_id).first()
    if reminder is None:
        return None
    for key, value in fields.items():
        if key in {"title", "trigger_time", "completed"}:
            setattr(reminder, key, value)
    db.commit()
    db.refresh(reminder)
    return reminder


def delete_reminder(db: Session, reminder_id: int) -> bool:
    reminder = db.query(Reminder).filter_by(id=reminder_id).first()
    if reminder is None:
        return False
    db.delete(reminder)
    db.commit()
    return True


def list_reminders(db: Session, student_id: int, pending_only: bool = True) -> list[Reminder]:
    query = db.query(Reminder).filter_by(student_id=student_id)
    if pending_only:
        query = query.filter(Reminder.completed.is_(False))
    return query.order_by(Reminder.trigger_time).all()


def generate_reminders(db: Session, student_id: int, now: datetime | None = None) -> list[Reminder]:
    now = normalize_utc_naive(now or utc_now_naive())
    profile = db.query(StudentAcademicProfile).filter_by(student_id=student_id).first()
    if profile is None:
        return []
    due_items = db.query(DeadlineItem).filter(
        DeadlineItem.academic_profile_id == profile.id,
        DeadlineItem.is_completed.is_(False),
        DeadlineItem.due_date >= now,
        DeadlineItem.due_date <= now + timedelta(days=7),
    ).all()
    created = []
    existing = {(r.title.removeprefix("Due soon: "), r.trigger_time) for r in list_reminders(db, student_id, pending_only=False)}
    for item in due_items:
        trigger = max(item.due_date - timedelta(days=1), now)
        if (item.title, trigger) not in existing:
            created.append(Reminder(student_id=student_id, title=f"Due soon: {item.title}", trigger_time=trigger))
    if created:
        db.add_all(created)
        db.commit()
        for reminder in created:
            db.refresh(reminder)
    return created
