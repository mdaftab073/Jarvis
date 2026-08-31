from pydantic import BaseModel


class SubjectCreate(BaseModel):
    name: str
    description: str | None = None
    course_id: int


class SubjectResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    course_id: int

    class Config:
        from_attributes = True