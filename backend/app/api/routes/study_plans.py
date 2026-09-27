from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.study_plan import (
    PlanProgress,
    RecalculateResponse,
    StudyPlanGenerateRequest,
    StudyPlanResponse,
)
from app.services.study_plan_service import (
    calculate_plan_progress,
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
    db: Session = Depends(get_db),
):
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
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = get_study_plan(db, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Study plan not found")
    return plan


@router.patch(
    "/study-plans/tasks/{task_id}/complete",
    response_model=StudyPlanResponse,
)
def complete_task(task_id: int, db: Session = Depends(get_db)):
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
def get_plan_progress(plan_id: int, db: Session = Depends(get_db)):
    plan = get_study_plan(db, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Study plan not found")
    return plan["progress"]


@router.post(
    "/study-plans/{plan_id}/recalculate",
    response_model=RecalculateResponse,
)
def recalculate_study_plan(plan_id: int, db: Session = Depends(get_db)):
    try:
        result = recalculate_plan(db, plan_id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail="Study plan not found")
    plan, rescheduled_tasks = result
    return RecalculateResponse(**plan, rescheduled_tasks=rescheduled_tasks)
