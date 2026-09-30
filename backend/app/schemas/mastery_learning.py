from typing import Optional
from pydantic import BaseModel, Field

class MasteryBase(BaseModel):
    topic_id: int
    student_id: int
    mastery_score: float = Field(..., ge=0.0, le=100.0)
    last_reviewed_at: Optional[str] = None

class MasteryCreate(MasteryBase):
    pass

class Mastery(MasteryBase):
    id: int

    class Config:
        from_attributes = True
        orm_mode = True

class LearningSessionBase(BaseModel):
    student_id: int
    subject_id: int
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    notes: Optional[str] = None

class LearningSessionCreate(LearningSessionBase):
    pass

class LearningSession(LearningSessionBase):
    id: int

    class Config:
        from_attributes = True
        orm_mode = True

