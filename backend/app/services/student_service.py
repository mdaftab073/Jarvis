from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.models import Student


def create_student(
    db: Session,
    name: str,
    email: str,
):
    student = Student(
        name=name,
        email=email,
    )

    db.add(student)

    try:
        db.commit()

    except IntegrityError:
        db.rollback()
        raise

    db.refresh(student)

    return student


def update_student(
    db: Session,
    student_id: int,
    name: str,
    email: str,
):
    student = (
        db.query(Student)
        .filter(Student.id == student_id)
        .first()
    )

    if student is None:
        return None

    student.name = name
    student.email = email

    try:
        db.commit()

    except IntegrityError:
        db.rollback()
        raise

    db.refresh(student)

    return student


def delete_student(
    db: Session,
    student_id: int,
):
    student = (
        db.query(Student)
        .filter(Student.id == student_id)
        .first()
    )

    if student is None:
        return False

    db.delete(student)

    db.commit()

    return True