from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.student_scope import require_record_owner, require_student_scope
from app.db.database import get_db
from app.db.models import StudyPlan, StudyTask
from app.schemas.study_plan import (
    PlanProgress,
    RecalculateResponse,
    StudyPlanGenerateRequest,
    StudyPlanResponse,
)
from app.services.study_plan_service import (
    complete_study_task,
    generate_study_plan,
    get_study_plan,
    recalculate_plan,
)

router = APIRouter()


def _raise_plan_error(error: ValueError):
    status_code = 404 if "not found" in str(error).lower() else 422
    raise HTTPException(status_code=status_code, detail=str(error)) from error


@router.post(
    "/study-plans/generate",
    response_model=StudyPlanResponse,
)
def generate_plan(
    request: StudyPlanGenerateRequest,
    http_request: Request,
    db: Session = Depends(get_db),
):
    require_student_scope(request.student_id, http_request, db)
    try:
        plan = generate_study_plan(
            db=db,
            student_id=request.student_id,
            subject_id=request.subject_id,
            exam_date=request.exam_date,
            hours_per_day=request.hours_per_day,
            subject_difficulty=request.subject_difficulty,
        )
    except ValueError as error:
        _raise_plan_error(error)
    return get_study_plan(db, plan.id)


@router.get(
    "/study-plans/{plan_id}",
    response_model=StudyPlanResponse,
)
def get_plan(plan_id: int, request: Request, db: Session = Depends(get_db)):
    plan = get_study_plan(db, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Study plan not found")
    require_record_owner(request, plan["student_id"])
    return plan


@router.patch(
    "/study-plans/tasks/{task_id}/complete",
    response_model=StudyPlanResponse,
)
def complete_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    task_owner = (
        db.query(StudyPlan.student_id)
        .join(StudyTask, StudyTask.study_plan_id == StudyPlan.id)
        .filter(StudyTask.id == task_id)
        .scalar()
    )
    if task_owner is not None:
        require_record_owner(request, task_owner)
    try:
        plan = complete_study_task(db, task_id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if plan is None:
        raise HTTPException(status_code=404, detail="Study task not found")
    return plan


@router.get(
    "/study-plans/{plan_id}/progress",
    response_model=PlanProgress,
)
def get_plan_progress(plan_id: int, request: Request, db: Session = Depends(get_db)):
    plan = get_study_plan(db, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Study plan not found")
    require_record_owner(request, plan["student_id"])
    return plan["progress"]


@router.post(
    "/study-plans/{plan_id}/recalculate",
    response_model=RecalculateResponse,
)
def recalculate_study_plan(plan_id: int, request: Request, db: Session = Depends(get_db)):
    owner_id = db.query(StudyPlan.student_id).filter_by(id=plan_id).scalar()
    if owner_id is not None:
        require_record_owner(request, owner_id)
    try:
        result = recalculate_plan(db, plan_id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail="Study plan not found")
    plan, rescheduled_tasks = result
    return RecalculateResponse(**plan, rescheduled_tasks=rescheduled_tasks)
