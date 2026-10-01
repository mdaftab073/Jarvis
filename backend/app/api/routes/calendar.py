from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.student_scope import require_record_owner, require_student_scope
from app.db.models import CalendarEvent
from app.schemas.student_os import CalendarEventInput
from app.services.calendar_service import create_event, delete_event, get_agenda, get_events, get_week_agenda, update_event
from app.services.time_service import utc_now_naive

router = APIRouter()


@router.get("/calendar/{student_id}/today")
def today_agenda(student_id: int, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    return get_agenda(db, student_id, utc_now_naive().date())


@router.get("/calendar/{student_id}/tomorrow")
def tomorrow_agenda(student_id: int, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    return get_agenda(db, student_id, utc_now_naive().date() + timedelta(days=1))


@router.get("/calendar/{student_id}/week")
def week_agenda(student_id: int, start_date: date | None = None, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    return get_week_agenda(db, student_id, start_date)


@router.get("/calendar/{student_id}")
def read_calendar(student_id: int, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    return get_events(db, student_id)


@router.post("/calendar/{student_id}")
def add_calendar_event(student_id: int, payload: CalendarEventInput, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    try:
        return create_event(db, student_id, payload.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.put("/calendar/events/{event_id}")
def edit_calendar_event(event_id: int, payload: CalendarEventInput, request: Request, db: Session = Depends(get_db)):
    existing = db.query(CalendarEvent).filter_by(id=event_id).first()
    if existing is not None:
        require_record_owner(request, existing.student_id)
    try:
        event = update_event(db, event_id, payload.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if event is None:
        raise HTTPException(status_code=404, detail="Calendar event not found")
    return event


@router.delete("/calendar/events/{event_id}")
def remove_calendar_event(event_id: int, request: Request, db: Session = Depends(get_db)):
    existing = db.query(CalendarEvent).filter_by(id=event_id).first()
    if existing is not None:
        require_record_owner(request, existing.student_id)
    if not delete_event(db, event_id):
        raise HTTPException(status_code=404, detail="Calendar event not found")
    return {"deleted": True}
