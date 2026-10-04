import logging
import os
from pathlib import Path
from typing import Optional
from uuid import uuid4

import chromadb
from sentence_transformers import SentenceTransformer

from app.core.rag_config import (
    DEFAULT_TOP_K,
    ENABLE_SCORE_FILTERING,
    SIMILARITY_THRESHOLD,
)


_embedding_model: Optional[SentenceTransformer] = None
_chroma_client = None
logger = logging.getLogger(__name__)

CHROMA_DB_PATH = os.getenv("CHROMA_PERSISTENT_DIRECTORY", "chroma_db")
COLLECTION_NAME = "study_materials"
CHROMA_HOST = os.getenv("CHROMA_HOST")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
CHROMA_SSL = os.getenv("CHROMA_SSL", "false").casefold() == "true"
_CHROMA_STATUS = "unknown"


def get_embedding_model():
    global _embedding_model

    if _embedding_model is None:
        _embedding_model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )

    return _embedding_model


def get_chroma_client():
    global _chroma_client

    if _chroma_client is None:
        if CHROMA_HOST:
            _chroma_client = chromadb.HttpClient(
                host=CHROMA_HOST,
                port=CHROMA_PORT,
                ssl=CHROMA_SSL,
            )
        else:
            _chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

    return _chroma_client


def get_collection():
    client = get_chroma_client()

    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={
            "hnsw:space": "cosine",
        },
    )


def chroma_status() -> str:
    return _CHROMA_STATUS


def is_chroma_available() -> bool:
    return _CHROMA_STATUS != "degraded"


def validate_chroma_storage() -> str:
    global _CHROMA_STATUS
    try:
        client = get_chroma_client()
        if not CHROMA_HOST and not Path(CHROMA_DB_PATH).is_dir():
            raise RuntimeError("Local Chroma persistence directory is missing")
        collection_names = {
            getattr(item, "name", item)
            for item in client.list_collections()
        }
        if COLLECTION_NAME not in collection_names:
            get_collection()
        collection = client.get_collection(name=COLLECTION_NAME)
        collection.count()
        collection.query(query_embeddings=[[0.0] * 384], n_results=1)
    except Exception:
        _CHROMA_STATUS = "degraded"
        raise
    _CHROMA_STATUS = "healthy"
    return _CHROMA_STATUS


def validate_rag_storage() -> str:
    was_healthy = _CHROMA_STATUS == "healthy"
    try:
        status = validate_chroma_storage()
        if not was_healthy:
            from app.services.keyword_search_service import sync_keyword_index_from_chroma

            sync_keyword_index_from_chroma()
    except Exception:
        mark_chroma_degraded()
        raise
    return status


def mark_chroma_degraded() -> None:
    global _CHROMA_STATUS
    _CHROMA_STATUS = "degraded"


def stage_material_chunks(
    material_id: int,
    chunks: list[str],
    title: str,
    subject_id: int,
    subject_name: str,
) -> dict[str, list[str]]:
    collection = get_collection()
    generation = uuid4().hex
    ids = [f"{material_id}_{generation}_{index}" for index in range(len(chunks))]
    embeddings = [generate_embedding(chunk) for chunk in chunks]
    metadatas = [
        {
            "material_id": material_id,
            "subject_id": subject_id,
            "subject_name": subject_name,
            "chunk_index": index,
            "title": title,
            "generation": generation,
            "indexing_state": "staged",
        }
        for index in range(len(chunks))
    ]

    try:
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
        )
        stored = collection.get(ids=ids, include=["metadatas"])
        if len(stored["ids"]) != len(ids):
            raise RuntimeError("Staged embedding verification failed")
        existing = collection.get(
            where={"material_id": {"$eq": material_id}},
            include=["metadatas"],
        )
        previous_ids = [
            chunk_id
            for chunk_id, metadata in zip(existing["ids"], existing["metadatas"])
            if chunk_id not in ids
            and metadata
            and metadata.get("indexing_state") not in {"staged", "retired"}
        ]
    except Exception:
        try:
            collection.delete(ids=ids)
        except Exception:
            logger.exception(
                "Could not remove incomplete staged embeddings: material_id=%s",
                material_id,
            )
        raise

    return {"ids": ids, "previous_ids": previous_ids}


