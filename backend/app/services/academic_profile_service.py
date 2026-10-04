from sqlalchemy.orm import Session

from app.db.models import AttendanceRecord, DeadlineItem, GradeRecord, Student, StudentAcademicProfile
from app.services.grade_service import grade_analytics


def get_profile(db: Session, student_id: int) -> StudentAcademicProfile | None:
    return db.query(StudentAcademicProfile).filter_by(student_id=student_id).first()


def create_or_update_profile(db: Session, student_id: int, fields: dict) -> StudentAcademicProfile:
    if db.query(Student).filter_by(id=student_id).first() is None:
        raise ValueError("Student not found")
    profile = get_profile(db, student_id)
    if profile is None:
        profile = StudentAcademicProfile(student_id=student_id)
        db.add(profile)
    fields = dict(fields)
    legacy_department = fields.pop("department", None)
    if "branch" not in fields and legacy_department is not None:
        fields["branch"] = legacy_department
    for key, value in fields.items():
        if hasattr(profile, key) and key not in {
            "id",
            "student_id",
            "created_at",
            "updated_at",
            "department",
        }:
            setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return profile


def academic_summary(db: Session, student_id: int) -> dict:
    profile = get_profile(db, student_id)
    if profile is None:
        return {"profile": None, "attendance_count": 0, "grade_count": 0, "pending_deadline_count": 0}
    return {
        "profile": profile,
        "attendance_count": db.query(AttendanceRecord).filter_by(academic_profile_id=profile.id).count(),
        "grade_count": db.query(GradeRecord).filter_by(academic_profile_id=profile.id).count(),
        "grade_analytics": grade_analytics(db, student_id),
        "pending_deadline_count": db.query(DeadlineItem).filter_by(academic_profile_id=profile.id, is_completed=False).count(),
    }
