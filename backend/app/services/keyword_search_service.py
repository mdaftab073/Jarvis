import json
import logging
import re
import sqlite3
from contextlib import closing
from pathlib import Path

from rank_bm25 import BM25Okapi

from app.core.hybrid_config import KEYWORD_INDEX_PATH, KEYWORD_TOP_K

logger = logging.getLogger(__name__)
_TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)


def _connect():
    index_path = Path(KEYWORD_INDEX_PATH)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(index_path), timeout=30)
    connection.execute("PRAGMA busy_timeout = 30000")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS keyword_chunks (
            chunk_id TEXT PRIMARY KEY,
            document TEXT NOT NULL,
            metadata TEXT NOT NULL,
            material_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS ix_keyword_chunks_subject_id "
        "ON keyword_chunks(subject_id)"
    )
    return connection


def _tokenize(text: str):
    return _TOKEN_PATTERN.findall(text.lower())


def index_chunk(
    chunk_id: str,
    document: str,
    metadata: dict,
):
    with closing(_connect()) as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO keyword_chunks (
                    chunk_id, document, metadata, material_id, subject_id
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(chunk_id) DO UPDATE SET
                    document = excluded.document,
                    metadata = excluded.metadata,
                    material_id = excluded.material_id,
                    subject_id = excluded.subject_id
                """,
                (
                    chunk_id,
                    document,
                    json.dumps(metadata),
                    int(metadata["material_id"]),
                    int(metadata["subject_id"]),
                ),
            )


def replace_material_chunks(
    material_id: int,
    chunks: list[str],
    title: str,
    subject_id: int,
    subject_name: str,
):
    rows = []
    for chunk_index, document in enumerate(chunks):
        metadata = {
            "material_id": material_id,
            "subject_id": subject_id,
            "subject_name": subject_name,
            "chunk_index": chunk_index,
            "title": title,
        }
        rows.append(
            (
                f"{material_id}_{chunk_index}",
                document,
                json.dumps(metadata),
                material_id,
                subject_id,
            )
        )

    with closing(_connect()) as connection:
        with connection:
            connection.execute(
                "DELETE FROM keyword_chunks WHERE material_id = ?",
                (material_id,),
            )
            connection.executemany(
                """
                INSERT INTO keyword_chunks (
                    chunk_id, document, metadata, material_id, subject_id
                ) VALUES (?, ?, ?, ?, ?)
                """,
                rows,
            )

    logger.info(
        "BM25 keyword index updated: material_id=%d chunks=%d",
        material_id,
        len(rows),
    )
    return len(rows)


def delete_material_chunks(material_id: int):
    with closing(_connect()) as connection:
        with connection:
            cursor = connection.execute(
                "DELETE FROM keyword_chunks WHERE material_id = ?",
                (material_id,),
            )
            return cursor.rowcount


def sync_keyword_index_from_chroma():
    from app.services.vector_service import get_collection

    chroma_chunks = get_collection().get(
        include=["documents", "metadatas"],
    )
    rows = []
    for chunk_id, document, metadata in zip(
        chroma_chunks["ids"],
        chroma_chunks["documents"],
        chroma_chunks["metadatas"],
    ):
        if not metadata or document is None:
            continue
        rows.append(
            (
                chunk_id,
                document,
                json.dumps(metadata),
                int(metadata["material_id"]),
                int(metadata["subject_id"]),
            )
        )

    with closing(_connect()) as connection:
        with connection:
            connection.execute("DELETE FROM keyword_chunks")
            connection.executemany(
                """
                INSERT INTO keyword_chunks (
                    chunk_id, document, metadata, material_id, subject_id
                ) VALUES (?, ?, ?, ?, ?)
                """,
                rows,
            )

    logger.info("Synchronized %d chunks from Chroma into BM25 index", len(rows))
    return len(rows)


def search_keywords(
    query: str,
    top_k: int = KEYWORD_TOP_K,
    subject_id: int | None = None,
):
    query_tokens = _tokenize(query)
    if not query_tokens or top_k <= 0:
        return []

    query_sql = (
        "SELECT chunk_id, document, metadata "
        "FROM keyword_chunks"
    )
    parameters = ()
    if subject_id is not None:
        query_sql += " WHERE subject_id = ?"
        parameters = (subject_id,)
    query_sql += " ORDER BY chunk_id"

    with closing(_connect()) as connection:
        rows = connection.execute(query_sql, parameters).fetchall()

    tokenized_documents = [_tokenize(row[1]) for row in rows]
    nonempty_rows = [
        (row, tokens)
        for row, tokens in zip(rows, tokenized_documents)
        if tokens
    ]
    if not nonempty_rows:
        return []

    corpus = [tokens for _, tokens in nonempty_rows]
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(query_tokens)
    query_terms = set(query_tokens)
    results = []

    for (row, tokens), score in zip(nonempty_rows, scores):
        if not query_terms.intersection(tokens):
            continue
        results.append(
            {
                "id": row[0],
                "document": row[1],
                "metadata": json.loads(row[2]),
                "score": float(score),
                "source": "keyword",
            }
        )

    results.sort(key=lambda item: (-item["score"], item["id"]))
    return results[:top_k]