def activate_staged_material_chunks(chunk_ids: list[str]) -> None:
    if not chunk_ids:
        raise ValueError("Cannot activate an empty embedding generation")
    collection = get_collection()
    staged = collection.get(ids=chunk_ids, include=["metadatas"])
    if len(staged["ids"]) != len(chunk_ids):
        raise RuntimeError("Staged embeddings disappeared before activation")
    metadatas = []
    for metadata in staged["metadatas"]:
        if not metadata or metadata.get("indexing_state") != "staged":
            raise RuntimeError("Embedding generation is not fully staged")
        metadatas.append({**metadata, "indexing_state": "active"})
    collection.update(ids=chunk_ids, metadatas=metadatas)


def discard_staged_material_chunks(chunk_ids: list[str]) -> None:
    if chunk_ids:
        get_collection().delete(ids=chunk_ids)


def retire_previous_material_chunks(chunk_ids: list[str]) -> None:
    if not chunk_ids:
        return
    collection = get_collection()
    previous = collection.get(ids=chunk_ids, include=["metadatas"])
    if not previous["ids"]:
        return
    metadatas = [
        {**(metadata or {}), "indexing_state": "retired"}
        for metadata in previous["metadatas"]
    ]
    collection.update(ids=previous["ids"], metadatas=metadatas)
    collection.delete(ids=previous["ids"])


# NEW FUNCTION
def delete_material_chunks(
    material_id: int,
):
    collection = get_collection()

    results = collection.get()

    ids_to_delete = []

    for idx, metadata in enumerate(
        results["metadatas"]
    ):
        if (
            metadata
            and metadata.get("material_id")
            == material_id
        ):
            ids_to_delete.append(
                results["ids"][idx]
            )

    if ids_to_delete:
        collection.delete(
            ids=ids_to_delete
        )

    return len(ids_to_delete)


def generate_embedding(text: str):
    model = get_embedding_model()

    embedding = model.encode(text)

    return embedding.tolist()


def add_chunks_to_vector_db(
    material_id: int,
    chunks: list[str],
    title: str,
    subject_id: int,
    subject_name: str,
):
    collection = get_collection()

    ids = []
    embeddings = []
    documents = []
    metadatas = []

    for index, chunk in enumerate(chunks):
        ids.append(f"{material_id}_{index}")

        embeddings.append(
            generate_embedding(chunk)
        )

        documents.append(chunk)

        metadatas.append(
            {
                "material_id": material_id,
                "subject_id": subject_id,
                "subject_name": subject_name,
                "chunk_index": index,
                "title": title,
            }
        )

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )

    return len(ids)


def filter_results_by_score(
    results: list[dict],
    threshold: float = SIMILARITY_THRESHOLD,
):
    return [
        {
            **result,
            "similarity": 1 - result["distance"],
        }
        for result in results
        if 1 - result["distance"] >= threshold
    ]


def _query_similar_chunks(
    query: str,
    n_results: int,
    subject_id: int | None = None,
):
    collection = get_collection()

    query_embedding = generate_embedding(
        query
    )

    query_params = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
        "where": {
            "$and": [
                {"indexing_state": {"$ne": "staged"}},
                {"indexing_state": {"$ne": "retired"}},
            ]
        },
    }

    if subject_id is not None:
        query_params["where"]["$and"].append(
            {"subject_id": {"$eq": subject_id}}
        )

    results = collection.query(
        **query_params
    )

    parsed_results = []

    if results["ids"]:
        for i in range(
            len(results["ids"][0])
        ):
            parsed_results.append(
                {
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                    "similarity": 1 - results["distances"][0][i],
                }
            )

    return parsed_results


def search_similar_chunks(
    query: str,
    n_results: int = DEFAULT_TOP_K,
    subject_id: int | None = None,
):
    retrieved_results = _query_similar_chunks(
        query=query,
        n_results=n_results,
        subject_id=subject_id,
    )

    if not ENABLE_SCORE_FILTERING:
        return retrieved_results

    return filter_results_by_score(retrieved_results)


def search_similar_chunks_with_stats(
    query: str,
    n_results: int = DEFAULT_TOP_K,
    subject_id: int | None = None,
):
    retrieved_results = _query_similar_chunks(
        query=query,
        n_results=n_results,
        subject_id=subject_id,
    )
    filtered_results = (
        filter_results_by_score(retrieved_results)
        if ENABLE_SCORE_FILTERING
        else retrieved_results
    )
    return retrieved_results, filtered_results