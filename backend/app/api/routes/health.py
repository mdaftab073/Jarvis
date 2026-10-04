import logging

from fastapi import APIRouter
from fastapi import Response
from sqlalchemy import inspect, text

from app.core.config import settings
from app.db.database import engine
from app.jobs.scheduler import scheduler
from app.jobs.worker_state import get_worker_health
from app.core.metrics import metrics
from app.services.system_health_service import _migration_state
from app.services.vector_service import chroma_status, validate_rag_storage
from app.tools.registry import get_tool_registry

router = APIRouter()
logger = logging.getLogger(__name__)


def dependency_status() -> dict:
    statuses = {}
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        statuses["database"] = "healthy"
    except Exception:
        logger.exception("Health database check failed")
        statuses["database"] = "degraded"
    try:
        validate_rag_storage()
        statuses["chromadb"] = "ok"
    except Exception:
        logger.exception("Health ChromaDB check failed")
        statuses["chromadb"] = "error"
    statuses["chroma"] = chroma_status()
    statuses["scheduler"] = "ok" if scheduler.running or not settings.BACKGROUND_JOBS_ENABLED else "error"
    try:
        statuses["worker"] = get_worker_health()
    except Exception:
        logger.exception("Health worker check failed")
        statuses["worker"] = {
            "status": "unhealthy",
            "last_heartbeat": None,
            "pending_jobs": None,
        }
    try:
        tools = get_tool_registry().list_tools()
        names = [tool["name"] for tool in tools]
        statuses["tool_registry"] = "ok" if names and len(names) == len(set(names)) else "error"
    except Exception:
        logger.exception("Health tool registry check failed")
        statuses["tool_registry"] = "error"
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
        if settings.REQUIRE_AUTHENTICATED_STUDENT
        and settings.JWT_SECRET_KEY
        and settings.GOOGLE_CLIENT_ID
        else "error"
    )
    return statuses


@router.get("/health/live")
def health_live():
    return {"status": "alive"}


@router.get("/health/ready")
def health_ready(response: Response):
    checks = dependency_status()
    ready = (
        checks["database"] == "healthy"
        and checks["chromadb"] == "ok"
        and checks["scheduler"] == "ok"
        and checks["tool_registry"] == "ok"
        and checks["migrations"] == "ok"
        and checks["metrics"] == "ok"
        and checks["audit_logging"] == "ok"
        and checks["authentication"] == "ok"
        and checks["worker"]["status"] == "healthy"
    )
    response.status_code = 200 if ready else 503
    return {"status": "ready" if ready else "not_ready", "ready": ready, **checks}


@router.get("/health/dependencies")
def health_dependencies(response: Response):
    checks = dependency_status()
    healthy = (
        checks["database"] == "healthy"
        and checks["chromadb"] == "ok"
        and checks["scheduler"] == "ok"
        and checks["tool_registry"] == "ok"
        and checks["migrations"] == "ok"
        and checks["metrics"] == "ok"
        and checks["audit_logging"] == "ok"
        and checks["authentication"] == "ok"
        and checks["worker"]["status"] == "healthy"
    )
    response.status_code = 200 if healthy else 503
    return {"status": "healthy" if healthy else "degraded", **checks}


@router.get("/health")
def health_check(response: Response):
    checks = dependency_status()
    healthy = (
        checks["database"] == "healthy"
        and checks["chromadb"] == "ok"
        and checks["scheduler"] == "ok"
        and checks["tool_registry"] == "ok"
        and checks["migrations"] == "ok"
        and checks["metrics"] == "ok"
        and checks["audit_logging"] == "ok"
        and checks["authentication"] == "ok"
        and checks["worker"]["status"] == "healthy"
    )
    response.status_code = 200 if healthy else 503
    return {"status": "healthy" if healthy else "degraded", **checks}
