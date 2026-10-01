from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.student_scope import require_record_owner, require_student_scope
from app.db.database import get_db
from app.schemas.student_os import HabitCreateInput, HabitLogInput, HabitUpdateInput
from app.services.habit_service import (
    create_habit,
    delete_habit,
    get_habit,
    list_habit_logs,
    list_habits,
    log_habit,
    update_habit,
)
from app.services.time_service import utc_now_naive

router = APIRouter()


@router.get("/habits/{student_id}")
def get_student_habits(student_id: int, active_only: bool = True, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    return list_habits(db, student_id, active_only)


@router.post("/habits/{student_id}")
def add_habit(student_id: int, payload: HabitCreateInput, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    try:
        return create_habit(db, student_id, payload.habit_name, payload.category, payload.target_per_week)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.patch("/habits/{habit_id}")
def edit_habit(habit_id: int, payload: HabitUpdateInput, request: Request, db: Session = Depends(get_db)):
    habit = get_habit(db, habit_id)
    if habit is None:
        raise HTTPException(status_code=404, detail="Habit not found")
    require_record_owner(request, habit.student_id)
    try:
        return update_habit(db, habit_id, payload.model_dump(exclude_unset=True))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.delete("/habits/{habit_id}")
def remove_habit(habit_id: int, request: Request, db: Session = Depends(get_db)):
    habit = get_habit(db, habit_id)
    if habit is None:
        raise HTTPException(status_code=404, detail="Habit not found")
    require_record_owner(request, habit.student_id)
    delete_habit(db, habit_id)
    return {"deleted": True}


@router.post("/habits/{habit_id}/logs")
def record_habit_log(habit_id: int, payload: HabitLogInput, request: Request, db: Session = Depends(get_db)):
    habit = get_habit(db, habit_id)
    if habit is None:
        raise HTTPException(status_code=404, detail="Habit not found")
    require_record_owner(request, habit.student_id)
    try:
        return log_habit(
            db,
            habit.student_id,
            habit_id,
            payload.log_date or utc_now_naive().date(),
            payload.completed,
            payload.duration_minutes,
            payload.notes,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/habits/{habit_id}/logs")
def get_habit_logs(habit_id: int, request: Request, start: date | None = None, end: date | None = None, db: Session = Depends(get_db)):
    habit = get_habit(db, habit_id)
    if habit is None:
        raise HTTPException(status_code=404, detail="Habit not found")
    require_record_owner(request, habit.student_id)
    if start is not None and end is not None and end < start:
        raise HTTPException(status_code=422, detail="end must be on or after start")
    return list_habit_logs(db, habit_id, start, end)
