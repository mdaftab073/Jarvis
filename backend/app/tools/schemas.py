from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr


class ToolRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    db: Any = Field(default=None, exclude=True, repr=False)
    student_id: int | None = Field(default=None, gt=0)
    principal_id: int | None = Field(default=None, gt=0)
    subject_id: int | None = Field(default=None, gt=0)
    goal: str = ""
    start: datetime | None = None
    end: datetime | None = None
    start_time: datetime | None = None
    session_length: int = Field(default=50, gt=0)
    break_minutes: int = Field(default=10, ge=0)
    subject_ids: list[int] = Field(default_factory=list)
    hours_per_day: float | None = Field(default=None, gt=0)
    semester_id: int | None = Field(default=None, gt=0)
    generate_alerts: bool = False
    generate_reminders: bool = False
    include_completed: bool = True
    active_only: bool = True
    unread_only: bool = True
    parameters: dict[str, Any] = Field(default_factory=dict)
    action: str | None = None
    goal_id: int | None = Field(default=None, gt=0)
    habit_id: int | None = Field(default=None, gt=0)
    topic_id: int | None = Field(default=None, gt=0)
    deck_id: int | None = Field(default=None, gt=0)
    plan_id: int | None = Field(default=None, gt=0)
    exam_date: date | None = None
    count: int = Field(default=10, ge=1, le=100)
    limit: int = Field(default=100, ge=1, le=1000)
    include_practice: bool = False
    pending_only: bool = True
    question: str | None = None
    retrieval_question: str | None = None
    fields: dict[str, Any] = Field(default_factory=dict)

    def value(self, name: str, default: Any = None) -> Any:
        if name in self.parameters:
            return self.parameters[name]
        value = getattr(self, name, default)
        return default if value is None else value


class StudentToolRequest(ToolRequest):
    db: Any = Field(exclude=True, repr=False)
    student_id: int = Field(gt=0)


class SubjectToolRequest(StudentToolRequest):
    subject_id: int = Field(gt=0)


class ToolActionRequest(StudentToolRequest):
    action: str
    record_id: int | None = Field(default=None, gt=0)
    fields: dict[str, Any] = Field(default_factory=dict)


class ToolResponse(BaseModel):
    success: bool = True
    tool: str
    data: Any = Field(default_factory=dict)
    _raw_data: Any = PrivateAttr(default=None)


class ToolError(BaseModel):
    success: bool = False
    tool: str | None = None
    error: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


ToolErrorResponse = ToolError


class ToolMetadata(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]


class ToolRecordRequest(ToolRequest):
    record_id: int = Field(gt=0)


class ToolDateRangeRequest(ToolRequest):
    start_date: date | None = None
    end_date: date | None = None


class GoalToolRequest(StudentToolRequest):
    action: Literal["list", "create", "update", "delete"] = "list"
    goal_id: int | None = Field(default=None, gt=0)
    fields: dict[str, Any] = Field(default_factory=dict)


class HabitToolRequest(StudentToolRequest):
    action: Literal["list", "create", "log", "update", "delete"] = "list"
    habit_id: int | None = Field(default=None, gt=0)
    fields: dict[str, Any] = Field(default_factory=dict)


class StudyPlanToolRequest(StudentToolRequest):
    action: Literal["rank_topics", "generate", "get", "get_latest"] = "rank_topics"
    plan_id: int | None = Field(default=None, gt=0)
    subject_id: int | None = Field(default=None, gt=0)
    exam_date: date | None = None
    hours_per_day: float | None = Field(default=None, gt=0, le=24)


class RAGSearchRequest(ToolRequest):
    db: Any = Field(exclude=True, repr=False)
    question: str = Field(min_length=1)
    subject_id: int | None = Field(default=None, gt=0)