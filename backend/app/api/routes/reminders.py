from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.student_scope import require_record_owner, require_student_scope
from app.db.database import get_db
from app.db.models import Reminder
from app.schemas.student_os import ReminderInput
from app.services.reminder_service import create_reminder, delete_reminder, list_reminders, update_reminder

router = APIRouter()


class ReminderUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    trigger_time: datetime | None = None
    completed: bool | None = None


@router.get("/reminders/{student_id}")
def get_student_reminders(
    student_id: int,
    db: Session = Depends(get_db),
    _scope: int = Depends(require_student_scope),
):
    return list_reminders(db, student_id, pending_only=False)


@router.post("/reminders/{student_id}")
def add_student_reminder(
    student_id: int,
    payload: ReminderInput,
    db: Session = Depends(get_db),
    _scope: int = Depends(require_student_scope),
):
    return create_reminder(db, student_id, payload.title, payload.trigger_time)


@router.patch("/reminders/{reminder_id}")
def edit_reminder(reminder_id: int, payload: ReminderUpdate, request: Request, db: Session = Depends(get_db)):
    reminder = db.query(Reminder).filter_by(id=reminder_id).first()
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    require_record_owner(request, reminder.student_id)
    updated = update_reminder(db, reminder_id, payload.model_dump(exclude_unset=True))
    return updated


@router.delete("/reminders/{reminder_id}")
def remove_reminder(reminder_id: int, request: Request, db: Session = Depends(get_db)):
    reminder = db.query(Reminder).filter_by(id=reminder_id).first()
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    require_record_owner(request, reminder.student_id)
    delete_reminder(db, reminder_id)
    return {"deleted": True}
