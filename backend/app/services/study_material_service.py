from sqlalchemy.orm import Session

from app.core.material_types import MaterialType
from app.db.models import StudyMaterial


def create_material(
    db: Session,
    title: str,
    file_path: str,
    subject_id: int,
    material_type: MaterialType = MaterialType.NOTES,
):
    material = StudyMaterial(
        title=title,
        file_path=file_path,
        subject_id=subject_id,
        material_type=material_type.value,
    )

    db.add(material)
    db.commit()
    db.refresh(material)

    return material


def get_material(
    db: Session,
    material_id: int,
):
    return (
        db.query(StudyMaterial)
        .filter(StudyMaterial.id == material_id)
        .first()
    )


def get_materials(
    db: Session,
):
    return db.query(StudyMaterial).all()


def get_subject_materials(
    db: Session,
    subject_id: int,
):
    return (
        db.query(StudyMaterial)
        .filter(StudyMaterial.subject_id == subject_id)
        .all()
    )