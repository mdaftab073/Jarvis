import logging
from concurrent.futures import ThreadPoolExecutor
from statistics import mean

from app.core.hybrid_config import (
    FINAL_TOP_K,
    KEYWORD_TOP_K,
    RRF_K,
    VECTOR_TOP_K,
)
from app.services.keyword_search_service import search_keywords
from app.services.vector_service import search_similar_chunks_with_stats

logger = logging.getLogger(__name__)


def _vector_search(query: str, subject_id: int | None):
    _, filtered_results = search_similar_chunks_with_stats(
        query=query,
        n_results=VECTOR_TOP_K,
        subject_id=subject_id,
    )
    return [
        {
            **result,
            "score": result.get("similarity", 1 - result["distance"]),
            "source": "vector",
        }
        for result in filtered_results
    ]


def fuse_results(
    vector_results: list[dict],
    keyword_results: list[dict],
    rrf_k: int = RRF_K,
):
    contributions = []
    for source, results in (
        ("vector", vector_results),
        ("keyword", keyword_results),
    ):
        for rank, result in enumerate(results, start=1):
            contributions.append(
                {
                    **result,
                    "score": 1 / (rrf_k + rank),
                    "source": source,
                }
            )
    return contributions


def deduplicate_results(results: list[dict]):
    by_id = {}

    for result in results:
        chunk_id = result["id"]
        source = result["source"]
        entry = by_id.get(chunk_id)
        if entry is None:
            entry = {
                **result,
                "score": 0.0,
                "_source_scores": {},
            }
            by_id[chunk_id] = entry

        source_scores = entry["_source_scores"]
        source_scores[source] = max(
            source_scores.get(source, 0.0),
            result["score"],
        )
        entry["score"] = sum(source_scores.values())
        if source == "vector":
            for key, value in result.items():
                if key not in {"score", "source"}:
                    entry[key] = value

    deduplicated = []
    for entry in by_id.values():
        source_scores = entry.pop("_source_scores")
        entry["source"] = (
            "hybrid"
            if "vector" in source_scores and "keyword" in source_scores
            else next(iter(source_scores))
        )
        deduplicated.append(entry)

    deduplicated.sort(key=lambda item: (-item["score"], item["id"]))
    return deduplicated


def _fusion_stats(
    vector_results: list[dict],
    keyword_results: list[dict],
    contributions: list[dict],
    fused_results: list[dict],
    final_results: list[dict],
):
    vector_ids = {result["id"] for result in vector_results}
    keyword_ids = {result["id"] for result in keyword_results}
    scores = [result["score"] for result in final_results]
    return {
        "vector_hits": len(vector_results),
        "keyword_hits": len(keyword_results),
        "hybrid_hits": len(vector_ids & keyword_ids),
        "duplicates_removed": len(contributions) - len(fused_results),
        "fusion_score_distribution": {
            "min": min(scores) if scores else None,
            "max": max(scores) if scores else None,
            "mean": mean(scores) if scores else None,
        },
    }


def hybrid_search_with_diagnostics(
    query: str,
    subject_id: int | None = None,
    final_top_k: int = FINAL_TOP_K,
):
    with ThreadPoolExecutor(max_workers=2) as executor:
        vector_future = executor.submit(_vector_search, query, subject_id)
        keyword_future = executor.submit(
            search_keywords,
            query,
            KEYWORD_TOP_K,
            subject_id,
        )
        vector_results = vector_future.result()
        keyword_results = keyword_future.result()

    contributions = fuse_results(vector_results, keyword_results)
    fused_results = deduplicate_results(contributions)
    final_results = fused_results[:final_top_k]
    fusion_stats = _fusion_stats(
        vector_results=vector_results,
        keyword_results=keyword_results,
        contributions=contributions,
        fused_results=fused_results,
        final_results=final_results,
    )
    logger.info(
        "Hybrid retrieval: vector_hits=%d keyword_hits=%d hybrid_hits=%d "
        "duplicates_removed=%d score_distribution=%s",
        fusion_stats["vector_hits"],
        fusion_stats["keyword_hits"],
        fusion_stats["hybrid_hits"],
        fusion_stats["duplicates_removed"],
        fusion_stats["fusion_score_distribution"],
    )
    return {
        "vector_results": vector_results,
        "keyword_results": keyword_results,
        "hybrid_results": final_results,
        "fusion_stats": fusion_stats,
    }


def hybrid_search(
    query: str,
    subject_id: int | None = None,
    final_top_k: int = FINAL_TOP_K,
):
    return hybrid_search_with_diagnostics(
        query=query,
        subject_id=subject_id,
        final_top_k=final_top_k,
    )["hybrid_results"]
