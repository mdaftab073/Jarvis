from pydantic import BaseModel


class AskRequest(BaseModel):

    question: str

    subject_id: int | None = None

class SourceItem(BaseModel):
    material_id: int
    title: str
    chunk_index: int


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceItem]