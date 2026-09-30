from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

class QuizSessionBase(BaseModel):
    student_id: int
    subject_id: int
    total_questions: int
    score: Optional[int] = None

class QuizSessionCreate(QuizSessionBase):
    pass

class QuizSession(QuizSessionBase):
    id: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        orm_mode = True

class QuizQuestionBase(BaseModel):
    topic_id: Optional[int] = None
    question: str
    question_type: str
    correct_answer: str

class QuizQuestionCreate(QuizQuestionBase):
    session_id: int

class QuizQuestion(QuizQuestionBase):
    id: int
    session_id: int

    class Config:
        from_attributes = True
        orm_mode = True

class QuizAnswerBase(BaseModel):
    question_id: int
    student_answer: str
    is_correct: bool

class QuizAnswerCreate(QuizAnswerBase):
    pass

class QuizAnswer(QuizAnswerBase):
    id: int
    answered_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        orm_mode = True

