from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.db.models import DeadlineItem, Habit, HabitLog, HabitStreak, StudyActivityLog, StudyBlock
from app.services.ownership_service import student_owned_query
from app.services.time_service import utc_now_naive


def analyze_productivity(db: Session, student_id: int, today: date | None = None) -> dict:
    today = today or utc_now_naive().date()
    week_start = today - timedelta(days=6)
    logs = student_owned_query(db, StudyActivityLog, student_id).filter(
        StudyActivityLog.logged_at >= utc_now_naive() - timedelta(days=7)
    ).all()
    completed_blocks = student_owned_query(db, StudyBlock, student_id).filter(
        StudyBlock.completed.is_(True),
        StudyBlock.start_time >= utc_now_naive() - timedelta(days=7),
    ).all()
    scheduled_blocks = student_owned_query(db, StudyBlock, student_id).filter(
        StudyBlock.start_time >= utc_now_naive() - timedelta(days=7),
        StudyBlock.start_time < utc_now_naive(),
    ).all()
    logged_minutes = sum(max(0, int(log.duration_minutes)) for log in logs)
    completed_block_minutes = sum(block.planned_duration for block in completed_blocks)
    study_minutes = max(logged_minutes, completed_block_minutes)

    habits = db.query(Habit).filter_by(student_id=student_id, active=True).all()
    streaks = [db.query(HabitStreak).filter_by(habit_id=habit.id).first() for habit in habits]
    streaks = [streak for streak in streaks if streak is not None]
    habit_completion = sum(streak.completion_rate for streak in streaks) / len(streaks) if streaks else 0.0
    consistency = sum(streak.consistency_score for streak in streaks) / len(streaks) if streaks else 0.0
    block_completion = 100 * len(completed_blocks) / len(scheduled_blocks) if scheduled_blocks else None
    completion_scores = [score for score in (habit_completion, block_completion) if score is not None]
    completion_rate = round(sum(completion_scores) / len(completion_scores), 1) if completion_scores else round(habit_completion, 1)
    study_target_score = min(100.0, 100 * study_minutes / 600)
    productivity_score = round(0.35 * study_target_score + 0.35 * completion_rate + 0.30 * consistency, 1)

    overdue = db.query(DeadlineItem).filter(
        DeadlineItem.student_id == student_id,
        DeadlineItem.completed.is_(False),
        DeadlineItem.due_date < utc_now_naive(),
    ).all()
    yesterday = today - timedelta(days=1)
    missed_habits = []
    for habit in habits:
        if db.query(HabitLog.id).filter_by(habit_id=habit.id, log_date=yesterday, completed=True).first() is None:
            missed_habits.append(habit.habit_name)
    risks = []
    if overdue:
        risks.append({"type": "OVERDUE_DEADLINE", "count": len(overdue)})
    if missed_habits:
        risks.append({"type": "MISSED_HABIT", "habits": missed_habits})
    if completion_rate < 50 and scheduled_blocks:
        risks.append({"type": "PROCRASTINATION", "completion_rate": completion_rate})

    suggestions = []
    if study_minutes < 300:
        suggestions.append("Schedule shorter focused study blocks across the week.")
    if consistency < 60:
        suggestions.append("Choose a small daily habit target and log it consistently.")
    if overdue:
        suggestions.append("Reserve the next available study block for the oldest overdue deadline.")
    if not suggestions:
        suggestions.append("Keep the current routine; review weekly progress and adjust one goal at a time.")

    return {
        "student_id": student_id,
        "productivity_score": productivity_score,
        "consistency_score": round(consistency, 1),
        "study_hours_7d": round(study_minutes / 60, 1),
        "study_minutes_7d": study_minutes,
        "completion_rate": completion_rate,
        "habit_streaks": [
            {"habit_id": habit.id, "habit_name": habit.habit_name, "current_streak": streak.current_streak,
             "longest_streak": streak.longest_streak, "completion_rate": streak.completion_rate}
            for habit in habits
            for streak in [db.query(HabitStreak).filter_by(habit_id=habit.id).first()]
            if streak is not None
        ],
        "procrastination_risks": risks,
        "suggestions": suggestions,
        "window_start": week_start,
        "window_end": today,
    }
