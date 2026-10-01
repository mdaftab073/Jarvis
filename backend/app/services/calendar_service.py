from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import CalendarEvent
from app.services.time_service import normalize_utc_naive


def create_event(db: Session, student_id: int, fields: dict) -> CalendarEvent:
    fields = dict(fields)
    fields["start_time"] = normalize_utc_naive(fields["start_time"])
    fields["end_time"] = normalize_utc_naive(fields["end_time"])
    if fields["end_time"] <= fields["start_time"]:
        raise ValueError("end_time must be after start_time")
    event = CalendarEvent(student_id=student_id, **fields)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_events(db: Session, student_id: int, start: datetime | None = None, end: datetime | None = None) -> list[CalendarEvent]:
    query = db.query(CalendarEvent).filter_by(student_id=student_id)
    if start is not None:
        query = query.filter(CalendarEvent.end_time >= normalize_utc_naive(start))
    if end is not None:
        query = query.filter(CalendarEvent.start_time <= normalize_utc_naive(end))
    return query.order_by(CalendarEvent.start_time).all()


def update_event(db: Session, event_id: int, fields: dict) -> CalendarEvent | None:
    event = db.query(CalendarEvent).filter_by(id=event_id).first()
    if event is None:
        return None
    fields = dict(fields)
    for key in ("start_time", "end_time"):
        if key in fields:
            fields[key] = normalize_utc_naive(fields[key])
    for key, value in fields.items():
        setattr(event, key, value)
    if event.end_time <= event.start_time:
        raise ValueError("end_time must be after start_time")
    db.commit()
    db.refresh(event)
    return event


def delete_event(db: Session, event_id: int) -> bool:
    event = db.query(CalendarEvent).filter_by(id=event_id).first()
    if event is None:
        return False
    db.delete(event)
    db.commit()
    return True
