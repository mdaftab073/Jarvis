from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.db.models import CalendarEvent, DeadlineItem, Reminder, StudyBlock
from app.services.time_service import normalize_utc_naive
from app.services.time_service import utc_now_naive


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


def get_agenda(db: Session, student_id: int, agenda_date: date) -> dict:
    start = datetime.combine(agenda_date, datetime.min.time())
    end = start + timedelta(days=1)
    items = []
    for event in db.query(CalendarEvent).filter(
        CalendarEvent.student_id == student_id,
        CalendarEvent.start_time < end,
        CalendarEvent.end_time > start,
    ).all():
        items.append({"kind": "CALENDAR", "title": event.title, "start_time": event.start_time, "end_time": event.end_time, "event_type": event.event_type, "id": event.id})
    for block in db.query(StudyBlock).filter(
        StudyBlock.student_id == student_id,
        StudyBlock.start_time < end,
        StudyBlock.end_time > start,
    ).all():
        items.append({"kind": "STUDY_BLOCK", "title": block.title or "Study block", "start_time": block.start_time, "end_time": block.end_time, "event_type": block.block_type, "subject_id": block.subject_id, "completed": block.completed, "id": block.id})
    for deadline in db.query(DeadlineItem).filter(
        DeadlineItem.student_id == student_id,
        DeadlineItem.completed.is_(False),
        DeadlineItem.due_date >= start,
        DeadlineItem.due_date < end,
    ).all():
        items.append({"kind": "DEADLINE", "title": deadline.title, "start_time": deadline.due_date, "end_time": None, "event_type": deadline.type, "priority": deadline.priority, "id": deadline.id})
    for reminder in db.query(Reminder).filter(
        Reminder.student_id == student_id,
        Reminder.completed.is_(False),
        Reminder.trigger_time >= start,
        Reminder.trigger_time < end,
    ).all():
        items.append({"kind": "REMINDER", "title": reminder.title, "start_time": reminder.trigger_time, "end_time": None, "event_type": "REMINDER", "id": reminder.id})
    items.sort(key=lambda item: item["start_time"])
    return {"student_id": student_id, "date": agenda_date, "items": items}


def get_week_agenda(db: Session, student_id: int, week_start: date | None = None) -> dict:
    week_start = week_start or utc_now_naive().date()
    return {
        "student_id": student_id,
        "start_date": week_start,
        "days": [get_agenda(db, student_id, week_start + timedelta(days=offset)) for offset in range(7)],
    }
