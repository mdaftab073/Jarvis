from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.student_scope import require_record_owner, require_student_scope
from app.db.models import DeadlineItem
from app.schemas.student_os import DeadlineCompletionInput, DeadlineInput
from app.services.deadline_service import create_deadline, list_deadlines, overdue_deadlines, serialize_deadline, set_deadline_completed, upcoming_deadlines

router = APIRouter()


@router.get("/deadlines/{student_id}")
def get_student_deadlines(student_id: int, include_completed: bool = False, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    return [serialize_deadline(item) for item in list_deadlines(db, student_id, include_completed)]


@router.get("/deadlines/{student_id}/upcoming")
def get_upcoming_deadlines(student_id: int, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    return [serialize_deadline(item) for item in upcoming_deadlines(db, student_id)]


@router.get("/deadlines/{student_id}/overdue")
def get_overdue_deadlines(student_id: int, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    return [serialize_deadline(item) for item in overdue_deadlines(db, student_id)]


@router.post("/deadlines/{student_id}")
def add_deadline(student_id: int, payload: DeadlineInput, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    try:
        return serialize_deadline(create_deadline(db, student_id, payload.model_dump()))
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.patch("/deadlines/{deadline_id}/complete")
def complete_deadline(deadline_id: int, payload: DeadlineCompletionInput, request: Request, db: Session = Depends(get_db)):
    existing = db.query(DeadlineItem).filter_by(id=deadline_id).first()
    if existing is not None:
        require_record_owner(request, existing.student_id)
    item = set_deadline_completed(db, deadline_id, payload.completed)
    if item is None:
        raise HTTPException(status_code=404, detail="Deadline not found")
    return serialize_deadline(item)
