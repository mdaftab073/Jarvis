from datetime import datetime

from pydantic import BaseModel

from app.core.material_types import MaterialType


class StudyMaterialCreate(BaseModel):
    title: str
    file_path: str
    subject_id: int
    material_type: MaterialType = MaterialType.NOTES


class StudyMaterialResponse(BaseModel):
    id: int
    title: str
    file_path: str
    uploaded_at: datetime | None
    subject_id: int
    material_type: MaterialType = MaterialType.NOTES

    class Config:
        from_attributes = True
    
class StudyMaterialEmbedResponse(
    BaseModel
):
    material_id: int
    chunks_stored: int
    questions_extracted: int = 0