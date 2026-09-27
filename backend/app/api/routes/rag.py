from fastapi import APIRouter, Depends
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

router = APIRouter()


@router.post(
    "/rag/ask",
    response_model=AskResponse,
)
def ask(
    request: AskRequest,
    db: Session = Depends(get_db),
):
    result = ask_question(
        question=request.question,
        db=db,
        subject_id=request.subject_id,
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
    query: str,
    subject_id: int | None = None,
    db: Session = Depends(get_db),
):
    return debug_search(
        question=query,
        db=db,
        subject_id=subject_id,
    )