
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.student_scope import require_record_owner, require_student_scope
from app.db.database import get_db
from app.db.models import GoalMilestone
from app.schemas.student_os import GoalCreateInput, GoalUpdateInput, MilestoneInput, ProgressInput
from app.services.goals_service import (
    create_goal,
    create_milestone,
    delete_goal,
    get_goal,
    list_goals,
    list_milestones,
    list_progress,
    record_progress,
    serialize_goal,
    set_milestone_completed,
    update_goal,
)

router = APIRouter()


@router.get("/goals/{student_id}")
def get_student_goals(student_id: int, include_completed: bool = True, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    return list_goals(db, student_id, include_completed)


@router.post("/goals/{student_id}")
def add_goal(student_id: int, payload: GoalCreateInput, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    try:
        goal = create_goal(db, student_id, payload.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return serialize_goal(db, goal)


@router.patch("/goals/{goal_id}")
def edit_goal(goal_id: int, payload: GoalUpdateInput, request: Request, db: Session = Depends(get_db)):
    existing = get_goal(db, goal_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    require_record_owner(request, existing.student_id)
    try:
        goal = update_goal(db, goal_id, payload.model_dump(exclude_unset=True))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return serialize_goal(db, goal)


@router.delete("/goals/{goal_id}")
def remove_goal(goal_id: int, request: Request, db: Session = Depends(get_db)):
    existing = get_goal(db, goal_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    require_record_owner(request, existing.student_id)
    delete_goal(db, goal_id)
    return {"deleted": True}


@router.post("/milestones/{goal_id}")
def add_milestone(goal_id: int, payload: MilestoneInput, request: Request, db: Session = Depends(get_db)):
    goal = get_goal(db, goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    require_record_owner(request, goal.student_id)
    try:
        return create_milestone(db, goal.student_id, goal_id, payload.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/milestones/{goal_id}")
def get_milestones(goal_id: int, request: Request, db: Session = Depends(get_db)):
    goal = get_goal(db, goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    require_record_owner(request, goal.student_id)
    return list_milestones(db, goal_id)


@router.patch("/milestones/{milestone_id}/complete")
def complete_milestone(milestone_id: int, completed: bool, request: Request, db: Session = Depends(get_db)):
    milestone = db.query(GoalMilestone).filter_by(id=milestone_id).first()
    if milestone is None:
        raise HTTPException(status_code=404, detail="Milestone not found")
    require_record_owner(request, milestone.student_id)
    return set_milestone_completed(db, milestone_id, completed)


@router.post("/progress/{goal_id}")
def add_progress(goal_id: int, payload: ProgressInput, request: Request, db: Session = Depends(get_db)):
    goal = get_goal(db, goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    require_record_owner(request, goal.student_id)
    try:
        return record_progress(db, goal.student_id, goal_id, payload.progress_value, payload.notes)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/progress/{goal_id}")
def get_progress(goal_id: int, request: Request, db: Session = Depends(get_db)):
    goal = get_goal(db, goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    require_record_owner(request, goal.student_id)
    return list_progress(db, goal_id)
