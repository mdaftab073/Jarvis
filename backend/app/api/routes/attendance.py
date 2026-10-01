from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.student_scope import require_student_scope
from app.db.database import get_db
from app.schemas.student_os import AttendanceInput
from app.services.attendance_service import attendance_risk, attendance_summary, upsert_attendance

router = APIRouter()


@router.get("/attendance/{student_id}")
def get_student_attendance(student_id: int, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    return attendance_summary(db, student_id)


@router.post("/attendance/{student_id}")
def record_attendance(student_id: int, payload: AttendanceInput, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    try:
        record = upsert_attendance(db, student_id, payload.subject_id, payload.attended_classes, payload.total_classes)
    except ValueError as error:
        raise HTTPException(status_code=404 if "profile" in str(error).lower() else 422, detail=str(error)) from error
    return {"record": record, "risk": attendance_risk(record.attendance_percentage)}
