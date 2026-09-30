"""Phase 14 – Learning Session routes.

Endpoints:
  POST /learning/session
  GET  /learning/history/{student_id}
  GET  /learning/insights/{student_id}
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db.database import get_db
from app.services.learning_session_service import LearningSessionService
from app.services.mastery_service import MasteryService
from app.models import Topic

router = APIRouter(tags=["Learning"])

VALID_ACTIVITY_TYPES = {
    "rag_question",
    "quiz",
    "flashcard_review",
    "revision",
    "study_session",
}


class LearningSessionCreate(BaseModel):
    student_id: int = Field(..., ge=1)
    subject_id: int = Field(..., ge=1)
    activity_type: str = Field(..., description="One of: rag_question, quiz, flashcard_review, revision, study_session")
    duration_minutes: Optional[float] = Field(None, ge=0)
    score: Optional[float] = Field(None, ge=0, le=100)


class LearningSessionResponse(BaseModel):
    id: int
    student_id: int
    subject_id: int
    activity_type: str
    duration_minutes: Optional[float]
    score: Optional[float]
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        orm_mode = True


class TopicInsight(BaseModel):
    topic_id: int
    topic_name: str
    mastery_score: float
    attempt_count: int


class LearningInsightsResponse(BaseModel):
    student_id: int
    weak_topics: List[TopicInsight]
    strong_topics: List[TopicInsight]
    average_mastery: float
    total_sessions: int
    total_time_minutes: float
    activity_breakdown: dict
    recommended_actions: List[str]
    overall_readiness: str


@router.post("/learning/session", response_model=LearningSessionResponse)
def create_learning_session(
    payload: LearningSessionCreate,
    db: Session = Depends(get_db),
):
    """Record a new learning session."""
    if payload.activity_type not in VALID_ACTIVITY_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"activity_type must be one of: {sorted(VALID_ACTIVITY_TYPES)}",
        )
    svc = LearningSessionService(db)
    session = svc.create_session(
        student_id=payload.student_id,
        subject_id=payload.subject_id,
        activity_type=payload.activity_type,
        duration_minutes=payload.duration_minutes,
        score=payload.score,
    )
    return session


@router.get("/learning/history/{student_id}", response_model=List[LearningSessionResponse])
def get_learning_history(
    student_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Return a student's learning session history, newest first."""
    svc = LearningSessionService(db)
    return svc.list_for_student(student_id=student_id, skip=skip, limit=limit)


@router.get("/learning/insights/{student_id}", response_model=LearningInsightsResponse)
def get_learning_insights(
    student_id: int,
    db: Session = Depends(get_db),
):
    """Return a personalised learning analysis for the student.

    Aggregates mastery data, session history, and generates actionable
    recommendations without calling any external LLM.
    """
    svc = LearningSessionService(db)
    mastery_svc = MasteryService(db)

    sessions = svc.list_for_student(student_id=student_id, limit=1000)
    mastery_records = mastery_svc.list_mastery_for_student(
        student_id=student_id, limit=1000
    )

    # Enrich mastery records with topic names
    topic_map: dict = {}
    for m in mastery_records:
        if m.topic_id not in topic_map:
            t = db.query(Topic).filter(Topic.id == m.topic_id).first()
            topic_map[m.topic_id] = t.name if t else f"Topic {m.topic_id}"

    weak = [m for m in mastery_records if m.mastery_score < 50.0]
    strong = [m for m in mastery_records if m.mastery_score >= 75.0]
    weak.sort(key=lambda x: x.mastery_score)
    strong.sort(key=lambda x: x.mastery_score, reverse=True)

    avg_mastery = (
        round(sum(m.mastery_score for m in mastery_records) / len(mastery_records), 2)
        if mastery_records
        else 0.0
    )

    total_time = sum(
        (s.duration_minutes or 0) for s in sessions
    )

    activity_breakdown: dict = {}
    for s in sessions:
        activity_breakdown[s.activity_type] = (
            activity_breakdown.get(s.activity_type, 0) + 1
        )

    # Simple rule-based recommendations
    recommendations: List[str] = []
    if weak:
        top_weak = weak[:3]
        for m in top_weak:
            recommendations.append(
                f"Review and practice '{topic_map.get(m.topic_id, 'topic')}' "
                f"(current mastery: {m.mastery_score:.0f}%)"
            )
    if avg_mastery < 40:
        recommendations.append(
            "Overall mastery is low. Consider scheduling dedicated study sessions."
        )
    if activity_breakdown.get("quiz", 0) == 0:
        recommendations.append(
            "You haven't taken any quizzes yet. Quizzes are a great way to test retention."
        )
    if activity_breakdown.get("flashcard_review", 0) == 0:
        recommendations.append(
            "Try using flashcards to reinforce key concepts."
        )
    if total_time < 60:
        recommendations.append(
            "Increase total study time. Aim for at least 1 hour of active learning."
        )

    # Determine overall readiness
    if avg_mastery >= 75:
        readiness = "HIGH"
    elif avg_mastery >= 50:
        readiness = "MEDIUM"
    else:
        readiness = "LOW"

    return LearningInsightsResponse(
        student_id=student_id,
        weak_topics=[
            TopicInsight(
                topic_id=m.topic_id,
                topic_name=topic_map.get(m.topic_id, "Unknown"),
                mastery_score=m.mastery_score,
                attempt_count=m.attempt_count,
            )
            for m in weak[:10]
        ],
        strong_topics=[
            TopicInsight(
                topic_id=m.topic_id,
                topic_name=topic_map.get(m.topic_id, "Unknown"),
                mastery_score=m.mastery_score,
                attempt_count=m.attempt_count,
            )
            for m in strong[:10]
        ],
        average_mastery=avg_mastery,
        total_sessions=len(sessions),
        total_time_minutes=round(total_time, 2),
        activity_breakdown=activity_breakdown,
        recommended_actions=recommendations,
        overall_readiness=readiness,
    )
