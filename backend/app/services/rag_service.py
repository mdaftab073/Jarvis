import logging
import re

from sqlalchemy.orm import Session

from app.core.rag_config import (
    DEFAULT_TOP_K,
    ENABLE_CONTEXT_TRUNCATION,
    MAX_CONTEXT_CHARS,
)
from app.core.hybrid_config import (
    FINAL_TOP_K,
    HYBRID_SOURCE_DIVERSITY_SCORE_MARGIN,
)
from app.services.hybrid_retrieval_service import (
    hybrid_search,
    hybrid_search_with_diagnostics,
)
from app.services.llm_service import generate_answer
from app.services.subject_service import (
    detect_subject_from_query,
    get_subject,
)
logger = logging.getLogger(__name__)


def enforce_source_diversity(
    results: list[dict],
    limit: int = FINAL_TOP_K,
    score_margin: float = HYBRID_SOURCE_DIVERSITY_SCORE_MARGIN,
):
    distinct_sources = []
    repeated_sources = []
    seen_materials = set()
    best_score = results[0].get("score", 0) if results else 0

    for result in results:
        material_id = result["metadata"].get("material_id")
        is_close_in_score = (
            best_score - result.get("score", 0) <= score_margin
        )
        if material_id not in seen_materials and is_close_in_score:
            seen_materials.add(material_id)
            distinct_sources.append(result)
        else:
            repeated_sources.append(result)

    return (distinct_sources + repeated_sources)[:limit]


def assemble_context(results: list[dict]):
    grouped_results = {}

    for result in results:
        metadata = result["metadata"]
        group_key = (
            metadata.get("material_id"),
            metadata.get("title", "Unknown"),
        )
        grouped_results.setdefault(group_key, []).append(result)

    source_blocks = []
    for (_, title), chunks in grouped_results.items():
        chunks.sort(key=lambda item: item["metadata"].get("chunk_index", 0))
        chunk_text = [
            f"[Chunk {item['metadata'].get('chunk_index', 0) + 1}]\n{item['document']}"
            for item in chunks
        ]
        safe_title = str(title).replace("\r", " ").replace("\n", " ")
        source_blocks.append(
            f"Source: {safe_title}\n\n" + "\n\n".join(chunk_text)
        )

    return "\n\n".join(source_blocks)


def truncate_context(
    context: str,
    max_chars: int = MAX_CONTEXT_CHARS,
):
    if max_chars <= 0:
        return ""
    if len(context) <= max_chars:
        return context

    source_blocks = re.split(r"\n\n(?=Source: )", context)
    retained_blocks = []

    for source_block in source_blocks:
        lines = source_block.splitlines()
        if not lines or not lines[0].startswith("Source: "):
            break

        source_label = lines[0]
        remaining = "\n".join(lines[1:]).lstrip("\n")
        chunks = re.split(r"(?m)(?=^\[Chunk \d+\]$)", remaining)
        retained_chunks = []

        for chunk in chunks:
            chunk = chunk.strip("\n")
            if not re.match(r"^\[Chunk \d+\]\n", chunk):
                continue

            candidate_block = "\n\n".join(
                [source_label, *retained_chunks, chunk]
            )
            candidate_context = "\n\n".join(
                [*retained_blocks, candidate_block]
            )
            if len(candidate_context) > max_chars:
                if retained_chunks:
                    retained_blocks.append(
                        "\n\n".join([source_label, *retained_chunks])
                    )
                return "\n\n".join(retained_blocks)

            retained_chunks.append(chunk)

        if retained_chunks:
            retained_blocks.append(
                "\n\n".join([source_label, *retained_chunks])
            )

    return "\n\n".join(retained_blocks)


def build_retrieval_stats(
    retrieved_results: list[dict],
    filtered_results: list[dict],
    selected_results: list[dict],
    subject_detected: str | None,
):
    materials_used = []
    seen_materials = set()

    for result in selected_results:
        metadata = result["metadata"]
        material_id = metadata.get("material_id")
        if material_id not in seen_materials:
            seen_materials.add(material_id)
            materials_used.append(
                {
                    "material_id": material_id,
                    "title": metadata.get("title"),
                }
            )

    return {
        "chunks_retrieved": len(retrieved_results),
        "chunks_after_filtering": len(filtered_results),
        "subject_detected": subject_detected,
        "materials_used": materials_used,
    }


