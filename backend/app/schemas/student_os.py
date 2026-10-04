from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, Field, model_validator


class ProfileInput(BaseModel):
    enrollment_number: str | None = None
    branch: str | None = None
    semester: int | None = Field(None, ge=1)
    section: str | None = None
    batch_year: int | None = None
    current_cpi: float | None = Field(None, ge=0, le=10)
    current_spi: float | None = Field(None, ge=0, le=10)
    earned_credits: int | None = Field(None, ge=0)
    total_credits: int | None = Field(None, ge=0)
    academic_status: Literal["ACTIVE", "PROBATION", "GRADUATED", "SUSPENDED", "DROPOUT"] | None = None

    @model_validator(mode="before")
    @classmethod
    def map_legacy_department(cls, values):
        if isinstance(values, dict) and "department" in values:
            values = dict(values)
            if not values.get("branch"):
                values["branch"] = values["department"]
            values.pop("department")
        return values


class AttendanceInput(BaseModel):
    subject_id: int
    attended_classes: int = Field(ge=0)
    total_classes: int = Field(ge=0)


class GradeInput(BaseModel):
    subject_id: int
    semester: int | None = Field(None, ge=1)
    credits: float | None = Field(None, ge=0)
    grade: str | None = None
    grade_points: float | None = Field(None, ge=0, le=10)
    grade_type: Literal["COMPONENT", "FINAL"] = "COMPONENT"
    component_type: Literal["CT1", "CT2", "CT3", "ASSIGNMENT", "LAB", "END_SEM", "MID_SEM", "VIVA", "PROJECT", "OTHER"] = "OTHER"
    obtained_marks: float | None = Field(None, ge=0)
    max_marks: float = Field(default=100, gt=0)
    grade_letter: str | None = None

    @model_validator(mode="after")
    def validate_final_grade(self):
        if self.grade_type == "FINAL" and (
            self.semester is None or self.credits is None or self.credits <= 0 or self.grade_points is None
        ):
            raise ValueError("FINAL grades require semester, positive credits, and grade_points")
        return self


class DeadlineInput(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    type: Literal["EXAM", "ASSIGNMENT", "PROJECT", "LAB_SUBMISSION", "QUIZ", "PRESENTATION", "OTHER"] = "OTHER"
    due_date: datetime
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"
    subject_id: int | None = None


class NotificationInput(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    message: str
    notification_type: Literal["INFO", "SUCCESS", "WARNING", "CRITICAL", "REMINDER"] = "INFO"


class CalendarEventInput(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    start_time: datetime
    end_time: datetime
    event_type: str = "OTHER"


class StudyBlockInput(BaseModel):
    subject_id: int | None = None
    title: str | None = Field(None, max_length=255)
    block_type: Literal["STUDY", "REVISION", "ATTENDANCE_RECOVERY", "DEADLINE_PREP", "GOAL"] = "STUDY"
    start_time: datetime
    end_time: datetime
    planned_duration: int | None = Field(None, ge=0)


class ScheduleInput(BaseModel):
    subject_ids: list[int]
    start_time: datetime
    session_length: int = Field(default=50, gt=0)
    break_minutes: int = Field(default=10, ge=0)


class IntelligentScheduleInput(BaseModel):
    start_time: datetime
    available_hours: float = Field(gt=0, le=16)
    horizon_days: int = Field(default=7, ge=1, le=14)
    session_minutes: int = Field(default=45, ge=15, le=180)


class PreferenceInput(BaseModel):
    preferred_study_time: str | None = None
    preferred_session_length: int | None = Field(None, gt=0)
    study_style: str | None = None


class ReminderInput(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    trigger_time: datetime


class DeadlineCompletionInput(BaseModel):
    completed: bool


class GoalCreateInput(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    goal_type: Literal["SEMESTER", "CPI", "ATTENDANCE", "PLACEMENT", "STUDY_HOURS"]
    target_value: float | None = Field(None, ge=0)
    target_unit: str | None = Field(None, max_length=30)
    target_date: date | None = None


class GoalUpdateInput(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    goal_type: Literal["SEMESTER", "CPI", "ATTENDANCE", "PLACEMENT", "STUDY_HOURS"] | None = None
    target_value: float | None = Field(None, ge=0)
    target_unit: str | None = Field(None, max_length=30)
    target_date: date | None = None
    completed: bool | None = None


class MilestoneInput(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    target_value: float | None = Field(None, ge=0)
    target_date: date | None = None


class ProgressInput(BaseModel):
    progress_value: float = Field(ge=0)
    notes: str | None = None


class HabitCreateInput(BaseModel):
    habit_name: str = Field(min_length=1, max_length=120)
    category: Literal["DAILY_STUDY", "REVISION", "PYQ_PRACTICE", "ATTENDANCE_CHECK", "ASSIGNMENT_COMPLETION"]
    target_per_week: int = Field(default=7, ge=1, le=7)


class HabitUpdateInput(BaseModel):
    habit_name: str | None = Field(None, min_length=1, max_length=120)
    category: Literal["DAILY_STUDY", "REVISION", "PYQ_PRACTICE", "ATTENDANCE_CHECK", "ASSIGNMENT_COMPLETION"] | None = None
    target_per_week: int | None = Field(None, ge=1, le=7)
    active: bool | None = None


class HabitLogInput(BaseModel):
    log_date: date | None = None
    completed: bool = True
    duration_minutes: int | None = Field(None, ge=0)
    notes: str | None = None
