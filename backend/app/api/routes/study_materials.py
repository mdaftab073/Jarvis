from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi import UploadFile, File, Form
from app.services.file_service import save_uploaded_file
from app.db.database import get_db
from app.services.pdf_service import (
    extract_text_from_pdf,
)
from app.schemas.study_material import (
    StudyMaterialCreate,
    StudyMaterialResponse,
    StudyMaterialEmbedResponse,
)

from app.services.study_material_service import (
    create_material,
    get_material,
    get_materials,
    get_subject_materials,
)

from app.services.chunking_service import (
    chunk_text,
)

from app.services import vector_service

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
    
@router.post(
    "/materials/upload",
    response_model=StudyMaterialResponse,
)
def upload_material(
    title: str = Form(...),
    subject_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    file_path = save_uploaded_file(
        file=file,
        subject_id=subject_id,
    )

    material = create_material(
        db=db,
        title=title,
        file_path=file_path,
        subject_id=subject_id,
    )

    return material

@router.get(
    "/materials/{material_id}/extract-text"
)
def extract_material_text(
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

    text = extract_text_from_pdf(
        material.file_path
    )

    return {
        "title": material.title,
        "text": text[:5000],
    }
    
@router.get(
    "/materials/{material_id}/chunks"
)
def get_material_chunks(
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

    from app.services.pdf_service import (
        extract_text_from_pdf,
    )

    text = extract_text_from_pdf(
        material.file_path
    )

    chunks = chunk_text(text)

    return {
        "total_chunks": len(chunks),
        "first_chunk": (
            chunks[0]
            if chunks
            else ""
        ),
    }


@router.post(
    "/materials/{material_id}/embed",
    response_model=StudyMaterialEmbedResponse,
)
def embed_material(
    material_id: int,
    db: Session = Depends(get_db),
):
    """
    Extract text from PDF, chunk it, generate embeddings, and store in ChromaDB.
    
    Flow:
    1. Get material from database
    2. Extract text from PDF
    3. Chunk the text
    4. Generate embeddings and store chunks in ChromaDB
    5. Update material's embedding_status to "embedded"
    6. Return response with material_id and chunk count
    """
    # Step 1: Get material from database
    material = get_material(
        db=db,
        material_id=material_id,
    )

    if material is None:
        raise HTTPException(
            status_code=404,
            detail="Material not found",
        )

    try:
        # Step 2: Extract text from PDF
        text = extract_text_from_pdf(material.file_path)
        
        if not text or not text.strip():
            raise HTTPException(
                status_code=400,
                detail="Failed to extract text from PDF",
            )

        # Step 3: Chunk the text
        chunks = chunk_text(text)
        
        if not chunks:
            raise HTTPException(
                status_code=400,
                detail="No text extracted from PDF",
            )

        # Step 4: Generate embeddings and store in ChromaDB
        # Remove old embeddings first
        vector_service.delete_material_chunks(
            material_id
        )

        # Create fresh embeddings
        chunks_stored = vector_service.add_chunks_to_vector_db(
            material_id=material_id,
            chunks=chunks,
            title=material.title,
        )

        # Step 5: Update material's embedding_status
        material.embedding_status = "embedded"
        db.commit()

        # Step 6: Return response
        return StudyMaterialEmbedResponse(
            material_id=material_id,
            chunks_stored=chunks_stored,
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Catch any other exception, set status to "failed", and re-raise
        material.embedding_status = "failed"
        db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to embed material: {str(e)}",
        )