from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.db.models import Habit, HabitLog, HabitStreak, Student, StudentHabit
from app.services.time_service import utc_now_naive

HABIT_CATEGORIES = {
    "DAILY_STUDY", "REVISION", "PYQ_PRACTICE", "ATTENDANCE_CHECK", "ASSIGNMENT_COMPLETION"
}


def create_habit(db: Session, student_id: int, habit_name: str, category: str, target_per_week: int = 7) -> Habit:
    if db.query(Student.id).filter_by(id=student_id).first() is None:
        raise ValueError("Student not found")
    category = category.upper()
    if category not in HABIT_CATEGORIES:
        raise ValueError("Unsupported habit category")
    if not 1 <= target_per_week <= 7:
        raise ValueError("target_per_week must be between 1 and 7")
    habit = Habit(student_id=student_id, habit_name=habit_name.strip(), category=category, target_per_week=target_per_week)
    if not habit.habit_name:
        raise ValueError("habit_name cannot be empty")
    db.add(habit)
    db.flush()
    db.add(HabitStreak(student_id=student_id, habit_id=habit.id))
    db.commit()
    db.refresh(habit)
    return habit


def list_habits(db: Session, student_id: int, active_only: bool = True) -> list[Habit]:
    query = db.query(Habit).filter_by(student_id=student_id)
    if active_only:
        query = query.filter(Habit.active.is_(True))
    return query.order_by(Habit.category, Habit.habit_name).all()


def get_habit(db: Session, habit_id: int) -> Habit | None:
    return db.query(Habit).filter_by(id=habit_id).first()


def update_habit(db: Session, habit_id: int, fields: dict) -> Habit | None:
    habit = get_habit(db, habit_id)
    if habit is None:
        return None
    if "category" in fields and fields["category"].upper() not in HABIT_CATEGORIES:
        raise ValueError("Unsupported habit category")
    if "target_per_week" in fields and not 1 <= fields["target_per_week"] <= 7:
        raise ValueError("target_per_week must be between 1 and 7")
    for key, value in fields.items():
        if key in {"habit_name", "category", "target_per_week", "active"}:
            setattr(habit, key, value.upper() if key == "category" else value)
    db.commit()
    db.refresh(habit)
    return habit


def delete_habit(db: Session, habit_id: int) -> bool:
    habit = get_habit(db, habit_id)
    if habit is None:
        return False
    db.delete(habit)
    db.commit()
    return True


def log_habit(db: Session, student_id: int, habit_id: int, log_date: date, completed: bool = True, duration_minutes: int | None = None, notes: str | None = None) -> HabitLog:
    habit = get_habit(db, habit_id)
    if habit is None or habit.student_id != student_id:
        raise ValueError("Habit not found for student")
    if duration_minutes is not None and duration_minutes < 0:
        raise ValueError("duration_minutes must be non-negative")
    log = db.query(HabitLog).filter_by(habit_id=habit_id, log_date=log_date).first()
    if log is None:
        log = HabitLog(student_id=student_id, habit_id=habit_id, log_date=log_date)
        db.add(log)
    log.completed = completed
    log.duration_minutes = duration_minutes
    log.notes = notes
    db.flush()
    recalculate_habit(db, habit)
    db.commit()
    db.refresh(log)
    return log


def list_habit_logs(db: Session, habit_id: int, start: date | None = None, end: date | None = None) -> list[HabitLog]:
    query = db.query(HabitLog).filter_by(habit_id=habit_id)
    if start is not None:
        query = query.filter(HabitLog.log_date >= start)
    if end is not None:
        query = query.filter(HabitLog.log_date <= end)
    return query.order_by(HabitLog.log_date.desc()).all()


def recalculate_habit(db: Session, habit: Habit, today: date | None = None) -> HabitStreak:
    today = today or utc_now_naive().date()
    window_start = today - timedelta(days=29)
    logs = db.query(HabitLog).filter(
        HabitLog.habit_id == habit.id,
        HabitLog.log_date >= window_start,
        HabitLog.log_date <= today,
    ).all()
    completed_dates = {log.log_date for log in logs if log.completed}
    current = 0
    cursor = today if today in completed_dates else today - timedelta(days=1)
    while cursor in completed_dates:
        current += 1
        cursor -= timedelta(days=1)
    longest = 0
    run = 0
    prior = None
    for completed_date in sorted(completed_dates):
        run = run + 1 if prior == completed_date - timedelta(days=1) else 1
        longest = max(longest, run)
        prior = completed_date
    expected = max(1, round(30 * habit.target_per_week / 7))
    completion_rate = min(100.0, round(100 * len(completed_dates) / expected, 1))
    consistency = round(0.75 * completion_rate + 0.25 * min(100.0, current / 7 * 100), 1)
    streak = db.query(HabitStreak).filter_by(habit_id=habit.id).first()
    if streak is None:
        streak = HabitStreak(student_id=habit.student_id, habit_id=habit.id)
        db.add(streak)
    streak.current_streak = current
    streak.longest_streak = max(longest, streak.longest_streak or 0)
    streak.completion_rate = completion_rate
    streak.consistency_score = consistency
    streak.last_completed_date = max(completed_dates) if completed_dates else None
    streak.updated_at = utc_now_naive()
    legacy = db.query(StudentHabit).filter_by(student_id=habit.student_id, habit_name=habit.habit_name).first()
    if legacy is None:
        db.add(StudentHabit(student_id=habit.student_id, habit_name=habit.habit_name, streak=streak.current_streak, completion_rate=streak.completion_rate))
    else:
        legacy.streak = streak.current_streak
        legacy.completion_rate = streak.completion_rate
    db.flush()
    return streak


def habit_summary(db: Session, student_id: int) -> list[dict]:
    results = []
    for habit in list_habits(db, student_id, active_only=False):
        streak = db.query(HabitStreak).filter_by(habit_id=habit.id).first()
        results.append({"habit": habit, "streak": streak, "logs": list_habit_logs(db, habit.id)})
    return results
