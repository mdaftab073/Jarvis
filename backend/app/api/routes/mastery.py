"""Phase 14 – Mastery routes.

Endpoints:
  GET /mastery/student/{student_id}
  GET /mastery/subject/{subject_id}
  GET /mastery/weak/{student_id}
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict

from app.api.student_scope import require_student_scope
from app.db.database import get_db
from app.services.mastery_service import MasteryService
from app.services.ownership_service import require_subject_owner
from app.models import TopicMastery, Topic

router = APIRouter(tags=["Mastery"])

WEAK_THRESHOLD = 50.0   # mastery_score below this is "weak"
STRONG_THRESHOLD = 75.0  # mastery_score above this is "strong"


class MasteryWithTopic(BaseModel):
    id: int
    student_id: int
    topic_id: int
    topic_name: str
    mastery_score: float
    attempt_count: int

    model_config = ConfigDict(from_attributes=True)


def _enrich(mastery_obj: TopicMastery, db: Session) -> MasteryWithTopic:
    topic = db.query(Topic).filter(Topic.id == mastery_obj.topic_id).first()
    topic_name = topic.name if topic else "Unknown"
    return MasteryWithTopic(
        id=mastery_obj.id,
        student_id=mastery_obj.student_id,
        topic_id=mastery_obj.topic_id,
        topic_name=topic_name,
        mastery_score=mastery_obj.mastery_score,
        attempt_count=mastery_obj.attempt_count,
    )


@router.get("/mastery/student/{student_id}", response_model=List[MasteryWithTopic])
def get_student_mastery(
    student_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _scope: int = Depends(require_student_scope),
):
    """Return all topic mastery records for a student."""
    records = MasteryService(db).list_mastery_for_student(
        student_id=student_id, skip=skip, limit=limit
    )
    return [_enrich(r, db) for r in records]


@router.get("/mastery/subject/{subject_id}", response_model=List[MasteryWithTopic])
def get_subject_mastery(
    subject_id: int,
    request: Request,
    student_id: int = Query(..., ge=1, description="Student to filter mastery for"),
    db: Session = Depends(get_db),
    _scope: int = Depends(require_student_scope),
):
    """Return mastery scores for all topics within a subject for a specific student."""
    try:
        require_subject_owner(db, student_id, subject_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail="Subject not found") from error
    topics = db.query(Topic).filter(Topic.subject_id == subject_id).all()
    topic_ids = {t.id for t in topics}
    topic_map = {t.id: t.name for t in topics}

    svc = MasteryService(db)
    all_mastery = svc.list_mastery_for_student(student_id=student_id, limit=1000)
    filtered = [m for m in all_mastery if m.topic_id in topic_ids]
    return [
        MasteryWithTopic(
            id=m.id,
            student_id=m.student_id,
            topic_id=m.topic_id,
            topic_name=topic_map.get(m.topic_id, "Unknown"),
            mastery_score=m.mastery_score,
            attempt_count=m.attempt_count,
        )
        for m in filtered
    ]


@router.get("/mastery/weak/{student_id}", response_model=List[MasteryWithTopic])
def get_weak_topics(
    student_id: int,
    threshold: float = Query(default=WEAK_THRESHOLD, ge=0.0, le=100.0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _scope: int = Depends(require_student_scope),
):
    """Return topics where a student's mastery score is below the threshold (default 50)."""
    records = MasteryService(db).list_mastery_for_student(
        student_id=student_id, limit=1000
    )
    weak = [r for r in records if r.mastery_score < threshold]
    weak.sort(key=lambda x: x.mastery_score)
    return [_enrich(r, db) for r in weak[:limit]]
