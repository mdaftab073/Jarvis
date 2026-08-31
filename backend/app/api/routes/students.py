from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.database import get_db
from app.db.models import Student

from app.services.student_service import (
    create_student,
    update_student,
    delete_student,
)

from app.schemas.student import (
    StudentCreate,
    StudentUpdate,
    StudentResponse,
    StudentWithCourses,
)

router = APIRouter()


@router.post(
    "/students",
    response_model=StudentResponse,
)
def create_student_endpoint(
    student: StudentCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_student(
            db=db,
            name=student.name,
            email=student.email,
        )

    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Email already registered",
        )


@router.get(
    "/students",
    response_model=list[StudentResponse],
)
def get_students(
    db: Session = Depends(get_db),
):
    return db.query(Student).all()


@router.get(
    "/students/{student_id}",
    response_model=StudentResponse,
)
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
):
    student = (
        db.query(Student)
        .filter(Student.id == student_id)
        .first()
    )

    if student is None:
        raise HTTPException(
            status_code=404,
            detail="Student not found",
        )

    return student


@router.put(
    "/students/{student_id}",
    response_model=StudentResponse,
)
def update_student_endpoint(
    student_id: int,
    student: StudentUpdate,
    db: Session = Depends(get_db),
):
    try:
        updated_student = update_student(
            db=db,
            student_id=student_id,
            name=student.name,
            email=student.email,
        )

        if updated_student is None:
            raise HTTPException(
                status_code=404,
                detail="Student not found",
            )

        return updated_student

    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Email already registered",
        )


@router.delete(
    "/students/{student_id}",
)
def delete_student_endpoint(
    student_id: int,
    db: Session = Depends(get_db),
):
    deleted = delete_student(
        db=db,
        student_id=student_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Student not found",
        )

    return {
        "message": "Student deleted successfully"
    }
    
@router.get(
    "/students/{student_id}/courses",
    response_model=StudentWithCourses,
)
def get_student_courses(
    student_id: int,
    db: Session = Depends(get_db),
):
    student = (
        db.query(Student)
        .filter(Student.id == student_id)
        .first()
    )

    if student is None:
        raise HTTPException(
            status_code=404,
            detail="Student not found",
        )

    return student