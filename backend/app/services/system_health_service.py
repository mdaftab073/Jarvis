import logging
import time
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from app.core.config import settings
from app.db import models
from app.db.database import engine
from app.services.vector_service import get_chroma_client, get_collection

logger = logging.getLogger(__name__)
BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _migration_details() -> dict:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(config)
    expected_heads = set(script.get_heads())
    with engine.connect() as connection:
        current = {
            row[0]
            for row in connection.execute(text("SELECT version_num FROM alembic_version"))
        }
    return {
        "current_revisions": sorted(current),
        "latest_heads": sorted(expected_heads),
        "status": "up_to_date" if current == expected_heads else "pending",
    }


def _migration_state() -> str:
    return _migration_details()["status"]


SYSTEM_START_TIME = time.time()


def get_system_health() -> dict:
    statuses = {
        "database": "unhealthy",
        "chroma": "unhealthy",
        "groq": "configured" if settings.GROQ_API_KEY.strip() else "missing",
        "migrations": "unknown",
        "agents": "healthy",
        "version": settings.VERSION,
        "uptime_seconds": round(time.time() - SYSTEM_START_TIME, 2),
    }
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        statuses["database"] = "healthy"
    except Exception:
        logger.exception("System health database check failed")
    try:
        get_collection().count()
        statuses["chroma"] = "healthy"
    except Exception:
        logger.exception("System health ChromaDB check failed")
    try:
        statuses["migrations"] = _migration_state()
    except Exception:
        logger.exception("System health migration check failed")
    try:
        from app.agents.agent_registry import create_default_registry
        reg = create_default_registry()
        expected = {"analytics", "study", "pyq", "retrieval", "memory", "semester"}
        statuses["agents"] = "healthy" if expected.issubset(set(reg.names())) else "unhealthy"
    except Exception:
        logger.exception("System health agent check failed")
        statuses["agents"] = "unhealthy"

    statuses["overall"] = (
        "healthy"
        if statuses["database"] == "healthy"
        and statuses["chroma"] == "healthy"
        and statuses["groq"] == "configured"
        and statuses["migrations"] == "up_to_date"
        and statuses["agents"] == "healthy"
        else "degraded"
    )
    return statuses


def get_system_readiness() -> dict:
    health = get_system_health()
    is_ready = (
        health["database"] == "healthy"
        and health["chroma"] == "healthy"
        and health["migrations"] == "up_to_date"
        and health.get("agents") == "healthy"
    )
    return {
        "status": "ready" if is_ready else "not_ready",
        "ready": is_ready,
        "version": health["version"],
        "uptime_seconds": health["uptime_seconds"],
        "database_connected": health["database"] == "healthy",
        "chroma_connected": health["chroma"] == "healthy",
        "migrations_up_to_date": health["migrations"] == "up_to_date",
        "agents_registered": health["agents"] == "healthy",
    }



