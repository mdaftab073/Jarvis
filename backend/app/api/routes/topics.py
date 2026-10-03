"""Phase 14 – Topics routes.

Endpoints:
  GET  /topics
  GET  /topics/{topic_id}
  GET  /subjects/{subject_id}/topics
  POST /topics/extract/{material_id}
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Course, StudyMaterial, Subject
from app.api.student_scope import require_record_owner
from app.services.topic_service import TopicService
from app.services.topic_extraction_service import TopicExtractionService
from app.schemas.topic import Topic
from app.models import Topic as TopicModel

router = APIRouter(tags=["Topics"])


@router.get("/topics", response_model=List[Topic])
def list_topics(
    request: Request,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Return all topics with optional pagination."""
    student_id = getattr(request.state, "student_id", None)
    if student_id is None:
        return TopicService(db).get_topics(skip=skip, limit=limit)
    return (
        db.query(TopicModel)
        .join(Subject, TopicModel.subject_id == Subject.id)
        .join(Course, Subject.course_id == Course.id)
        .filter(Course.student_id == student_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/topics/{topic_id}", response_model=Topic)
def get_topic(
    topic_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Return a single topic by ID."""
    topic = db.query(TopicModel).filter_by(id=topic_id).first()
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    subject = db.query(Subject).filter_by(id=topic.subject_id).first()
    if subject is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    require_record_owner(request, subject.course.student_id)
    return topic


@router.get("/subjects/{subject_id}/topics", response_model=List[Topic])
def list_subject_topics(
    subject_id: int,
    request: Request,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Return all topics that belong to a specific subject."""
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")
    require_record_owner(request, subject.course.student_id)
    return TopicService(db).get_subject_topics(
        subject_id=subject_id, skip=skip, limit=limit
    )


@router.post("/topics/extract/{material_id}", response_model=List[Topic])
def extract_topics(
    material_id: int,
    request: Request,
    subject_id: int = Query(..., ge=1, description="Subject to associate extracted topics with"),
    db: Session = Depends(get_db),
):
    """Use an LLM to extract topics from a study material and persist them."""
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")
    material = (
        db.query(StudyMaterial)
        .filter_by(id=material_id, subject_id=subject_id)
        .first()
    )
    if material is None:
        raise HTTPException(status_code=404, detail="Material not found")
    require_record_owner(request, subject.course.student_id)
    try:
        svc = TopicExtractionService(db)
        topics = svc.extract_and_store(material_id=material_id, subject_id=subject_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return topics
