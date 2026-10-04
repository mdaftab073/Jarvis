import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from fastapi import UploadFile, File, Form
from app.services.file_service import save_uploaded_file, validate_uploaded_file_path
from app.core.material_types import MaterialType
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
    get_subject_materials,
)

from app.services.chunking_service import (
    chunk_text,
)

from app.services import vector_service
from app.services.keyword_search_service import (
    delete_material_chunks as delete_keyword_chunks,
    replace_material_chunks,
)
from app.services.pyq_service import analyze_pyq_material
from app.db.models import Course, Subject, StudyMaterial
from app.schemas.jobs import JobExecutionResponse
from app.services.job_service import enqueue_job
from app.services.study_material_processing import process_pdf_material
from app.api.student_scope import require_record_owner, require_student_scope
from app.core.config import settings
from app.api.rate_limit import limiter
from app.services.audit_log_service import AuditLogService

router = APIRouter()
logger = logging.getLogger(__name__)


def _material_owner(material) -> int:
    subject = getattr(material, "subject", material)
    return subject.course.student_id


def _require_material_access(material, request: Request) -> int:
    owner_id = _material_owner(material)
    require_record_owner(request, owner_id)
    if settings.REQUIRE_AUTHENTICATED_STUDENT and getattr(request.state, "student_id", None) is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return owner_id


