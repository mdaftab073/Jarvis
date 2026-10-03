import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, text

from app.core.config import settings
from app.db.database import engine
from app.jobs.scheduler import scheduler
from app.core.metrics import metrics
from app.services.system_health_service import _migration_state
from app.services.mis.configuration import get_mis_site_configuration
from app.services.mis.client import MISClientError
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
        get_mis_site_configuration()
        statuses["mis"] = "ok"
    except MISClientError:
        statuses["mis"] = "error"
    try:
        statuses["migrations"] = "ok" if _migration_state() == "up_to_date" else "pending"
    except Exception:
        logger.exception("Health migration check failed")
        statuses["migrations"] = "error"
    try:
        statuses["metrics"] = "ok" if isinstance(metrics.get_metrics(), dict) else "error"
    except Exception:
        logger.exception("Health metrics check failed")
        statuses["metrics"] = "error"
    try:
        statuses["audit_logging"] = "ok" if "audit_logs" in inspect(engine).get_table_names() else "error"
    except Exception:
        logger.exception("Health audit logging check failed")
        statuses["audit_logging"] = "error"
    statuses["authentication"] = (
        "ok"
        if not settings.REQUIRE_AUTHENTICATED_STUDENT
        or (settings.JWT_SECRET_KEY and settings.GOOGLE_CLIENT_ID)
        else "error"
    )
    return statuses


@router.get("/health/live")
def health_live():
    return {"status": "alive"}


@router.get("/health/ready")
def health_ready():
    checks = dependency_status()
    ready = all(checks[key] == "ok" for key in (
        "database", "chromadb", "scheduler", "tool_registry", "migrations",
        "metrics", "audit_logging", "authentication",
    ))
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ready" if ready else "not_ready", "ready": ready, **checks},
    )


@router.get("/health/dependencies")
def health_dependencies():
    checks = dependency_status()
    healthy = all(checks[key] == "ok" for key in (
        "database", "chromadb", "scheduler", "tool_registry", "migrations",
        "metrics", "audit_logging", "authentication",
    ))
    return JSONResponse(status_code=200 if healthy else 503, content={"status": "healthy" if healthy else "degraded", **checks})


@router.get("/health")
def health_check():
    checks = dependency_status()
    healthy = all(checks[key] == "ok" for key in (
        "database", "chromadb", "scheduler", "tool_registry", "migrations",
        "metrics", "audit_logging", "authentication",
    ))
    return JSONResponse(status_code=200 if healthy else 503, content={"status": "healthy" if healthy else "degraded", **checks})
