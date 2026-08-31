from pydantic import BaseModel, EmailStr


class StudentCreate(BaseModel):
    name: str
    email: EmailStr


class StudentUpdate(BaseModel):
    name: str
    email: EmailStr


class StudentResponse(BaseModel):
    id: int
    name: str
    email: EmailStr

    class Config:
        from_attributes = True
        
from pydantic import BaseModel, EmailStr


class StudentCourse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class StudentWithCourses(BaseModel):
    id: int
    name: str
    email: EmailStr

    courses: list[StudentCourse]

    class Config:
        from_attributes = True