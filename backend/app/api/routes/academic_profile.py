from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.student_scope import require_student_scope
from app.db.database import get_db
from app.db.models import StudentPreference
from app.schemas.student_os import PreferenceInput, ProfileInput
from app.services.academic_profile_service import academic_summary, create_or_update_profile, get_profile

router = APIRouter()


@router.get("/academic-profiles/{student_id}")
def read_profile(student_id: int, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    profile = get_profile(db, student_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Academic profile not found")
    return profile


@router.put("/academic-profiles/{student_id}")
def write_profile(student_id: int, payload: ProfileInput, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    try:
        return create_or_update_profile(db, student_id, payload.model_dump(exclude_unset=True))
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/academic-profiles/{student_id}/summary")
def read_academic_summary(student_id: int, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    return academic_summary(db, student_id)


@router.get("/academic-profiles/{student_id}/preferences")
def read_preferences(student_id: int, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    return db.query(StudentPreference).filter_by(student_id=student_id).first() or {}


@router.put("/academic-profiles/{student_id}/preferences")
def write_preferences(student_id: int, payload: PreferenceInput, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    preference = db.query(StudentPreference).filter_by(student_id=student_id).first()
    if preference is None:
        preference = StudentPreference(student_id=student_id)
        db.add(preference)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(preference, key, value)
    db.commit()
    db.refresh(preference)
    return preference
