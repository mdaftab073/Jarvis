from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator


class SemesterSubjectInput(BaseModel):
    subject_id: int
    target_score: float | None = Field(default=None, ge=0, le=100)


class SemesterCreateRequest(BaseModel):
    student_id: int
    semester_number: int = Field(gt=0)
    start_date: date
    end_date: date
    target_cgpa: float | None = Field(default=None, gt=0)
    subjects: list[SemesterSubjectInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        return self


class SemesterMilestoneCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    due_date: date
    description: str | None = Field(default=None, max_length=2000)
    completed: bool = False


class SemesterMilestoneUpdateRequest(BaseModel):
    completed: bool


class SemesterStatusUpdateRequest(BaseModel):
    status: str


class SemesterSubjectResponse(BaseModel):
    id: int
    subject_id: int
    subject_name: str
    target_score: float | None
    current_readiness: int


class SemesterMilestoneResponse(BaseModel):
    id: int
    semester_id: int
    title: str
    description: str | None
    due_date: date
    completed: bool
    completed_at: datetime | None
    created_at: datetime


class SemesterResponse(BaseModel):
    id: int
    student_id: int
    semester_number: int
    start_date: date
    end_date: date
    target_cgpa: float | None
    status: str
    created_at: datetime
    subjects: list[SemesterSubjectResponse]
    milestones: list[SemesterMilestoneResponse]
    progress: dict | None = None