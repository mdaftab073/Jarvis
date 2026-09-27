from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.analytics import (
    AnalyticsDashboard,
    PracticeStartRequest,
    PracticeStartResponse,
    PracticeQuestion,
    PracticeSubmitRequest,
    PracticeSubmitResponse,
    ReadinessResponse,
    TopicMastery,
)
from app.services.analytics_service import get_student_dashboard
from app.services.performance_service import (
    calculate_exam_readiness,
    complete_practice_session,
    create_practice_session,
    generate_personalized_recommendations,
    get_strong_topics,
    get_weak_topics,
)

router = APIRouter()


def _service_error(error: ValueError):
    status = 404 if "not found" in str(error).lower() else 422
    raise HTTPException(status_code=status, detail=str(error)) from error


@router.post("/practice/start", response_model=PracticeStartResponse)
def start_practice(
    request: PracticeStartRequest,
    db: Session = Depends(get_db),
):
    try:
        created = create_practice_session(
            db=db,
            student_id=request.student_id,
            subject_id=request.subject_id,
            count=request.count,
        )
    except ValueError as error:
        _service_error(error)
    return PracticeStartResponse(
        session_id=created["session"].id,
        student_id=created["session"].student_id,
        subject_id=created["session"].subject_id,
        started_at=created["session"].started_at,
        total_questions=len(created["attempts"]),
        questions=[
            PracticeQuestion(
                attempt_id=attempt.id,
                question=attempt.question_text,
                topic=attempt.topic or "General review",
                difficulty=attempt.difficulty,
            )
            for attempt in created["attempts"]
        ],
    )


@router.post("/practice/submit", response_model=PracticeSubmitResponse)
def submit_practice(
    request: PracticeSubmitRequest,
    db: Session = Depends(get_db),
):
    try:
        result = complete_practice_session(
            db=db,
            session_id=request.session_id,
            answers=[answer.model_dump() for answer in request.answers],
        )
    except ValueError as error:
        _service_error(error)
    return result


@router.get(
    "/analytics/dashboard/{student_id}",
    response_model=AnalyticsDashboard,
)
def student_dashboard(student_id: int, db: Session = Depends(get_db)):
    try:
        return get_student_dashboard(db, student_id)
    except ValueError as error:
        _service_error(error)


@router.get(
    "/analytics/readiness/{student_id}/{subject_id}",
    response_model=ReadinessResponse,
)
def subject_readiness(
    student_id: int,
    subject_id: int,
    db: Session = Depends(get_db),
):
    try:
        return calculate_exam_readiness(db, student_id, subject_id)
    except ValueError as error:
        _service_error(error)


@router.get("/analytics/weak-topics/{student_id}/{subject_id}")
def weak_topics(student_id: int, subject_id: int, db: Session = Depends(get_db)):
    try:
        return get_weak_topics(db, student_id, subject_id)
    except ValueError as error:
        _service_error(error)


@router.get("/analytics/strong-topics/{student_id}/{subject_id}")
def strong_topics(student_id: int, subject_id: int, db: Session = Depends(get_db)):
    try:
        return get_strong_topics(db, student_id, subject_id)
    except ValueError as error:
        _service_error(error)


@router.get("/analytics/recommendations/{student_id}/{subject_id}")
def recommendations(student_id: int, subject_id: int, db: Session = Depends(get_db)):
    try:
        return generate_personalized_recommendations(db, student_id, subject_id)
    except ValueError as error:
        _service_error(error)
