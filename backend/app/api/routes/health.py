import json
import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.db.database import engine
from app.jobs.scheduler import scheduler
from app.services.system_health_service import _migration_state
from app.services.vector_service import get_collection
from app.tools.registry import get_tool_registry

router = APIRouter()
logger = logging.getLogger(__name__)


def dependency_status() -> dict:
    statuses = {}
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        statuses["database"] = "ok"
    except Exception:
        logger.exception("Health database check failed")
        statuses["database"] = "error"
    try:
        get_collection().count()
        statuses["chromadb"] = "ok"
    except Exception:
        logger.exception("Health ChromaDB check failed")
        statuses["chromadb"] = "error"
    statuses["scheduler"] = "ok" if scheduler.running or not settings.BACKGROUND_JOBS_ENABLED else "error"
    try:
        statuses["tool_registry"] = "ok" if len(get_tool_registry().list_tools()) >= 32 else "error"
    except Exception:
        logger.exception("Health tool registry check failed")
        statuses["tool_registry"] = "error"
    try:
        connectors = json.loads(settings.CONNECTOR_ENDPOINTS_JSON)
        statuses["mis"] = "ok" if isinstance(connectors, dict) else "error"
    except (TypeError, ValueError):
        statuses["mis"] = "error"
    try:
        statuses["migrations"] = "ok" if _migration_state() == "up_to_date" else "pending"
    except Exception:
        logger.exception("Health migration check failed")
        statuses["migrations"] = "error"
    return statuses


@router.get("/health/live")
def health_live():
    return {"status": "alive"}


@router.get("/health/ready")
def health_ready():
    checks = dependency_status()
    ready = all(checks[key] == "ok" for key in ("database", "chromadb", "scheduler", "tool_registry", "migrations"))
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ready" if ready else "not_ready", "ready": ready, **checks},
    )


@router.get("/health/dependencies")
def health_dependencies():
    checks = dependency_status()
    healthy = all(checks[key] == "ok" for key in ("database", "chromadb", "scheduler", "tool_registry", "migrations"))
    return JSONResponse(status_code=200 if healthy else 503, content={"status": "healthy" if healthy else "degraded", **checks})


@router.get("/health")
def health_check():
    checks = dependency_status()
    healthy = all(checks[key] == "ok" for key in ("database", "chromadb", "scheduler", "tool_registry", "migrations"))
    return JSONResponse(status_code=200 if healthy else 503, content={"status": "healthy" if healthy else "degraded", **checks})
