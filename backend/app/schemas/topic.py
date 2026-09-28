"""Pydantic schemas for Topic model.

Used by FastAPI request/response models.
"""

from typing import Optional

from pydantic import BaseModel, Field

class TopicBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None

class TopicCreate(TopicBase):
    pass

class TopicUpdate(TopicBase):
    pass

class TopicInDBBase(TopicBase):
    id: int
    subject_id: int

    class Config:
        orm_mode = True

class Topic(TopicInDBBase):
    pass
