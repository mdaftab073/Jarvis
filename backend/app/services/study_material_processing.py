from sqlalchemy.orm import Session

from app.core.material_types import MaterialType
from app.db.database import SessionLocal
from app.services.file_service import validate_uploaded_file_path
from app.services.chunking_service import chunk_text
from app.services.keyword_search_service import delete_material_chunks as delete_keyword_chunks
from app.services.keyword_search_service import replace_material_chunks
from app.services.pdf_service import extract_text_from_pdf
from app.services.pyq_service import analyze_pyq_material
from app.services.study_material_service import get_material
from app.services import vector_service


def process_pdf_material(
    material_id: int,
    db: Session | None = None,
    dependencies: dict | None = None,
) -> dict:
    owns_session = db is None
    db = db or SessionLocal()
    operations = dependencies or {}
    extract = operations.get("extract_text", extract_text_from_pdf)
    chunk = operations.get("chunk_text", chunk_text)
    vectors = operations.get("vector_service", vector_service)
    remove_keywords = operations.get("delete_keyword_chunks", delete_keyword_chunks)
    replace_keywords = operations.get("replace_material_chunks", replace_material_chunks)
    analyze_pyq = operations.get("analyze_pyq_material", analyze_pyq_material)
    material = None
    try:
        material = get_material(db, material_id)
        if material is None:
            raise ValueError("Material not found")
        text = extract(validate_uploaded_file_path(material.file_path))
        if not text or not text.strip():
            raise ValueError("No text could be extracted from PDF")
        chunks = chunk(text)
        if not chunks:
            raise ValueError("No chunks could be created from PDF")
        vectors.delete_material_chunks(material_id)
        remove_keywords(material_id)
        chunks_stored = vectors.add_chunks_to_vector_db(
            material_id=material_id,
            chunks=chunks,
            title=material.title,
            subject_id=material.subject.id,
            subject_name=material.subject.name,
        )
        replace_keywords(
            material_id=material_id,
            chunks=chunks,
            title=material.title,
            subject_id=material.subject.id,
            subject_name=material.subject.name,
        )
        pyq_questions = []
        if material.material_type == MaterialType.PYQ.value:
            pyq_questions = analyze_pyq(db=db, material=material, text=text)
        material.embedding_status = "embedded"
        db.commit()
        return {
            "material_id": material_id,
            "chunks_stored": chunks_stored,
            "questions_extracted": len(pyq_questions),
        }
    except Exception:
        db.rollback()
        if material is not None:
            material.embedding_status = "failed"
            db.commit()
        raise
    finally:
        if owns_session:
            db.close()