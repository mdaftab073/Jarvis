from datetime import datetime, timedelta
from collections import deque

from sqlalchemy.orm import Session

from app.db.models import AttendanceRecord, CalendarEvent, DeadlineItem, Habit, HabitLog, StudentGoal, StudyBlock
from app.models import Topic, TopicMastery
from app.services.ownership_service import require_subject_owner
from app.services.time_service import normalize_utc_naive, utc_now_naive


def detect_conflicts(
    db: Session,
    student_id: int,
    start_time: datetime,
    end_time: datetime,
    exclude_id: int | None = None,
) -> list[StudyBlock | CalendarEvent]:
    start_time = normalize_utc_naive(start_time)
    end_time = normalize_utc_naive(end_time)
    if end_time <= start_time:
        raise ValueError("end_time must be after start_time")
    query = db.query(StudyBlock).filter(
        StudyBlock.student_id == student_id,
        StudyBlock.start_time < end_time,
        StudyBlock.end_time > start_time,
    )
    if exclude_id is not None:
        query = query.filter(StudyBlock.id != exclude_id)
    blocks = query.all()
    events = db.query(CalendarEvent).filter(
        CalendarEvent.student_id == student_id,
        CalendarEvent.start_time < end_time,
        CalendarEvent.end_time > start_time,
    ).all()
    return [*blocks, *events]


def create_study_block(db: Session, student_id: int, fields: dict) -> StudyBlock:
    fields = dict(fields)
    fields["start_time"] = normalize_utc_naive(fields["start_time"])
    fields["end_time"] = normalize_utc_naive(fields["end_time"])
    require_subject_owner(db, student_id, fields.get("subject_id"))
    start, end = fields["start_time"], fields["end_time"]
    if end <= start:
        raise ValueError("end_time must be after start_time")
    if detect_conflicts(db, student_id, start, end):
        raise ValueError("Study block conflicts with an existing block")
    fields.setdefault("planned_duration", int((end - start).total_seconds() // 60))
    block = StudyBlock(student_id=student_id, **fields)
    db.add(block)
    db.commit()
    db.refresh(block)
    return block


def generate_study_schedule(db: Session, student_id: int, subject_ids: list[int], start_time: datetime, session_length: int = 50, break_minutes: int = 10) -> list[StudyBlock]:
    start_time = normalize_utc_naive(start_time)
    if session_length <= 0 or break_minutes < 0:
        raise ValueError("session_length must be positive and break_minutes non-negative")
    for subject_id in subject_ids:
        require_subject_owner(db, student_id, subject_id)
    specs = []
    cursor = start_time
    for subject_id in subject_ids:
        end = cursor + timedelta(minutes=session_length)
        if detect_conflicts(db, student_id, cursor, end) or any(cursor < other_end and end > other_start for other_start, other_end in specs):
            raise ValueError("Generated schedule conflicts with an existing block")
        specs.append((cursor, end))
        cursor = end + timedelta(minutes=break_minutes)
    blocks = [StudyBlock(student_id=student_id, subject_id=subject_id, start_time=start, end_time=end, planned_duration=session_length) for subject_id, (start, end) in zip(subject_ids, specs)]
    db.add_all(blocks)
    db.commit()
    for block in blocks:
        db.refresh(block)
    return blocks


def generate_intelligent_schedule(
    db: Session,
    student_id: int,
    start_time: datetime,
    available_hours: float,
    horizon_days: int = 7,
    session_minutes: int = 45,
) -> list[StudyBlock]:
    if available_hours <= 0 or horizon_days < 1 or session_minutes < 15:
        raise ValueError("available_hours, horizon_days, and session_minutes must be positive")
    start_time = normalize_utc_naive(start_time)
    horizon_end = start_time + timedelta(days=horizon_days)
    tasks: list[tuple[float, int | None, str, str]] = []
    now = utc_now_naive()

    deadlines = db.query(DeadlineItem).filter(
        DeadlineItem.student_id == student_id,
        DeadlineItem.completed.is_(False),
        DeadlineItem.due_date >= now,
        DeadlineItem.due_date <= horizon_end,
    ).all()
    priority_value = {"CRITICAL": 5, "HIGH": 4, "MEDIUM": 3, "LOW": 2}
    for deadline in deadlines:
        days_left = max(0, (deadline.due_date - now).total_seconds() / 86400)
        score = priority_value.get(deadline.priority, 1) + 5 / (days_left + 1)
        tasks.append((score, deadline.subject_id, f"Prepare: {deadline.title}", "DEADLINE_PREP"))

    for attendance in db.query(AttendanceRecord).filter_by(student_id=student_id).all():
        percentage = attendance.attendance_percentage
        if percentage is not None and percentage < 75:
            tasks.append((8 + (75 - percentage) / 10, attendance.subject_id, "Review attendance recovery plan", "ATTENDANCE_RECOVERY"))

    weak_topics = (
        db.query(TopicMastery, Topic)
        .join(Topic, TopicMastery.topic_id == Topic.id)
        .filter(TopicMastery.student_id == student_id, TopicMastery.mastery_score < 50)
        .all()
    )
    for mastery, topic in weak_topics:
        tasks.append((7 + (50 - mastery.mastery_score) / 10, topic.subject_id, f"Revise: {topic.name}", "REVISION"))

    goals = db.query(StudentGoal).filter_by(student_id=student_id, completed=False).all()
    for goal in goals:
        score = 4
        if goal.target_date is not None:
            days_left = (goal.target_date - start_time.date()).days
            score += 3 / (max(0, days_left) + 1)
        tasks.append((score, None, f"Work on goal: {goal.title}", "GOAL"))

    yesterday = start_time.date() - timedelta(days=1)
    for habit in db.query(Habit).filter_by(student_id=student_id, active=True).all():
        done = db.query(HabitLog.id).filter_by(habit_id=habit.id, log_date=yesterday, completed=True).first()
        if done is None:
            tasks.append((3, None, f"Resume habit: {habit.habit_name}", "STUDY"))

    if not tasks:
        tasks.append((1, None, "Review current course material", "STUDY"))
    tasks.sort(key=lambda task: task[0], reverse=True)
    queue = deque(tasks)
    created: list[StudyBlock] = []
    daily_minutes = int(available_hours * 60)
    block_count = 0

    for day_offset in range(horizon_days):
        day = start_time.date() + timedelta(days=day_offset)
        cursor = datetime.combine(day, start_time.time())
        elapsed = 0
        while elapsed + session_minutes <= daily_minutes:
            conflicts = detect_conflicts(
                db,
                student_id,
                cursor,
                cursor + timedelta(minutes=session_minutes),
            )
            while conflicts:
                cursor = max(item.end_time for item in conflicts) + timedelta(minutes=5)
                conflicts = detect_conflicts(
                    db,
                    student_id,
                    cursor,
                    cursor + timedelta(minutes=session_minutes),
                )
            if cursor.date() != day:
                break
            _, subject_id, title, block_type = queue[0]
            queue.rotate(-1)
            block_count += 1
            if block_count % 4 == 0:
                block_type = "REVISION"
            block = StudyBlock(
                student_id=student_id,
                subject_id=subject_id,
                title=title,
                block_type=block_type,
                start_time=cursor,
                end_time=cursor + timedelta(minutes=session_minutes),
                planned_duration=session_minutes,
            )
            db.add(block)
            db.flush()
            created.append(block)
            elapsed += session_minutes + 5
            cursor = block.end_time + timedelta(minutes=5)

    db.commit()
    for block in created:
        db.refresh(block)
    return created
