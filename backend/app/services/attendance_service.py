import math
from sqlalchemy.orm import Session

from app.db.models import AttendanceRecord, StudentAcademicProfile
from app.services.ownership_service import require_subject_owner, student_owned_query
from app.services.time_service import utc_now_naive


def _profile(db: Session, student_id: int) -> StudentAcademicProfile:
    profile = db.query(StudentAcademicProfile).filter_by(student_id=student_id).first()
    if profile is None:
        raise ValueError("Academic profile not found")
    return profile


def attendance_risk(percentage: float | None) -> str:
    if percentage is None:
        return "UNKNOWN"
    if percentage >= 75:
        return "SAFE"
    if percentage >= 65:
        return "WARNING"
    return "CRITICAL"


def classes_to_recover(attended: int, total: int, target: float = 75) -> int:
    if attended < 0 or total < 0 or attended > total or not 0 < target < 100:
        raise ValueError("Invalid attendance values or target")
    if total == 0 or attended / total * 100 >= target:
        return 0
    return max(0, math.ceil((target * total - 100 * attended) / (100 - target)))


def list_attendance(db: Session, student_id: int) -> list[AttendanceRecord]:
    return student_owned_query(db, AttendanceRecord, student_id).all()


def upsert_attendance(db: Session, student_id: int, subject_id: int, attended: int, total: int) -> AttendanceRecord:
    if attended < 0 or total < 0 or attended > total:
        raise ValueError("attended_classes must be between zero and total_classes")
    require_subject_owner(db, student_id, subject_id)
    profile = _profile(db, student_id)
    record = db.query(AttendanceRecord).filter_by(academic_profile_id=profile.id, subject_id=subject_id).first()
    if record is None:
        record = AttendanceRecord(student_id=student_id, academic_profile_id=profile.id, subject_id=subject_id)
        db.add(record)
    record.student_id = student_id
    record.attended_classes = attended
    record.total_classes = total
    record.attendance_percentage = round(attended * 100 / total, 2) if total else None
    record.last_updated = utc_now_naive()
    db.commit()
    db.refresh(record)
    return record


def update_attendance_record(db: Session, record_id: int, fields: dict) -> AttendanceRecord | None:
    record = db.query(AttendanceRecord).filter_by(id=record_id).first()
    if record is None:
        return None
    attended = fields.get("attended_classes", record.attended_classes)
    total = fields.get("total_classes", record.total_classes)
    if attended < 0 or total < 0 or attended > total:
        raise ValueError("attended_classes must be between zero and total_classes")
    record.attended_classes = attended
    record.total_classes = total
    record.attendance_percentage = round(attended * 100 / total, 2) if total else None
    record.last_updated = utc_now_naive()
    db.commit()
    db.refresh(record)
    return record


def attendance_summary(db: Session, student_id: int) -> list[dict]:
    return [
        {"record": record, "risk": attendance_risk(record.attendance_percentage),
         "classes_to_recover": classes_to_recover(record.attended_classes, record.total_classes)}
        for record in list_attendance(db, student_id)
    ]
