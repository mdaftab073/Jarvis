from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.api.student_scope import require_record_owner, require_student_scope
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
from app.core.config import settings

router = APIRouter()


@router.post(
    "/courses",
    response_model=CourseResponse,
)
def create_course_endpoint(
    course: CourseCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    require_student_scope(course.student_id, request, db)
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
    request: Request,
    db: Session = Depends(get_db),
):
    if settings.REQUIRE_AUTHENTICATED_STUDENT:
        principal_id = getattr(request.state, "student_id", None)
        if principal_id is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        return db.query(Course).filter(Course.student_id == principal_id).all()
    return get_courses(db)


@router.get(
    "/courses/{course_id}",
    response_model=CourseResponse,
)
def get_course_endpoint(
    course_id: int,
    request: Request,
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

    require_record_owner(request, course.student_id)

    return course

@router.get(
    "/courses/{course_id}/subjects",
    response_model=CourseWithSubjects,
)
def get_course_subjects(
    course_id: int,
    request: Request,
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

    require_record_owner(request, course.student_id)

    return course