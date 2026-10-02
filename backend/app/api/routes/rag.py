from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.database import get_db

from app.schemas.rag import (
    AskRequest,
    AskResponse,
    RetrievalDebug,
    SourceItem,
)

from app.services.rag_service import (
    ask_question,
    debug_search,
)
from app.services.audit_log_service import AuditLogService
from app.api.rate_limit import limiter
from app.core.config import settings
from app.services.ownership_service import require_subject_owner
from fastapi import HTTPException

router = APIRouter()


@router.post(
    "/rag/ask",
    response_model=AskResponse,
)
@limiter.limit(settings.RAG_RATE_LIMIT)
def ask(
    request: Request,
    payload: AskRequest,
    db: Session = Depends(get_db),
):
    student_id = getattr(request.state, "student_id", None)
    if settings.REQUIRE_AUTHENTICATED_STUDENT and student_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    if student_id is not None:
        if payload.subject_id is None:
            raise HTTPException(status_code=422, detail="subject_id is required for student-scoped retrieval")
        try:
            require_subject_owner(db, student_id, payload.subject_id)
        except HTTPException as error:
            raise HTTPException(status_code=404, detail="Subject not found") from error
    result = ask_question(
        question=payload.question,
        db=db,
        subject_id=payload.subject_id,
    )
    AuditLogService.record_event_isolated(
        event_type="RAG_QUERY",
        resource_type="subject" if payload.subject_id is not None else "rag",
        resource_id=payload.subject_id,
        action="query",
        student_id=student_id,
        metadata_json={"chunks_used": result.get("chunks_used", 0)},
        ip_address=request.client.host if request.client else None,
    )

    sources = []
    seen = set()

    for item in result["results"]:
        metadata = item["metadata"]

        material_id = metadata["material_id"]

        if material_id not in seen:
            seen.add(material_id)

            sources.append(
                SourceItem(
                    material_id=material_id,
                    title=metadata["title"],
                    chunk_index=metadata["chunk_index"],
                )
            )

    return AskResponse(
        answer=result["answer"],
        sources=sources,
        debug=RetrievalDebug(
            chunks_used=result["chunks_used"],
            subject_detected=result["stats"]["subject_detected"],
        ),
    )


@router.get("/rag/debug-search")
def rag_debug_search(
    request: Request,
    query: str,
    subject_id: int | None = None,
    db: Session = Depends(get_db),
):
    if settings.ENVIRONMENT.casefold() == "production":
        raise HTTPException(status_code=404, detail="Not found")
    student_id = getattr(request.state, "student_id", None)
    if settings.REQUIRE_AUTHENTICATED_STUDENT and student_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    if student_id is not None and subject_id is not None:
        try:
            require_subject_owner(db, student_id, subject_id)
        except HTTPException as error:
            raise HTTPException(status_code=404, detail="Subject not found") from error
    return debug_search(
        question=query,
        db=db,
        subject_id=subject_id,
    )