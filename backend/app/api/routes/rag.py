from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db

from app.schemas.rag import (
    AskRequest,
    AskResponse,
    SourceItem,
)

from app.services.rag_service import (
    ask_question,
)
from app.services.subject_service import (
    detect_subject_from_query,
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
    detected_subject = detect_subject_from_query(
        db=db,
        query=request.question,
    )

    # An explicitly supplied subject takes priority over automatic detection.
    subject_id = (
        request.subject_id
        if request.subject_id is not None
        else (
            detected_subject.id
            if detected_subject
            else None
        )
    )

    print(
        f"Detected subject: "
        f"{detected_subject.name if detected_subject else 'None'}"
    )

    result = ask_question(
        question=request.question,
        subject_id=subject_id,
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
    )