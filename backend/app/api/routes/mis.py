from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.student_scope import require_student_scope
from app.db.database import get_db
from app.schemas.mis import (
    AttendanceResponse,
    MISSyncResponse,
    ResultResponse,
    SemesterResult,
    StudentProfileResponse,
    TimetableEntry,
    TimetableResponse,
    AttendanceRecord,
)
from app.services.mis.client import MISClientError
from app.services.mis.parser import MISParseError
from app.services.mis_sync_service import (
    MISSyncError,
    get_profile,
    sync_attendance,
    sync_profile,
    sync_results,
    sync_timetable,
)


router = APIRouter()


def _translate_error(error: Exception):
    if isinstance(error, MISClientError):
        detail = {"code": error.code, "message": str(error)}
        if getattr(error, "required", None):
            detail["required"] = error.required
        raise HTTPException(status_code=error.status_code, detail=detail) from error
    if isinstance(error, MISParseError):
        raise HTTPException(status_code=502, detail={"code": "parse_error", "message": str(error)}) from error
    if isinstance(error, MISSyncError):
        status_code = 404 if str(error) == "Student not found" else 409
        raise HTTPException(status_code=status_code, detail={"code": "sync_error", "message": str(error)}) from error
    raise error


@router.post("/mis/sync-profile", response_model=MISSyncResponse)
def post_sync_profile(student_id: int, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    try:
        profile, count = sync_profile(db, student_id)
        return MISSyncResponse(student_id=student_id, resource="profile", status="succeeded", records_processed=count, synced_at=profile.updated_at)
    except Exception as error:
        _translate_error(error)


@router.get("/mis/profile", response_model=StudentProfileResponse)
def read_mis_profile(student_id: int, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    profile = get_profile(db, student_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="MIS profile not found")
    return profile


@router.post("/mis/sync-attendance", response_model=MISSyncResponse)
def post_sync_attendance(student_id: int, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    try:
        profile, count = sync_attendance(db, student_id)
        return MISSyncResponse(student_id=student_id, resource="attendance", status="succeeded", records_processed=count, synced_at=profile.updated_at)
    except Exception as error:
        _translate_error(error)


@router.get("/mis/attendance", response_model=AttendanceResponse)
def read_mis_attendance(student_id: int, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    profile = get_profile(db, student_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="MIS attendance not found")
    return AttendanceResponse(student_id=student_id, records=[AttendanceRecord.model_validate(row) for row in profile.attendance_json], updated_at=profile.updated_at)


@router.post("/mis/sync-results", response_model=MISSyncResponse)
def post_sync_results(student_id: int, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    try:
        profile, count = sync_results(db, student_id)
        return MISSyncResponse(student_id=student_id, resource="results", status="succeeded", records_processed=count, synced_at=profile.updated_at)
    except Exception as error:
        _translate_error(error)


@router.get("/mis/results", response_model=ResultResponse)
def read_mis_results(student_id: int, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    profile = get_profile(db, student_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="MIS results not found")
    return ResultResponse(student_id=student_id, records=[SemesterResult.model_validate(row) for row in profile.results_json], updated_at=profile.updated_at)


@router.get("/mis/timetable", response_model=TimetableResponse)
def read_mis_timetable(student_id: int, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    profile = get_profile(db, student_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="MIS timetable not found")
    return TimetableResponse(student_id=student_id, entries=[TimetableEntry.model_validate(row) for row in profile.timetable_json], updated_at=profile.updated_at)


@router.post("/mis/sync-timetable", response_model=MISSyncResponse)
def post_sync_timetable(student_id: int, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    try:
        profile, count = sync_timetable(db, student_id)
        return MISSyncResponse(student_id=student_id, resource="timetable", status="succeeded", records_processed=count, synced_at=profile.updated_at)
    except Exception as error:
        _translate_error(error)