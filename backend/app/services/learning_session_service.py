"""Service for managing LearningSession records.

A LearningSession captures one unit of study activity (quiz, flashcard
review, revision, RAG question, etc.) together with its duration and score.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.learning_session import LearningSession


class LearningSessionService:
    def __init__(self, db: Session):
        self.db = db

    def create_session(
        self,
        student_id: int,
        subject_id: int,
        activity_type: str,
        duration_minutes: Optional[float] = None,
        score: Optional[float] = None,
    ) -> LearningSession:
        """Persist a new learning session."""
        session = LearningSession(
            student_id=student_id,
            subject_id=subject_id,
            activity_type=activity_type,
            duration_minutes=duration_minutes,
            score=score,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def list_for_student(
        self,
        student_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[LearningSession]:
        """Return all learning sessions for a student, newest first."""
        return (
            self.db.query(LearningSession)
            .filter(LearningSession.student_id == student_id)
            .order_by(LearningSession.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_session(self, session_id: int) -> Optional[LearningSession]:
        return (
            self.db.query(LearningSession)
            .filter(LearningSession.id == session_id)
            .first()
        )
