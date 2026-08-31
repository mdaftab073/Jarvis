from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db

from app.schemas.study_material import (
    StudyMaterialCreate,
    StudyMaterialResponse,
)

from app.services.study_material_service import (
    create_material,
    get_material,
    get_materials,
    get_subject_materials,
)

router = APIRouter()


@router.post(
    "/materials",
    response_model=StudyMaterialResponse,
)
def create_material_endpoint(
    material: StudyMaterialCreate,
    db: Session = Depends(get_db),
):
    return create_material(
        db=db,
        title=material.title,
        file_path=material.file_path,
        subject_id=material.subject_id,
    )


@router.get(
    "/materials",
    response_model=list[StudyMaterialResponse],
)
def get_materials_endpoint(
    db: Session = Depends(get_db),
):
    return get_materials(db)


@router.get(
    "/materials/{material_id}",
    response_model=StudyMaterialResponse,
)
def get_material_endpoint(
    material_id: int,
    db: Session = Depends(get_db),
):
    material = get_material(
        db=db,
        material_id=material_id,
    )

    if material is None:
        raise HTTPException(
            status_code=404,
            detail="Material not found",
        )

    return material


@router.get(
    "/subjects/{subject_id}/materials",
    response_model=list[StudyMaterialResponse],
)
def get_subject_materials_endpoint(
    subject_id: int,
    db: Session = Depends(get_db),
):
    return get_subject_materials(
        db=db,
        subject_id=subject_id,
    )