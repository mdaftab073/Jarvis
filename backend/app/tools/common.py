from app.db.models import Course, Student, Subject
from app.tools.exceptions import ToolOwnershipError, ToolValidationError


def require_student(payload, tool_name: str):
    db = getattr(payload, "db", None)
    student_id = getattr(payload, "student_id", None)
    if db is None or student_id is None:
        raise ToolValidationError(tool_name, "A database session and student_id are required")
    if db.query(Student.id).filter_by(id=student_id).first() is None:
        raise ToolValidationError(tool_name, "Student not found")
    principal_id = getattr(payload, "principal_id", None)
    if principal_id is not None and principal_id != student_id:
        raise ToolOwnershipError()
    return db, student_id


def require_subject_owner(db, student_id: int, subject_id: int, tool_name: str):
    subject = (
        db.query(Subject)
        .join(Course, Course.id == Subject.course_id)
        .filter(Subject.id == subject_id, Course.student_id == student_id)
        .first()
    )
    if subject is None:
        raise ToolOwnershipError(f"Subject does not belong to student {student_id}")
    return subject