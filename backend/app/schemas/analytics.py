from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


PracticeDifficulty = Literal["Easy", "Medium", "Hard"]


class PracticeStartRequest(BaseModel):
    student_id: int
    subject_id: int
    count: int = Field(default=10, ge=1, le=30)


class PracticeQuestion(BaseModel):
    attempt_id: int
    question: str
    topic: str
    difficulty: PracticeDifficulty
    marks: float | None = None


class PracticeStartResponse(BaseModel):
    session_id: int
    student_id: int
    subject_id: int
    started_at: datetime
    total_questions: int
    questions: list[PracticeQuestion]


class PracticeAnswer(BaseModel):
    attempt_id: int
    student_answer: str = Field(max_length=12000)
    confidence_score: float = Field(default=50, ge=0, le=100)


class PracticeSubmitRequest(BaseModel):
    session_id: int
    answers: list[PracticeAnswer] = Field(min_length=1, max_length=30)


class GradedPracticeAnswer(BaseModel):
    attempt_id: int
    topic: str
    is_correct: bool
    score: float
    feedback: str


class PracticeSubmitResponse(BaseModel):
    session_id: int
    score: float
    total_questions: int
    correct_answers: int
    accuracy: float
    duration_seconds: int
    topic_coverage: list[str]
    results: list[GradedPracticeAnswer]


class TopicMastery(BaseModel):
    topic: str
    attempts: int
    correct_answers: int
    incorrect_answers: int
    confidence_score: float
    mastery_score: float
    last_practiced_at: datetime | None


class ReadinessResponse(BaseModel):
    student_id: int
    subject_id: int
    readiness_score: int
    status: str
    topic_mastery: list[TopicMastery]
    plan_completion: int
    pyq_coverage: int


class AnalyticsDashboard(BaseModel):
    student_id: int
    readiness_score: int
    status: str
    plan_completion: int
    weak_topics: list[dict]
    strong_topics: list[dict]
    recommendations: list[str]
    subjects: list[dict]
    practice_score_trend: list[dict]
