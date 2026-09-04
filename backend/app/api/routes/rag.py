from fastapi import APIRouter

from app.schemas.rag import (
    AskRequest,
    AskResponse,
    SourceItem,
)

from app.services.rag_service import (
    ask_question,
)

router = APIRouter()


@router.post(
    "/rag/ask",
    response_model=AskResponse,
)
def ask(
    request: AskRequest,
):
    result = ask_question(
        request.question
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