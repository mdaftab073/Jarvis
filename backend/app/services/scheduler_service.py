from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.db.models import CalendarEvent, StudyBlock
from app.services.ownership_service import require_subject_owner
from app.services.time_service import normalize_utc_naive


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
