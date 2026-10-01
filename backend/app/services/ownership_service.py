from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from app.db.models import Course, StudentAcademicProfile, Subject


def student_owned_query(db: Session, model, student_id: int) -> Query:
    """Query student-owned rows, including legacy rows reachable through their profile."""
    query = db.query(model)
    if hasattr(model, "academic_profile"):
        return query.filter(
            or_(
                model.student_id == student_id,
                model.academic_profile.has(StudentAcademicProfile.student_id == student_id),
            )
        )
    return query.filter(model.student_id == student_id)


def student_id_for_profile(db: Session, profile_id: int) -> int:
    profile = db.query(StudentAcademicProfile).filter_by(id=profile_id).first()
    if profile is None:
        raise ValueError("Academic profile not found")
    return profile.student_id


def require_subject_owner(db: Session, student_id: int, subject_id: int | None) -> None:
    if subject_id is None:
        return
    exists = (
        db.query(Subject.id)
        .join(Course, Subject.course_id == Course.id)
        .filter(Subject.id == subject_id, Course.student_id == student_id)
        .first()
    )
    if exists is None:
        raise ValueError(f"Subject {subject_id} not found for student")