def _retrieve(
    question: str,
    subject_id: int | None,
    top_k: int = DEFAULT_TOP_K,
):
    hybrid_results = hybrid_search(
        query=question,
        subject_id=subject_id,
        final_top_k=max(top_k * 3, top_k),
    )
    selected_results = enforce_source_diversity(
        hybrid_results,
        limit=top_k,
    )
    return hybrid_results, selected_results


def _resolve_subject(db: Session, question: str, subject_id: int | None):
    detected_subject = detect_subject_from_query(db=db, query=question)
    effective_subject_id = (
        subject_id
        if subject_id is not None
        else detected_subject.id if detected_subject else None
    )
    effective_subject = (
        get_subject(db=db, subject_id=effective_subject_id)
        if effective_subject_id is not None
        else None
    )
    subject_name = effective_subject.name if effective_subject else None
    logger.info("RAG subject detection: %s", subject_name or "None")
    return effective_subject_id, subject_name


def build_context(
    question: str,
    top_k: int = DEFAULT_TOP_K,
    subject_id: int | None = None,
):
    _, results = _retrieve(
        question=question,
        subject_id=subject_id,
        top_k=top_k,
    )
    context = assemble_context(results)
    if ENABLE_CONTEXT_TRUNCATION:
        context = truncate_context(context, MAX_CONTEXT_CHARS)
    return context, results


def _context_for_results(results: list[dict]):
    context = assemble_context(results)
    if ENABLE_CONTEXT_TRUNCATION:
        context = truncate_context(context, MAX_CONTEXT_CHARS)
    logger.info("RAG final context size: %d characters", len(context))
    return context


def ask_question(
    question: str,
    db: Session,
    subject_id: int | None = None,
):
    effective_subject_id, subject_name = _resolve_subject(
        db=db,
        question=question,
        subject_id=subject_id,
    )
    hybrid_results, selected_results = _retrieve(
        question=question,
        subject_id=effective_subject_id,
    )
    logger.info(
        "RAG hybrid retrieval counts: fused=%d selected=%d",
        len(hybrid_results),
        len(selected_results),
    )
    context = _context_for_results(selected_results)
    answer = generate_answer(question=question, context=context)
    stats = build_retrieval_stats(
        retrieved_results=hybrid_results,
        filtered_results=hybrid_results,
        selected_results=selected_results,
        subject_detected=subject_name,
    )
    return {
        "answer": answer,
        "results": selected_results,
        "stats": stats,
        "chunks_used": len(re.findall(r"(?m)^\[Chunk \d+\]$", context)),
    }


def debug_search(
    question: str,
    db: Session,
    subject_id: int | None = None,
):
    effective_subject_id, subject_name = _resolve_subject(
        db=db,
        question=question,
        subject_id=subject_id,
    )
    diagnostics = hybrid_search_with_diagnostics(
        query=question,
        subject_id=effective_subject_id,
        final_top_k=FINAL_TOP_K * 3,
    )
    results = enforce_source_diversity(diagnostics["hybrid_results"])
    stats = build_retrieval_stats(
        retrieved_results=diagnostics["vector_results"],
        filtered_results=diagnostics["hybrid_results"],
        selected_results=results,
        subject_detected=subject_name,
    )
    logger.info(
        "RAG debug retrieval counts: vector=%d keyword=%d hybrid=%d",
        len(diagnostics["vector_results"]),
        len(diagnostics["keyword_results"]),
        len(results),
    )
    _context_for_results(results)
    return {
        "query": question,
        "subject_id": effective_subject_id,
        "retrieved_chunks": results,
        "stats": stats,
        "vector_results": diagnostics["vector_results"],
        "keyword_results": diagnostics["keyword_results"],
        "hybrid_results": results,
        "fusion_stats": diagnostics["fusion_stats"],
    }