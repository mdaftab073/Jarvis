"""Service for handling Quiz sessions, questions, and answers using the database."""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models import QuizSession, QuizQuestion, QuizAnswer
from app.schemas.quiz import (
    QuizSessionCreate,
    QuizQuestionCreate,
    QuizAnswerCreate,
    QuizSession as QuizSessionSchema,
    QuizQuestion as QuizQuestionSchema,
    QuizAnswer as QuizAnswerSchema,
)

class QuizService:
    def __init__(self, db: Session):
        self.db = db

    # QuizSession operations
    def create_session(self, obj_in: QuizSessionCreate) -> QuizSession:
        session = QuizSession(**obj_in.model_dump())
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_session(self, session_id: int) -> Optional[QuizSession]:
        return self.db.query(QuizSession).filter(QuizSession.id == session_id).first()

    def list_sessions(self, student_id: int, skip: int = 0, limit: int = 100) -> List[QuizSession]:
        return (
            self.db.query(QuizSession)
            .filter(QuizSession.student_id == student_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    # QuizQuestion operations
    def add_question(self, session_id: int, obj_in: QuizQuestionCreate) -> QuizQuestion:
        question = QuizQuestion(session_id=session_id, **obj_in.model_dump(exclude={"session_id"}))
        self.db.add(question)
        self.db.commit()
        self.db.refresh(question)
        return question

    def get_questions(self, session_id: int, skip: int = 0, limit: int = 100) -> List[QuizQuestion]:
        return (
            self.db.query(QuizQuestion)
            .filter(QuizQuestion.session_id == session_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    # QuizAnswer operations
    def submit_answer(self, question_id: int, obj_in: QuizAnswerCreate) -> QuizAnswer:
        answer = QuizAnswer(question_id=question_id, **obj_in.model_dump(exclude={"question_id"}))
        self.db.add(answer)
        self.db.commit()
        self.db.refresh(answer)
        return answer

    def get_answers(self, question_id: int) -> List[QuizAnswer]:
        return self.db.query(QuizAnswer).filter(QuizAnswer.question_id == question_id).all()
