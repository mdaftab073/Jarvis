from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    session_id: int | None = Field(default=None, gt=0)
    student_id: int | None = Field(default=None, gt=0)
    message: str = Field(min_length=1, max_length=8000)


class ChatResponse(BaseModel):
    session_id: int
    user_message_id: int
    assistant_message_id: int
    answer: str
    agent_used: str
    tool_used: str | None = None
    created_at: datetime


class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    title: str
    created_at: datetime
    updated_at: datetime


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    role: str
    content: str
    agent_name: str | None = None
    tool_name: str | None = None
    metadata_json: dict
    created_at: datetime


class CreateSessionRequest(BaseModel):
    student_id: int = Field(gt=0)
    title: str | None = Field(default=None, max_length=255)