"""Phase 14 – Quizzes routes.

Endpoints:
  POST /quizzes/generate
  POST /quizzes/submit
  GET  /quizzes/history/{student_id}
  GET  /quizzes/session/{session_id}
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, Field

from app.api.student_scope import require_record_owner, require_student_scope
from app.db.database import get_db
from app.services.quiz_service import QuizService
from app.services.mastery_service import MasteryService
from app.services.ownership_service import require_subject_owner
from app.schemas.quiz import (
    QuizSession,
    QuizSessionCreate,
    QuizQuestion,
    QuizQuestionCreate,
    QuizAnswer,
    QuizAnswerCreate,
)
from app.schemas.mastery_learning import MasteryCreate
from app.services.time_service import utc_now_naive

router = APIRouter(tags=["Quizzes"])


class QuestionInput(BaseModel):
    topic_id: Optional[int] = None
    question: str
    question_type: str = Field(default="short_answer", description="MCQ, true_false, short_answer")
    correct_answer: str


class QuizGenerateRequest(BaseModel):
    student_id: int = Field(..., ge=1)
    subject_id: int = Field(..., ge=1)
    questions: List[QuestionInput] = Field(..., min_items=1)


class AnswerSubmission(BaseModel):
    question_id: int
    student_answer: str


class QuizSubmitRequest(BaseModel):
    session_id: int = Field(..., ge=1)
    answers: List[AnswerSubmission] = Field(..., min_items=1)
    update_mastery: bool = Field(default=True, description="Whether to update topic mastery scores")


class AnswerResult(BaseModel):
    question_id: int
    is_correct: bool
    correct_answer: str
    student_answer: str


class QuizSubmitResponse(BaseModel):
    session_id: int
    score: int
    total_questions: int
    results: List[AnswerResult]


class QuizSessionWithQuestions(BaseModel):
    session: QuizSession
    questions: List[QuizQuestion]

    model_config = ConfigDict(from_attributes=True)


@router.post("/quizzes/generate", response_model=QuizSessionWithQuestions)
def generate_quiz(
    payload: QuizGenerateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create a new quiz session with the given questions."""
    require_student_scope(payload.student_id, request, db)
    require_subject_owner(db, payload.student_id, payload.subject_id)
    svc = QuizService(db)
    session = svc.create_session(
        QuizSessionCreate(
            student_id=payload.student_id,
            subject_id=payload.subject_id,
            total_questions=len(payload.questions),
        )
    )
    questions = []
    for q in payload.questions:
        question = svc.add_question(
            session_id=session.id,
            obj_in=QuizQuestionCreate(
                session_id=session.id,
                topic_id=q.topic_id,
                question=q.question,
                question_type=q.question_type,
                correct_answer=q.correct_answer,
            ),
        )
        questions.append(question)
    return QuizSessionWithQuestions(session=session, questions=questions)


@router.post("/quizzes/submit", response_model=QuizSubmitResponse)
def submit_quiz(
    payload: QuizSubmitRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Submit answers for a quiz session and get scored results."""
    svc = QuizService(db)
    session = svc.get_session(payload.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Quiz session not found")
    require_record_owner(request, session.student_id)

    # Build question lookup
    questions = svc.get_questions(session_id=payload.session_id)
    q_map = {q.id: q for q in questions}

    results = []
    correct_count = 0
    mastery_svc = MasteryService(db)

    for ans in payload.answers:
        q = q_map.get(ans.question_id)
        if q is None:
            raise HTTPException(
                status_code=404,
                detail=f"Question {ans.question_id} not found in session {payload.session_id}",
            )
        is_correct = ans.student_answer.strip().lower() == q.correct_answer.strip().lower()
        if is_correct:
            correct_count += 1
        svc.submit_answer(
            question_id=q.id,
            obj_in=QuizAnswerCreate(
                question_id=q.id,
                student_answer=ans.student_answer,
                is_correct=is_correct,
            ),
        )
        results.append(
            AnswerResult(
                question_id=q.id,
                is_correct=is_correct,
                correct_answer=q.correct_answer,
                student_answer=ans.student_answer,
            )
        )
        # Update mastery for topics that have a topic_id
        if payload.update_mastery and q.topic_id:
            existing = mastery_svc.get_mastery(
                student_id=session.student_id, topic_id=q.topic_id
            )
            prev_score = existing.mastery_score if existing else 0.0
            # Exponential moving average mastery update (alpha=0.3)
            new_score = round(prev_score * 0.7 + (100.0 if is_correct else 0.0) * 0.3, 2)
            mastery_svc.set_mastery(
                MasteryCreate(
                    student_id=session.student_id,
                    topic_id=q.topic_id,
                    mastery_score=new_score,
                    last_reviewed_at=utc_now_naive().isoformat(),
                )
            )

    # Persist score on session
    session.score = correct_count
    session.completed_at = utc_now_naive()
    db.commit()
    db.refresh(session)

    return QuizSubmitResponse(
        session_id=session.id,
        score=correct_count,
        total_questions=session.total_questions,
        results=results,
    )


@router.get("/quizzes/history/{student_id}", response_model=List[QuizSession])
def get_quiz_history(
    student_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _scope: int = Depends(require_student_scope),
):
    """Return all quiz sessions for a student."""
    return QuizService(db).list_sessions(
        student_id=student_id, skip=skip, limit=limit
    )


@router.get("/quizzes/session/{session_id}", response_model=QuizSessionWithQuestions)
def get_quiz_session(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Return a quiz session and its questions."""
    svc = QuizService(db)
    session = svc.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Quiz session not found")
    require_record_owner(request, session.student_id)
    questions = svc.get_questions(session_id=session_id)
    return QuizSessionWithQuestions(session=session, questions=questions)
