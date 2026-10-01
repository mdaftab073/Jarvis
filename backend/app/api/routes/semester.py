from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.student_scope import require_record_owner, require_student_scope
from app.db.models import Semester
from app.schemas.semester import (
    SemesterCreateRequest,
    SemesterMilestoneCreateRequest,
    SemesterMilestoneUpdateRequest,
    SemesterResponse,
    SemesterStatusUpdateRequest,
)
from app.services.copilot_service import generate_copilot_guidance
from app.services.semester_service import (
    add_semester_milestone,
    calculate_semester_health,
    calculate_semester_progress,
    create_semester,
    detect_academic_risks,
    generate_weekly_review,
    get_semester,
    update_milestone_completion,
    update_semester_status,
)

router = APIRouter()


def _raise_semester_error(error: ValueError):
    status_code = 404 if "not found" in str(error).lower() else 422
    raise HTTPException(status_code=status_code, detail=str(error)) from error


def _require_semester_scope(db: Session, request: Request, semester_id: int) -> None:
    owner_id = db.query(Semester.student_id).filter_by(id=semester_id).scalar()
    if owner_id is not None:
        require_record_owner(request, owner_id)


@router.post("/semester", status_code=201, response_model=SemesterResponse)
def post_semester(
    request: SemesterCreateRequest,
    http_request: Request,
    db: Session = Depends(get_db),
):
    require_student_scope(request.student_id, http_request, db)
    try:
        return create_semester(
            db,
            student_id=request.student_id,
            semester_number=request.semester_number,
            start_date=request.start_date,
            end_date=request.end_date,
            target_cgpa=request.target_cgpa,
            subjects=[item.model_dump() for item in request.subjects],
        )
    except ValueError as error:
        _raise_semester_error(error)


@router.get("/semester/{semester_id}", response_model=SemesterResponse)
def semester_detail(semester_id: int, request: Request, db: Session = Depends(get_db)):
    _require_semester_scope(db, request, semester_id)
    try:
        return {
            **get_semester(db, semester_id),
            "progress": calculate_semester_progress(db, semester_id),
        }
    except ValueError as error:
        _raise_semester_error(error)


@router.get("/semester/{semester_id}/health")
def semester_health(semester_id: int, request: Request, db: Session = Depends(get_db)):
    _require_semester_scope(db, request, semester_id)
    try:
        return calculate_semester_health(db, semester_id)
    except ValueError as error:
        _raise_semester_error(error)


@router.get("/semester/{semester_id}/review")
def semester_review(semester_id: int, request: Request, db: Session = Depends(get_db)):
    _require_semester_scope(db, request, semester_id)
    try:
        return generate_weekly_review(db, semester_id)
    except ValueError as error:
        _raise_semester_error(error)


@router.get("/semester/{semester_id}/risks")
def semester_risks(semester_id: int, request: Request, db: Session = Depends(get_db)):
    _require_semester_scope(db, request, semester_id)
    try:
        return detect_academic_risks(db, semester_id)
    except ValueError as error:
        _raise_semester_error(error)


@router.post("/semester/{semester_id}/milestone", status_code=201)
def post_semester_milestone(
    semester_id: int,
    http_request: Request,
    request: SemesterMilestoneCreateRequest,
    db: Session = Depends(get_db),
):
    _require_semester_scope(db, http_request, semester_id)
    try:
        return add_semester_milestone(
            db,
            semester_id,
            request.title,
            request.due_date,
            description=request.description,
            completed=request.completed,
        )
    except ValueError as error:
        _raise_semester_error(error)


@router.patch("/semester/{semester_id}/milestone/{milestone_id}")
def patch_semester_milestone(
    semester_id: int,
    milestone_id: int,
    http_request: Request,
    request: SemesterMilestoneUpdateRequest,
    db: Session = Depends(get_db),
):
    _require_semester_scope(db, http_request, semester_id)
    try:
        milestone = update_milestone_completion(
            db,
            semester_id,
            milestone_id,
            request.completed,
        )
    except ValueError as error:
        _raise_semester_error(error)
    if milestone is None:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return milestone


@router.get("/semester/{semester_id}/copilot")
def semester_copilot(semester_id: int, request: Request, db: Session = Depends(get_db)):
    _require_semester_scope(db, request, semester_id)
    try:
        return generate_copilot_guidance(db, semester_id)
    except ValueError as error:
        _raise_semester_error(error)


@router.patch("/semester/{semester_id}/status", response_model=SemesterResponse)
def patch_semester_status(
    semester_id: int,
    http_request: Request,
    request: SemesterStatusUpdateRequest,
    db: Session = Depends(get_db),
):
    _require_semester_scope(db, http_request, semester_id)
    try:
        return update_semester_status(db, semester_id, request.status)
    except ValueError as error:
        _raise_semester_error(error)