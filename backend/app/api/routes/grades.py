from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.student_scope import require_student_scope
from app.db.database import get_db
from app.db.models import GradeRecord
from app.schemas.student_os import GradeInput
from app.services.grade_service import add_grade, grade_analytics
from app.services.ownership_service import student_owned_query

router = APIRouter()


@router.get("/grades/{student_id}")
def get_grades(student_id: int, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    return student_owned_query(db, GradeRecord, student_id).order_by(GradeRecord.semester, GradeRecord.subject_id).all()


@router.post("/grades/{student_id}")
def record_grade(student_id: int, payload: GradeInput, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    try:
        return add_grade(db, student_id, payload.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=404 if "profile" in str(error).lower() else 422, detail=str(error)) from error


@router.get("/grades/{student_id}/analytics")
def read_grade_analytics(student_id: int, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    return grade_analytics(db, student_id)
