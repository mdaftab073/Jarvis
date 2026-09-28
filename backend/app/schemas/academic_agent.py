from pydantic import BaseModel, Field


class AcademicAgentRequest(BaseModel):
    student_id: int
    goal: str = Field(min_length=1, max_length=2000)


class AcademicAgentResponse(BaseModel):
    summary: str
    priority_actions: list[str]
    recommended_topics: list[str]
    next_steps: list[str]


class AcademicAgentDebugResponse(AcademicAgentResponse):
    goal_type: str
    planned_actions: list[str]
    executed_actions: list[str]