def validate_system() -> dict:
    checks = {}
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as error:
        checks["database"] = False
        checks["database_error"] = str(error)

    try:
        chroma_client = get_chroma_client()
        collections = chroma_client.list_collections()
        collection_names = {
            getattr(collection, "name", collection)
            for collection in collections
        }
        checks["chroma"] = "study_materials" in collection_names
        checks["chroma_collections"] = sorted(str(name) for name in collection_names)
        checks["chroma_items"] = get_collection().count()
    except Exception as error:
        checks["chroma"] = False
        checks["chroma_error"] = str(error)

    try:
        existing_tables = set(inspect(engine).get_table_names())
        required_tables = set(models.Base.metadata.tables)
        missing_tables = sorted(required_tables - existing_tables)
        checks["tables"] = sorted(existing_tables)
        checks["expected_tables"] = sorted(required_tables)
        checks["required_tables"] = not missing_tables
        checks["missing_tables"] = missing_tables
    except Exception as error:
        existing_tables = set()
        checks["required_tables"] = False
        checks["tables_error"] = str(error)

    try:
        migration = _migration_details()
        checks["current_revisions"] = migration["current_revisions"]
        checks["latest_heads"] = migration["latest_heads"]
        checks["current_revision"] = (
            migration["current_revisions"][0]
            if len(migration["current_revisions"]) == 1
            else None
        )
        checks["latest_head"] = (
            migration["latest_heads"][0]
            if len(migration["latest_heads"]) == 1
            else None
        )
        checks["migration_state"] = migration["status"]
        checks["alembic_head"] = (
            migration["status"] == "up_to_date"
            and len(migration["latest_heads"]) == 1
        )
    except Exception as error:
        checks["alembic_head"] = False
        checks["migration_error"] = str(error)

    try:
        inspector = inspect(engine)
        missing_indexes = []
        missing_foreign_keys = []
        actual_foreign_keys = {}
        orphaned_foreign_keys = []
        expected_index_count = 0
        verified_index_count = 0
        expected_foreign_key_count = sum(
            len(table.foreign_keys) for table in models.Base.metadata.tables.values()
        )
        verified_foreign_key_count = 0
        for table_name, table in models.Base.metadata.tables.items():
            if table_name not in existing_tables:
                continue
            database_indexes = {
                item["name"] for item in inspector.get_indexes(table_name)
            }
            expected_index_count += len(table.indexes)
            verified_index_count += sum(
                index.name in database_indexes for index in table.indexes
            )
            for index in table.indexes:
                if index.name not in database_indexes:
                    missing_indexes.append(f"{table_name}.{index.name}")
            actual = inspector.get_foreign_keys(table_name)
            actual_foreign_keys[table_name] = actual
            for foreign_key in table.foreign_keys:
                found = any(
                    item["constrained_columns"] == [foreign_key.parent.name]
                    and item["referred_table"] == foreign_key.column.table.name
                    and item["referred_columns"] == [foreign_key.column.name]
                    for item in actual
                )
                if not found:
                    missing_foreign_keys.append(
                        f"{table_name}.{foreign_key.parent.name}"
                    )
                else:
                    verified_foreign_key_count += 1

        with engine.connect() as connection:
            for table_name, foreign_keys in actual_foreign_keys.items():
                for foreign_key in foreign_keys:
                    local_columns = foreign_key["constrained_columns"]
                    remote_columns = foreign_key["referred_columns"]
                    if len(local_columns) != 1 or len(remote_columns) != 1:
                        continue
                    local_column = local_columns[0]
                    remote_column = remote_columns[0]
                    parent_table = foreign_key["referred_table"]
                    quote = engine.dialect.identifier_preparer.quote
                    query = text(
                        f"SELECT COUNT(*) FROM {quote(table_name)} AS child "
                        f"LEFT JOIN {quote(parent_table)} AS parent "
                        f"ON child.{quote(local_column)} = parent.{quote(remote_column)} "
                        f"WHERE child.{quote(local_column)} IS NOT NULL "
                        f"AND parent.{quote(remote_column)} IS NULL"
                    )
                    orphan_count = connection.execute(query).scalar_one()
                    if orphan_count:
                        orphaned_foreign_keys.append(
                            {
                                "constraint": (
                                    f"{table_name}.{local_column}->"
                                    f"{parent_table}.{remote_column}"
                                ),
                                "orphan_rows": orphan_count,
                            }
                        )
        checks["missing_indexes"] = sorted(missing_indexes)
        checks["expected_index_count"] = expected_index_count
        checks["verified_index_count"] = verified_index_count
        checks["index_integrity"] = not missing_indexes and not checks.get("missing_tables")
        checks["missing_foreign_keys"] = sorted(missing_foreign_keys)
        checks["expected_foreign_key_count"] = expected_foreign_key_count
        checks["verified_foreign_key_count"] = verified_foreign_key_count
        checks["orphaned_foreign_keys"] = orphaned_foreign_keys
        checks["foreign_key_integrity"] = (
            not missing_foreign_keys
            and not orphaned_foreign_keys
            and not checks.get("missing_tables")
        )
    except Exception as error:
        checks["index_integrity"] = False
        checks["foreign_key_integrity"] = False
        checks["integrity_error"] = str(error)

    checks["environment"] = bool(
        settings.DATABASE_URL.strip() and settings.GROQ_API_KEY.strip()
    )
    try:
        from app.agents.agent_registry import create_default_registry

        checks["agent_registry"] = set(create_default_registry().names()) == {
            "analytics",
            "study",
            "pyq",
            "retrieval",
            "memory",
            "semester",
        }
    except Exception as error:
        checks["agent_registry"] = False
        checks["agent_registry_error"] = str(error)

    try:
        from app.main import app

        paths = set(app.openapi()["paths"])
        required_paths = {
            "/api/director/academic",
            "/api/director/debug-plan",
            "/system/health",
        }
        checks["api_routes"] = required_paths <= paths
        checks["missing_routes"] = sorted(required_paths - paths)
    except Exception as error:
        checks["api_routes"] = False
        checks["api_routes_error"] = str(error)

    checks["success"] = all(
        checks.get(name, False)
        for name in (
            "database",
            "chroma",
            "required_tables",
            "index_integrity",
            "foreign_key_integrity",
            "alembic_head",
            "environment",
            "agent_registry",
            "api_routes",
        )
    )
    return checks