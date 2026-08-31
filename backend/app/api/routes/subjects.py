from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db

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
    db: Session = Depends(get_db),
):
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
    db: Session = Depends(get_db),
):
    return get_subjects(db)


@router.get(
    "/subjects/{subject_id}",
    response_model=SubjectResponse,
)
def get_subject_endpoint(
    subject_id: int,
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

    return subject