from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.db.models import AttendanceRecord, DeadlineItem, Habit, HabitLog, GoalProgress, StudentAcademicProfile, StudentGoal, StudentNotification
from app.models import Topic, TopicMastery
from app.services.time_service import utc_now_naive


def create_notification(db: Session, student_id: int, title: str, message: str, notification_type: str = "INFO") -> StudentNotification:
    item = StudentNotification(student_id=student_id, title=title, message=message, notification_type=notification_type)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_notifications(db: Session, student_id: int, unread_only: bool = False) -> list[StudentNotification]:
    query = db.query(StudentNotification).filter_by(student_id=student_id)
    if unread_only:
        query = query.filter(StudentNotification.read.is_(False))
    return query.order_by(StudentNotification.created_at.desc()).all()


def mark_notification_read(db: Session, notification_id: int) -> StudentNotification | None:
    item = db.query(StudentNotification).filter_by(id=notification_id).first()
    if item is not None:
        item.read = True
        db.commit()
        db.refresh(item)
    return item


def generate_alerts(db: Session, student_id: int, now: datetime | None = None) -> list[StudentNotification]:
    now = now or utc_now_naive()
    alerts = []
    existing = {
        (item.title, item.message)
        for item in list_notifications(db, student_id, unread_only=False)
    }
    profile = db.query(StudentAcademicProfile).filter_by(student_id=student_id).first()
    if profile:
        low = db.query(AttendanceRecord).filter(
            AttendanceRecord.academic_profile_id == profile.id,
            AttendanceRecord.attendance_percentage < 75,
        ).all()
        for record in low:
            message = f"Subject {record.subject_id} attendance is {record.attendance_percentage:.1f}%."
            if ("Attendance warning", message) not in existing:
                alerts.append(create_notification(db, student_id, "Attendance warning", message, "WARNING"))
                existing.add(("Attendance warning", message))
        due = db.query(DeadlineItem).filter(
            DeadlineItem.academic_profile_id == profile.id,
            DeadlineItem.is_completed.is_(False),
            DeadlineItem.due_date >= now,
            DeadlineItem.due_date <= now + timedelta(days=3),
        ).all()
        for item in due:
            message = f"{item.title} is due {item.due_date.isoformat()}."
            if ("Upcoming deadline", message) not in existing:
                alerts.append(create_notification(db, student_id, "Upcoming deadline", message, "REMINDER"))
                existing.add(("Upcoming deadline", message))

    weak_topics = (
        db.query(TopicMastery, Topic)
        .join(Topic, TopicMastery.topic_id == Topic.id)
        .filter(TopicMastery.student_id == student_id, TopicMastery.mastery_score < 50)
        .order_by(TopicMastery.mastery_score)
        .limit(5)
        .all()
    )
    for mastery, topic in weak_topics:
        message = f"{topic.name} mastery is {mastery.mastery_score:.1f}%; schedule a revision block."
        if ("Weak topic", message) not in existing:
            alerts.append(create_notification(db, student_id, "Weak topic", message, "WARNING"))
            existing.add(("Weak topic", message))

    yesterday = now.date() - timedelta(days=1)
    habits = db.query(Habit).filter_by(student_id=student_id, active=True).all()
    for habit in habits:
        cadence_days = max(1, round(7 / habit.target_per_week))
        last_day = yesterday
        first_day = last_day - timedelta(days=cadence_days - 1)
        completed = db.query(HabitLog.id).filter(
            HabitLog.habit_id == habit.id,
            HabitLog.completed.is_(True),
            HabitLog.log_date >= first_day,
            HabitLog.log_date <= last_day,
        ).first()
        if completed is None:
            message = f"{habit.habit_name} was not logged in its last {cadence_days}-day window."
            if ("Missed habit", message) not in existing:
                alerts.append(create_notification(db, student_id, "Missed habit", message, "REMINDER"))
                existing.add(("Missed habit", message))

    goals = db.query(StudentGoal).filter(
        StudentGoal.student_id == student_id,
        StudentGoal.completed.is_(False),
        StudentGoal.target_date.is_not(None),
        StudentGoal.target_date <= (now + timedelta(days=7)).date(),
    ).all()
    for goal in goals:
        latest = db.query(GoalProgress).filter_by(goal_id=goal.id).order_by(GoalProgress.recorded_at.desc()).first()
        current_value = latest.progress_value if latest else 0
        if goal.target_value is None or current_value < goal.target_value * 0.75:
            message = f"{goal.title} is due {goal.target_date.isoformat()} and needs progress."
            if ("Goal at risk", message) not in existing:
                alerts.append(create_notification(db, student_id, "Goal at risk", message, "WARNING"))
                existing.add(("Goal at risk", message))
    return alerts
