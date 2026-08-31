from pydantic import BaseModel

class CourseCreate(BaseModel):
    name: str
    description: str | None = None
    student_id: int


class CourseResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    student_id: int

    class Config:
        from_attributes = True


class CourseSubject(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class CourseWithSubjects(BaseModel):
    id: int
    name: str
    description: str | None = None

    subjects: list[CourseSubject]

    class Config:
        from_attributes = True