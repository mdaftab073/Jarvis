from datetime import date, datetime

from pydantic import BaseModel, Field


class StudyPlanGenerateRequest(BaseModel):
    student_id: int
    subject_id: int
    exam_date: date
    hours_per_day: float = Field(gt=0, le=24)
    subject_difficulty: int = Field(default=3, ge=1, le=5)


class StudyTaskResponse(BaseModel):
    id: int
    day_number: int
    scheduled_date: date
    topic: str
    priority: int
    estimated_hours: float
    status: str


class DailyAgenda(BaseModel):
    day_number: int
    date: date
    tasks: list[StudyTaskResponse]


class PlanProgress(BaseModel):
    completion: int
    tasks_done: int
    tasks_remaining: int


class StudyPlanResponse(BaseModel):
    id: int
    student_id: int
    subject_id: int
    subject_name: str
    exam_date: date
    start_date: date
    hours_per_day: float
    created_at: datetime
    progress: PlanProgress
    daily_agenda: list[DailyAgenda]


class RecalculateResponse(StudyPlanResponse):
    rescheduled_tasks: int