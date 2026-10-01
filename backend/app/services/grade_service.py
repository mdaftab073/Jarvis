from sqlalchemy.orm import Session

from app.db.models import GradeRecord, StudentAcademicProfile
from app.services.ownership_service import require_subject_owner, student_owned_query


def _records(db: Session, student_id: int) -> list[GradeRecord]:
    return student_owned_query(db, GradeRecord, student_id).all()


def _final_records(records: list[GradeRecord]) -> list[GradeRecord]:
    return [
        record for record in records
        if record.grade_type == "FINAL"
        and record.grade_points is not None
        and record.credits is not None
        and record.credits > 0
    ]


def _latest_per_subject(records: list[GradeRecord], key) -> list[GradeRecord]:
    latest = {}
    for record in records:
        group = key(record)
        previous = latest.get(group)
        sort_key = (record.semester or 0, record.recorded_at, record.id or 0)
        if previous is None or sort_key > (previous.semester or 0, previous.recorded_at, previous.id or 0):
            latest[group] = record
    return list(latest.values())


def _weighted_average(records: list[GradeRecord]) -> float | None:
    credits = sum(record.credits for record in records)
    if not credits:
        return None
    return round(sum(record.grade_points * record.credits for record in records) / credits, 2)


def calculate_spi(records: list[GradeRecord], semester: int) -> float | None:
    selected = [record for record in _final_records(records) if record.semester == semester]
    selected = _latest_per_subject(selected, lambda record: record.subject_id)
    return _weighted_average(selected)


def calculate_cpi(records: list[GradeRecord]) -> float | None:
    selected = _latest_per_subject(
        _final_records(records), lambda record: record.subject_id
    )
    return _weighted_average(selected)


def recalculate_profile_grades(db: Session, student_id: int) -> dict:
    profile = db.query(StudentAcademicProfile).filter_by(student_id=student_id).first()
    if profile is None:
        return {"cpi": None, "current_spi": None}
    records = _records(db, student_id)
    semesters = sorted({record.semester for record in records if record.semester is not None})
    spi_by_semester = {semester: calculate_spi(records, semester) for semester in semesters}
    profile.current_cpi = calculate_cpi(records)
    profile.current_spi = spi_by_semester.get(profile.semester) if profile.semester else None
    db.flush()
    return {"cpi": profile.current_cpi, "current_spi": profile.current_spi}


def add_grade(db: Session, student_id: int, fields: dict) -> GradeRecord:
    require_subject_owner(db, student_id, fields.get("subject_id"))
    profile = db.query(StudentAcademicProfile).filter_by(student_id=student_id).first()
    if profile is None:
        raise ValueError("Academic profile not found")
    if fields.get("credits") is not None and fields["credits"] < 0:
        raise ValueError("credits must be non-negative")
    if fields.get("grade_points") is not None and not 0 <= fields["grade_points"] <= 10:
        raise ValueError("grade_points must be between 0 and 10")
    if fields.get("semester") is not None and fields["semester"] < 1:
        raise ValueError("semester must be positive")
    grade_type = fields.get("grade_type", "COMPONENT")
    if grade_type not in {"COMPONENT", "FINAL"}:
        raise ValueError("grade_type must be COMPONENT or FINAL")
    if grade_type == "FINAL" and (
        fields.get("semester") is None
        or fields.get("credits") is None
        or fields["credits"] <= 0
        or fields.get("grade_points") is None
    ):
        raise ValueError("FINAL grades require semester, positive credits, and grade_points")
    record = GradeRecord(student_id=student_id, academic_profile_id=profile.id, **fields)
    db.add(record)
    db.flush()
    recalculate_profile_grades(db, student_id)
    db.commit()
    db.refresh(record)
    return record


def list_grades(db: Session, student_id: int) -> list[GradeRecord]:
    return student_owned_query(db, GradeRecord, student_id).order_by(
        GradeRecord.recorded_at.desc(), GradeRecord.id.desc()
    ).all()


def upsert_final_grade(db: Session, student_id: int, fields: dict) -> GradeRecord:
    require_subject_owner(db, student_id, fields.get("subject_id"))
    if fields.get("semester") is None or fields.get("credits") is None or fields["credits"] <= 0:
        raise ValueError("Final grade sync requires semester and positive credits")
    if fields.get("grade_points") is None or not 0 <= fields["grade_points"] <= 10:
        raise ValueError("Final grade sync requires grade_points from 0 to 10")
    record = db.query(GradeRecord).filter_by(
        student_id=student_id,
        subject_id=fields["subject_id"],
        semester=fields["semester"],
        grade_type="FINAL",
    ).first()
    if record is None:
        return add_grade(db, student_id, {**fields, "grade_type": "FINAL"})
    return update_grade(db, record.id, {**fields, "grade_type": "FINAL"})


def update_grade(db: Session, record_id: int, fields: dict) -> GradeRecord | None:
    record = db.query(GradeRecord).filter_by(id=record_id).first()
    if record is None:
        return None
    merged = {
        "grade_type": record.grade_type,
        "semester": record.semester,
        "credits": record.credits,
        "grade_points": record.grade_points,
        **fields,
    }
    if merged["grade_type"] == "FINAL" and (
        merged["semester"] is None
        or merged["credits"] is None
        or merged["credits"] <= 0
        or merged["grade_points"] is None
        or not 0 <= merged["grade_points"] <= 10
    ):
        raise ValueError("FINAL grades require semester, positive credits, and grade_points from 0 to 10")
    for key, value in fields.items():
        if hasattr(record, key) and key not in {"id", "student_id", "academic_profile_id"}:
            setattr(record, key, value)
    db.flush()
    recalculate_profile_grades(db, record.student_id)
    db.commit()
    db.refresh(record)
    return record


def delete_grade(db: Session, record_id: int) -> bool:
    record = db.query(GradeRecord).filter_by(id=record_id).first()
    if record is None:
        return False
    student_id = record.student_id
    db.delete(record)
    db.flush()
    recalculate_profile_grades(db, student_id)
    db.commit()
    return True


def grade_analytics(db: Session, student_id: int) -> dict:
    records = _records(db, student_id)
    profile = db.query(StudentAcademicProfile).filter_by(student_id=student_id).first()
    semesters = sorted({r.semester for r in records if r.semester is not None})
    spi_by_semester = {semester: calculate_spi(records, semester) for semester in semesters}
    return {
        "spi_by_semester": spi_by_semester,
        "cpi": calculate_cpi(records),
        "record_count": len(records),
        "current_spi": spi_by_semester.get(profile.semester) if profile and profile.semester else None,
    }
