from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

class FlashcardDeckBase(BaseModel):
    name: str = Field(..., max_length=255)

class FlashcardDeckCreate(FlashcardDeckBase):
    pass

class FlashcardDeck(FlashcardDeckBase):
    id: int
    subject_id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        orm_mode = True

class FlashcardBase(BaseModel):
    question: str
    answer: str
    difficulty: str = Field(default="medium", max_length=20)
    topic_id: Optional[int] = None

class FlashcardCreate(FlashcardBase):
    pass

class Flashcard(FlashcardBase):
    id: int
    deck_id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        orm_mode = True

