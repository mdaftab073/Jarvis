from typing import Any, Literal

from pydantic import BaseModel


class AskRequest(BaseModel):

    question: str

    subject_id: int | None = None

class SourceItem(BaseModel):
    material_id: int
    title: str
    chunk_index: int


class RetrievalDebug(BaseModel):
    chunks_used: int
    subject_detected: str | None = None


class RetrievalResult(BaseModel):
    id: str
    document: str
    metadata: dict[str, Any]
    score: float
    source: Literal["vector", "keyword", "hybrid"]


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
    debug: RetrievalDebug | None = None