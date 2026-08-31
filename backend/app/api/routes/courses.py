from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.models import Course
from app.db.database import get_db

from app.services.course_service import (
    create_course,
    get_courses,
    get_course,
)

from app.schemas.course import (
    CourseCreate,
    CourseResponse,
    CourseWithSubjects,
)

router = APIRouter()


@router.post(
    "/courses",
    response_model=CourseResponse,
)
def create_course_endpoint(
    course: CourseCreate,
    db: Session = Depends(get_db),
):
    return create_course(
        db=db,
        name=course.name,
        description=course.description,
        student_id=course.student_id,
    )


@router.get(
    "/courses",
    response_model=list[CourseResponse],
)
def get_courses_endpoint(
    db: Session = Depends(get_db),
):
    return get_courses(db)


@router.get(
    "/courses/{course_id}",
    response_model=CourseResponse,
)
def get_course_endpoint(
    course_id: int,
    db: Session = Depends(get_db),
):
    course = get_course(
        db=db,
        course_id=course_id,
    )

    if course is None:
        raise HTTPException(
            status_code=404,
            detail="Course not found",
        )

    return course

@router.get(
    "/courses/{course_id}/subjects",
    response_model=CourseWithSubjects,
)
def get_course_subjects(
    course_id: int,
    db: Session = Depends(get_db),
):
    course = (
        db.query(Course)
        .filter(Course.id == course_id)
        .first()
    )

    if course is None:
        raise HTTPException(
            status_code=404,
            detail="Course not found",
        )

    return course