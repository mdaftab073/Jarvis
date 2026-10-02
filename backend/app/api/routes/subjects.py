from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.student_scope import require_record_owner, require_student_scope
from app.db.database import get_db
from app.db.models import Course, Subject
from app.core.config import settings

from app.schemas.subject import (
    SubjectCreate,
    SubjectResponse,
)

from app.services.subject_service import (
    create_subject,
    get_subject,
    get_subjects,
)

router = APIRouter()


@router.post(
    "/subjects",
    response_model=SubjectResponse,
)
def create_subject_endpoint(
    subject: SubjectCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    owner_id = db.query(Course.student_id).filter_by(id=subject.course_id).scalar()
    if owner_id is None:
        raise HTTPException(status_code=404, detail="Course not found")
    require_student_scope(owner_id, request, db)
    return create_subject(
        db=db,
        name=subject.name,
        description=subject.description,
        course_id=subject.course_id,
    )


@router.get(
    "/subjects",
    response_model=list[SubjectResponse],
)
def get_subjects_endpoint(
    request: Request,
    db: Session = Depends(get_db),
):
    if settings.REQUIRE_AUTHENTICATED_STUDENT:
        principal_id = getattr(request.state, "student_id", None)
        if principal_id is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        return (
            db.query(Subject)
            .join(Course)
            .filter(Course.student_id == principal_id)
            .all()
        )
    return get_subjects(db)


@router.get(
    "/subjects/{subject_id}",
    response_model=SubjectResponse,
)
def get_subject_endpoint(
    subject_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    subject = get_subject(
        db=db,
        subject_id=subject_id,
    )

    if subject is None:
        raise HTTPException(
            status_code=404,
            detail="Subject not found",
        )

    require_record_owner(request, subject.course.student_id)

    return subject