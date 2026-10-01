from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import DeadlineItem, StudentAcademicProfile
from app.services.ownership_service import require_subject_owner, student_owned_query
from app.services.time_service import utc_now_naive

_PRIORITY = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}


def serialize_deadline(item: DeadlineItem) -> dict:
    return {
        "id": item.id,
        "student_id": item.student_id,
        "subject_id": item.subject_id,
        "title": item.title,
        "description": item.description,
        "type": item.type,
        "due_date": item.due_date,
        "priority": item.priority,
        "completed": item.completed,
    }


def create_deadline(db: Session, student_id: int, fields: dict) -> DeadlineItem:
    require_subject_owner(db, student_id, fields.get("subject_id"))
    profile = db.query(StudentAcademicProfile).filter_by(student_id=student_id).first()
    if profile is None:
        raise ValueError("Academic profile not found")
    mapped = dict(fields)
    mapped["academic_profile_id"] = profile.id
    mapped["student_id"] = student_id
    item = DeadlineItem(**mapped)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_deadlines(db: Session, student_id: int, include_completed: bool = False) -> list[DeadlineItem]:
    query = student_owned_query(db, DeadlineItem, student_id)
    if not include_completed:
        query = query.filter(DeadlineItem.is_completed.is_(False))
    return query.all()


def upcoming_deadlines(db: Session, student_id: int, now: datetime | None = None) -> list[DeadlineItem]:
    now = now or utc_now_naive()
    items = [d for d in list_deadlines(db, student_id) if d.due_date >= now]
    return sorted(items, key=lambda d: (-_PRIORITY.get(d.priority, 0), d.due_date))


def overdue_deadlines(db: Session, student_id: int, now: datetime | None = None) -> list[DeadlineItem]:
    now = now or utc_now_naive()
    return [d for d in list_deadlines(db, student_id) if d.due_date < now]


def set_deadline_completed(db: Session, deadline_id: int, completed: bool) -> DeadlineItem | None:
    item = db.query(DeadlineItem).filter_by(id=deadline_id).first()
    if item is None:
        return None
    item.is_completed = completed
    item.completed_at = utc_now_naive() if completed else None
    db.commit()
    db.refresh(item)
    return item


def update_deadline(db: Session, deadline_id: int, fields: dict) -> DeadlineItem | None:
    item = db.query(DeadlineItem).filter_by(id=deadline_id).first()
    if item is None:
        return None
    for key, value in fields.items():
        if key in {"title", "description", "type", "due_date", "priority", "completed"}:
            setattr(item, key, value)
    item.completed_at = utc_now_naive() if item.completed else None
    db.commit()
    db.refresh(item)
    return item


def delete_deadline(db: Session, deadline_id: int) -> bool:
    item = db.query(DeadlineItem).filter_by(id=deadline_id).first()
    if item is None:
        return False
    db.delete(item)
    db.commit()
    return True
