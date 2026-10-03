"""Service layer for Topic CRUD operations.

Provides:
- create_topic
- get_topic
- get_topics
- get_subject_topics
- delete_topic
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models import Topic
from app.schemas.topic import TopicCreate

class TopicService:
    def __init__(self, db: Session):
        self.db = db

    def create_topic(self, subject_id: int, obj_in: TopicCreate) -> Topic:
        db_obj = Topic(
            subject_id=subject_id,
            name=obj_in.name,
            description=obj_in.description,
        )
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def get_topic(self, topic_id: int) -> Optional[Topic]:
        return self.db.query(Topic).filter(Topic.id == topic_id).first()

    def get_topics(self, skip: int = 0, limit: int = 100) -> List[Topic]:
        return self.db.query(Topic).offset(skip).limit(limit).all()

    def get_subject_topics(self, subject_id: int, skip: int = 0, limit: int = 100) -> List[Topic]:
        return (
            self.db.query(Topic)
            .filter(Topic.subject_id == subject_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def delete_topic(self, topic_id: int) -> None:
        obj = self.db.query(Topic).filter(Topic.id == topic_id).first()
        if obj:
            self.db.delete(obj)
            self.db.commit()
