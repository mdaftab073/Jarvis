import logging
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from app.core.config import settings
from app.db import models
from app.db.database import Base, engine
from app.services.vector_service import get_chroma_client, get_collection

logger = logging.getLogger(__name__)
BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _migration_state() -> str:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(config)
    expected_heads = set(script.get_heads())
    with engine.connect() as connection:
        current = {
            row[0]
            for row in connection.execute(text("SELECT version_num FROM alembic_version"))
        }
    return "up_to_date" if current == expected_heads else "pending"


def get_system_health() -> dict:
    statuses = {
        "database": "unhealthy",
        "chroma": "unhealthy",
        "groq": "configured" if settings.GROQ_API_KEY.strip() else "missing",
        "migrations": "unknown",
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
    statuses["overall"] = (
        "healthy"
        if statuses["database"] == "healthy"
        and statuses["chroma"] == "healthy"
        and statuses["groq"] == "configured"
        and statuses["migrations"] == "up_to_date"
        else "degraded"
    )
    return statuses


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
        collection_names = {
            getattr(collection, "name", collection)
            for collection in chroma_client.list_collections()
        }
        checks["chroma"] = "study_materials" in collection_names
    except Exception as error:
        checks["chroma"] = False
        checks["chroma_error"] = str(error)

    try:
        existing_tables = set(inspect(engine).get_table_names())
        required_tables = set(Base.metadata.tables)
        missing_tables = sorted(required_tables - existing_tables)
        checks["required_tables"] = not missing_tables
        checks["missing_tables"] = missing_tables
    except Exception as error:
        checks["required_tables"] = False
        checks["tables_error"] = str(error)

    try:
        migration_state = _migration_state()
        checks["alembic_head"] = migration_state == "up_to_date"
        checks["migration_state"] = migration_state
    except Exception as error:
        checks["alembic_head"] = False
        checks["migration_error"] = str(error)

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
            "alembic_head",
            "environment",
            "agent_registry",
            "api_routes",
        )
    )
    return checks