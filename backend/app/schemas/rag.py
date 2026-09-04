from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str


class SourceItem(BaseModel):
    material_id: int
    title: str
    chunk_index: int


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceItem]