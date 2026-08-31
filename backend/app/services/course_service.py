from sqlalchemy.orm import Session

from app.db.models import Course


def create_course(
    db: Session,
    name: str,
    description: str | None,
    student_id: int,
):
    course = Course(
        name=name,
        description=description,
        student_id=student_id,
    )

    db.add(course)
    db.commit()
    db.refresh(course)

    return course


def get_courses(
    db: Session,
):
    return db.query(Course).all()


def get_course(
    db: Session,
    course_id: int,
):
    return (
        db.query(Course)
        .filter(Course.id == course_id)
        .first()
    )