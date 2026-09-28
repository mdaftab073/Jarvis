from pydantic import BaseModel, Field


class DirectorAcademicRequest(BaseModel):
    student_id: int
    goal: str = Field(min_length=1, max_length=2000)
    subject_id: int | None = None
    retrieval_question: str | None = Field(default=None, max_length=2000)
    hours_per_day: float | None = Field(default=None, gt=0, le=24)


class AgentResponse(BaseModel):
    agent_name: str
    summary: str
    recommendations: list[str]
    data: dict = Field(default_factory=dict)
    risks: list[dict] = Field(default_factory=list)


class DirectorAcademicResponse(AgentResponse):
    pass


class DirectorDebugResponse(DirectorAcademicResponse):
    goal_type: str
    selected_agents: list[str]
    execution_order: list[str]
    failures: list[dict]