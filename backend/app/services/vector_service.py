from pathlib import Path
from typing import Optional

import chromadb
from sentence_transformers import SentenceTransformer


_embedding_model: Optional[SentenceTransformer] = None
_chroma_client = None

CHROMA_DB_PATH = "chroma_db"
COLLECTION_NAME = "study_materials"


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
        _chroma_client = chromadb.PersistentClient(
            path=CHROMA_DB_PATH
        )

    return _chroma_client


def get_collection():
    client = get_chroma_client()

    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={
            "hnsw:space": "cosine",
        },
    )


def generate_embedding(text: str):
    model = get_embedding_model()

    embedding = model.encode(text)

    return embedding.tolist()


def add_chunks_to_vector_db(
    material_id: int,
    chunks: list[str],
    title: str,
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


def search_similar_chunks(
    query: str,
    n_results: int = 5,
):
    collection = get_collection()

    query_embedding = generate_embedding(
        query
    )

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
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
                }
            )

    return parsed_results