from pydantic import BaseModel


class ProfileResponse(BaseModel):
    student_id: int
    preferred_study_hours: float | None = None
    preferred_subjects: list[str]
    current_goal: str | None = None
    strengths: list[str]
    weaknesses: list[str]
    study_habits: list[str]
    readiness_trend: list[int]


class ProfileSummaryResponse(BaseModel):
    summary: str