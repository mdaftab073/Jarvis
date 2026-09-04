from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str


class SourceItem(BaseModel):
    material_id: int
    title: str


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceItem]