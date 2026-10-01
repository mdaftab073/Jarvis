from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.student_scope import require_student_scope
from app.db.database import get_db
from app.db.models import StudyBlock
from app.schemas.student_os import ScheduleInput, StudyBlockInput
from app.services.scheduler_service import create_study_block, generate_study_schedule

router = APIRouter()


@router.get("/schedule/{student_id}")
def get_schedule(student_id: int, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    return db.query(StudyBlock).filter_by(student_id=student_id).order_by(StudyBlock.start_time).all()


@router.post("/schedule/{student_id}/blocks")
def add_study_block(student_id: int, payload: StudyBlockInput, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    try:
        return create_study_block(db, student_id, payload.model_dump(exclude_none=True))
    except ValueError as error:
        raise HTTPException(status_code=409 if "conflict" in str(error).lower() else 422, detail=str(error)) from error


@router.post("/schedule/{student_id}/generate")
def generate_schedule(student_id: int, payload: ScheduleInput, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    try:
        blocks = generate_study_schedule(db, student_id, payload.subject_ids, payload.start_time, payload.session_length, payload.break_minutes)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return blocks
