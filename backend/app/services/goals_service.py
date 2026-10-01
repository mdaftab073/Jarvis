from datetime import date, datetime

from sqlalchemy.orm import Session

from app.db.models import GoalMilestone, GoalProgress, Student, StudentGoal
from app.services.time_service import utc_now_naive

GOAL_TYPES = {"SEMESTER", "CPI", "ATTENDANCE", "PLACEMENT", "STUDY_HOURS"}


def _validate_value(goal_type: str, value: float | None, label: str) -> None:
    if value is not None and value < 0:
        raise ValueError(f"{label} must be non-negative")
    if goal_type == "CPI" and value is not None and value > 10:
        raise ValueError(f"{label} for CPI goals cannot exceed 10")
    if goal_type == "ATTENDANCE" and value is not None and value > 100:
        raise ValueError(f"{label} for attendance goals cannot exceed 100")


def create_goal(db: Session, student_id: int, fields: dict) -> StudentGoal:
    if db.query(Student.id).filter_by(id=student_id).first() is None:
        raise ValueError("Student not found")
    goal_type = fields.get("goal_type", "STUDY_HOURS").upper()
    if goal_type not in GOAL_TYPES:
        raise ValueError("Unsupported goal_type")
    _validate_value(goal_type, fields.get("target_value"), "target_value")
    goal = StudentGoal(student_id=student_id, **{**fields, "goal_type": goal_type})
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def list_goals(db: Session, student_id: int, include_completed: bool = True) -> list[dict]:
    query = db.query(StudentGoal).filter_by(student_id=student_id)
    if not include_completed:
        query = query.filter(StudentGoal.completed.is_(False))
    return [serialize_goal(db, goal) for goal in query.order_by(StudentGoal.target_date, StudentGoal.id).all()]


def get_goal(db: Session, goal_id: int) -> StudentGoal | None:
    return db.query(StudentGoal).filter_by(id=goal_id).first()


def update_goal(db: Session, goal_id: int, fields: dict) -> StudentGoal | None:
    goal = get_goal(db, goal_id)
    if goal is None:
        return None
    goal_type = fields.get("goal_type", goal.goal_type).upper()
    if goal_type not in GOAL_TYPES:
        raise ValueError("Unsupported goal_type")
    _validate_value(goal_type, fields.get("target_value", goal.target_value), "target_value")
    for key, value in fields.items():
        if key in {"title", "goal_type", "target_value", "target_unit", "target_date", "completed"}:
            setattr(goal, key, value)
    db.commit()
    db.refresh(goal)
    return goal


def delete_goal(db: Session, goal_id: int) -> bool:
    goal = get_goal(db, goal_id)
    if goal is None:
        return False
    db.delete(goal)
    db.commit()
    return True


def create_milestone(db: Session, student_id: int, goal_id: int, fields: dict) -> GoalMilestone:
    goal = get_goal(db, goal_id)
    if goal is None or goal.student_id != student_id:
        raise ValueError("Goal not found for student")
    milestone = GoalMilestone(student_id=student_id, goal_id=goal_id, **fields)
    db.add(milestone)
    db.commit()
    db.refresh(milestone)
    return milestone


def list_milestones(db: Session, goal_id: int) -> list[GoalMilestone]:
    return db.query(GoalMilestone).filter_by(goal_id=goal_id).order_by(GoalMilestone.target_date, GoalMilestone.id).all()


def set_milestone_completed(db: Session, milestone_id: int, completed: bool) -> GoalMilestone | None:
    milestone = db.query(GoalMilestone).filter_by(id=milestone_id).first()
    if milestone is None:
        return None
    milestone.completed = completed
    milestone.completed_at = utc_now_naive() if completed else None
    db.commit()
    db.refresh(milestone)
    return milestone


def record_progress(db: Session, student_id: int, goal_id: int, value: float, notes: str | None = None) -> GoalProgress:
    goal = get_goal(db, goal_id)
    if goal is None or goal.student_id != student_id:
        raise ValueError("Goal not found for student")
    _validate_value(goal.goal_type, value, "progress_value")
    progress = GoalProgress(student_id=student_id, goal_id=goal_id, progress_value=value, notes=notes)
    db.add(progress)
    db.flush()
    if goal.target_value is not None:
        goal.completed = value >= goal.target_value
    db.commit()
    db.refresh(progress)
    return progress


def list_progress(db: Session, goal_id: int) -> list[GoalProgress]:
    return db.query(GoalProgress).filter_by(goal_id=goal_id).order_by(GoalProgress.recorded_at, GoalProgress.id).all()


def serialize_goal(db: Session, goal: StudentGoal) -> dict:
    latest = (
        db.query(GoalProgress)
        .filter_by(goal_id=goal.id)
        .order_by(GoalProgress.recorded_at.desc(), GoalProgress.id.desc())
        .first()
    )
    current = goal.target_value if goal.completed and goal.target_value is not None else latest.progress_value if latest else 0.0
    percent = min(100.0, round(100 * current / goal.target_value, 1)) if goal.target_value else (100.0 if goal.completed else None)
    return {
        "id": goal.id,
        "student_id": goal.student_id,
        "title": goal.title,
        "goal_type": goal.goal_type,
        "target_value": goal.target_value,
        "target_unit": goal.target_unit,
        "target_date": goal.target_date,
        "completed": goal.completed,
        "current_value": current,
        "progress_percent": percent,
        "milestones": list_milestones(db, goal.id),
        "created_at": goal.created_at,
    }
