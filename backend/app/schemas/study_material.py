from datetime import datetime

from pydantic import BaseModel


class StudyMaterialCreate(BaseModel):
    title: str
    file_path: str
    subject_id: int


class StudyMaterialResponse(BaseModel):
    id: int
    title: str
    file_path: str
    uploaded_at: datetime | None
    subject_id: int

    class Config:
        from_attributes = True