@router.post(
    "/materials",
    response_model=StudyMaterialResponse,
)
def create_material_endpoint(
    material: StudyMaterialCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    subject = db.query(Subject).join(Course).filter(Subject.id == material.subject_id).first()
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")
    _require_material_access(subject, request)
    return create_material(
        db=db,
        title=material.title,
        file_path=validate_uploaded_file_path(material.file_path),
        subject_id=material.subject_id,
        material_type=material.material_type,
    )


@router.get(
    "/materials",
    response_model=list[StudyMaterialResponse],
)
def get_materials_endpoint(
    student_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _scope: int = Depends(require_student_scope),
):
    return (
        db.query(StudyMaterial)
        .join(Subject, StudyMaterial.subject_id == Subject.id)
        .join(Course, Subject.course_id == Course.id)
        .filter(Course.student_id == student_id)
        .order_by(StudyMaterial.uploaded_at.desc())
        .all()
    )


@router.get(
    "/materials/{material_id}",
    response_model=StudyMaterialResponse,
)
def get_material_endpoint(
    material_id: int,
    request: Request,
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

    _require_material_access(material, request)

    return material


@router.get(
    "/subjects/{subject_id}/materials",
    response_model=list[StudyMaterialResponse],
)
def get_subject_materials_endpoint(
    subject_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    subject = db.query(Subject).join(Course).filter(Subject.id == subject_id).first()
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")
    _require_material_access(subject, request)
    return get_subject_materials(
        db=db,
        subject_id=subject_id,
    )
    
def upload_material(
    title: str = Form(...),
    subject_id: int = Form(...),
    material_type: MaterialType = Form(MaterialType.NOTES),
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
        material_type=material_type,
    )

    return material


@router.post("/materials/upload", response_model=StudyMaterialResponse, status_code=202)
@limiter.limit(settings.UPLOAD_RATE_LIMIT)
def _upload_material_background(
    request: Request,
    title: str = Form(...),
    subject_id: int = Form(...),
    material_type: MaterialType = Form(MaterialType.NOTES),
    file: UploadFile = File(...),
    student_id: int | None = Form(None),
    db: Session = Depends(get_db),
):
    subject = db.query(Subject).join(Course).filter(Subject.id == subject_id).first()
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")
    owner_id = subject.course.student_id
    principal_id = getattr(request.state, "student_id", None)
    if student_id is not None and student_id != owner_id:
        raise HTTPException(status_code=403, detail="Subject is outside the requested student scope")
    require_record_owner(request, owner_id)
    if settings.REQUIRE_AUTHENTICATED_STUDENT and principal_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    material = save_uploaded_file(file=file, subject_id=subject_id)
    record = create_material(
        db=db,
        title=title,
        file_path=material,
        subject_id=subject_id,
        material_type=material_type,
    )
    job = enqueue_job(db, "process_pdf_material", {"material_id": record.id}, owner_id)
    try:
        with db.begin_nested():
            AuditLogService.record_event(
                db,
                "FILE_UPLOAD",
                "study_material",
                "upload",
                student_id=owner_id,
                resource_id=record.id,
                metadata_json={"processing_job_id": job.id, "material_type": str(material_type)},
                ip_address=request.client.host if request.client else None,
            )
        db.commit()
    except Exception:
        logger.exception("Upload audit event could not be recorded: material_id=%s", record.id)
    return {
        "id": record.id,
        "title": record.title,
        "file_path": record.file_path,
        "uploaded_at": record.uploaded_at,
        "subject_id": record.subject_id,
        "material_type": record.material_type,
        "processing_job_id": job.id,
        "processing_status": job.status,
    }

@router.get(
    "/materials/{material_id}/extract-text"
)
def extract_material_text(
    material_id: int,
    request: Request,
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

    _require_material_access(material, request)

    text = extract_text_from_pdf(validate_uploaded_file_path(material.file_path))

    return {
        "title": material.title,
        "text": text[:5000],
    }
    
@router.get(
    "/materials/{material_id}/chunks"
)
def get_material_chunks(
    material_id: int,
    request: Request,
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

    _require_material_access(material, request)

    from app.services.pdf_service import (
        extract_text_from_pdf,
    )

    text = extract_text_from_pdf(validate_uploaded_file_path(material.file_path))

    chunks = chunk_text(text)

    return {
        "total_chunks": len(chunks),
        "first_chunk": (
            chunks[0]
            if chunks
            else ""
        ),
    }


def embed_material(
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

    try:
        result = process_pdf_material(
            material_id,
            db=db,
            dependencies={
                "extract_text": extract_text_from_pdf,
                "chunk_text": chunk_text,
                "vector_service": vector_service,
                "delete_keyword_chunks": delete_keyword_chunks,
                "replace_material_chunks": replace_material_chunks,
                "analyze_pyq_material": analyze_pyq_material,
            },
        )
        return StudyMaterialEmbedResponse(**result)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail="Failed to embed material") from error


@router.post("/materials/{material_id}/embed", response_model=JobExecutionResponse, status_code=202)
@limiter.limit(settings.UPLOAD_RATE_LIMIT)
def enqueue_material_embedding(
    material_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    material = get_material(db, material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Material not found")
    student_id = material.subject.course.student_id
    require_record_owner(request, student_id)
    if settings.REQUIRE_AUTHENTICATED_STUDENT and getattr(request.state, "student_id", None) is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    execution = enqueue_job(db, "process_pdf_material", {"material_id": material_id}, student_id)
    return execution
        
@router.get("/debug/chroma")
def debug_chroma(
    request: Request,
    db: Session = Depends(get_db),
):
    if settings.ENVIRONMENT.casefold() == "production":
        raise HTTPException(status_code=404, detail="Not found")
    if settings.REQUIRE_AUTHENTICATED_STUDENT and getattr(request.state, "student_id", None) is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    from app.services.vector_service import get_collection

    collection = get_collection()
    student_id = getattr(request.state, "student_id", None)
    if student_id is None:
        results = collection.get()
    else:
        subject_ids = [
            subject_id
            for (subject_id,) in db.query(Subject.id)
            .join(Course, Subject.course_id == Course.id)
            .filter(Course.student_id == student_id)
            .all()
        ]
        results = (
            collection.get(where={"subject_id": {"$in": subject_ids}})
            if subject_ids
            else {"ids": [], "metadatas": []}
        )

    return {
        "total_chunks": len(results["ids"]),
        "sample_metadata": (
            results["metadatas"][:5]
            if results["metadatas"]
            else []
        ),
    }
    
@router.get("/debug/search")
def debug_search(
    request: Request,
    query: str,
    subject_id: int,
    db: Session = Depends(get_db),
):
    if not vector_service.is_chroma_available():
        raise HTTPException(
            status_code=503,
            detail="RAG is temporarily unavailable because vector search is degraded",
        )
    from app.services.vector_service import (
        search_similar_chunks,
    )

    subject = db.query(Subject).join(Course).filter(Subject.id == subject_id).first()
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")
    _require_material_access(subject, request)
    return search_similar_chunks(
        query=query,
        subject_id=subject_id,
        n_results=5,
    )