from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.profile import ProfileResponse, ProfileSummaryResponse
from app.services.memory_service import (
    build_student_profile,
    generate_profile_summary,
    get_memories,
    get_readiness_snapshots,
)

router = APIRouter()


def _handle_profile_error(error: ValueError):
    status_code = 404 if "not found" in str(error).lower() else 422
    raise HTTPException(status_code=status_code, detail=str(error)) from error


@router.get("/profile/{student_id}", response_model=ProfileResponse)
def student_profile(student_id: int, db: Session = Depends(get_db)):
    try:
        return build_student_profile(student_id, db=db)
    except ValueError as error:
        _handle_profile_error(error)


@router.get("/profile/{student_id}/summary", response_model=ProfileSummaryResponse)
def student_profile_summary(student_id: int, db: Session = Depends(get_db)):
    try:
        return generate_profile_summary(student_id, db=db)
    except ValueError as error:
        _handle_profile_error(error)


@router.get("/profile/{student_id}/readiness-history")
def student_readiness_history(student_id: int, db: Session = Depends(get_db)):
    try:
        return get_readiness_snapshots(student_id, db=db)
    except ValueError as error:
        _handle_profile_error(error)


@router.get("/profile/{student_id}/memories")
def student_memories(student_id: int, db: Session = Depends(get_db)):
    try:
        return get_memories(student_id, db=db)
    except ValueError as error:
        _handle_profile_error(error)


@router.get("/profile/debug/{student_id}")
def debug_student_profile(student_id: int, db: Session = Depends(get_db)):
    try:
        return {
            "stored_memories": get_memories(student_id, db=db),
            "profile_state": build_student_profile(student_id, db=db),
            "readiness_snapshots": get_readiness_snapshots(student_id, db=db),
        }
    except ValueError as error:
        _handle_profile_error(error)