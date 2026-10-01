"""Service for handling mastery tracking of topics per student."""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models import TopicMastery
from app.schemas.mastery_learning import MasteryCreate, Mastery as MasterySchema

class MasteryService:
    def __init__(self, db: Session):
        self.db = db

    def set_mastery(self, obj_in: MasteryCreate) -> TopicMastery:
        """Create or update mastery record for a student-topic pair."""
        mastery = (
            self.db.query(TopicMastery)
            .filter(
                TopicMastery.topic_id == obj_in.topic_id,
                TopicMastery.student_id == obj_in.student_id,
            )
            .first()
        )
        if mastery:
            mastery.mastery_score = obj_in.mastery_score
            mastery.attempt_count = (mastery.attempt_count or 0) + 1
        else:
            data = obj_in.model_dump()
            data.pop("last_reviewed_at", None)
            mastery = TopicMastery(**data, attempt_count=1)
            self.db.add(mastery)
        self.db.commit()
        self.db.refresh(mastery)
        return mastery

    def get_mastery(self, student_id: int, topic_id: int) -> Optional[TopicMastery]:
        return (
            self.db.query(TopicMastery)
            .filter(TopicMastery.student_id == student_id, TopicMastery.topic_id == topic_id)
            .first()
        )

    def list_mastery_for_student(self, student_id: int, skip: int = 0, limit: int = 100) -> List[TopicMastery]:
        return (
            self.db.query(TopicMastery)
            .filter(TopicMastery.student_id == student_id)
            .offset(skip)
            .limit(limit)
            .all()
        )
