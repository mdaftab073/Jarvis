import logging
import sys

from app.db.database import SessionLocal
from app.db.models import StudyMaterial
from app.services.study_material_processing import process_pdf_material
from app.services.vector_service import get_collection, validate_chroma_storage


logger = logging.getLogger("jarvis.embedding_rebuild")
CHROMA_BATCH_SIZE = 1000


def _remove_orphaned_chunks(material_ids: set[int]) -> int:
    collection = get_collection()
    orphaned_ids: list[str] = []
    offset = 0
    while True:
        batch = collection.get(
            limit=CHROMA_BATCH_SIZE,
            offset=offset,
            include=["metadatas"],
        )
        ids = batch["ids"]
        metadatas = batch["metadatas"]
        if not ids:
            break
        for chunk_id, metadata in zip(ids, metadatas):
            material_id = metadata.get("material_id") if metadata else None
            state = metadata.get("indexing_state") if metadata else None
            if material_id not in material_ids or state in {"staged", "retired"}:
                orphaned_ids.append(chunk_id)
        offset += len(ids)

    for start in range(0, len(orphaned_ids), CHROMA_BATCH_SIZE):
        collection.delete(ids=orphaned_ids[start : start + CHROMA_BATCH_SIZE])
    return len(orphaned_ids)


def rebuild_embeddings() -> int:
    validate_chroma_storage()
    with SessionLocal() as db:
        material_ids = [
            material_id
            for (material_id,) in db.query(StudyMaterial.id)
            .order_by(StudyMaterial.id)
            .all()
        ]

        failures: list[tuple[int, str]] = []
        for position, material_id in enumerate(material_ids, start=1):
            logger.info(
                "Rebuilding material embeddings: progress=%s/%s material_id=%s",
                position,
                len(material_ids),
                material_id,
            )
            try:
                result = process_pdf_material(material_id, db=db)
                logger.info(
                    "Material embeddings rebuilt: material_id=%s chunks=%s",
                    material_id,
                    result["chunks_stored"],
                )
            except Exception as error:
                db.rollback()
                failures.append((material_id, str(error)))
                logger.exception(
                    "Material embedding rebuild failed: material_id=%s",
                    material_id,
                )

        if failures:
            for material_id, message in failures:
                logger.error(
                    "Rebuild failure summary: material_id=%s error=%s",
                    material_id,
                    message,
                )
            raise RuntimeError(
                f"Embedding rebuild failed for {len(failures)} of "
                f"{len(material_ids)} materials"
            )

        removed = _remove_orphaned_chunks(set(material_ids))
        logger.info(
            "Embedding rebuild completed: materials=%s orphaned_chunks_removed=%s",
            len(material_ids),
            removed,
        )
        return len(material_ids)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    try:
        rebuild_embeddings()
    except Exception:
        logger.exception("Embedding rebuild did not complete")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
