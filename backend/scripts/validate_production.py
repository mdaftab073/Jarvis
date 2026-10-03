"""Validate backend dependencies and deployment configuration before release."""

import json
import os
import re
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from sqlalchemy import inspect, text

from app.core.config import settings
from app.db.database import engine
from app.jobs.registry import get_job_registry
from app.jobs.scheduler import scheduler, start_scheduler, stop_scheduler
from app.services.system_health_service import _migration_details
from app.services.vector_service import get_collection
from app.tools.registry import get_tool_registry


BACKEND_ROOT = Path(__file__).resolve().parents[1]
RATE_LIMIT_PATTERN = re.compile(r"^\d+/(second|minute|hour|day)s?$", re.IGNORECASE)


def validate_rate_limit(value: str) -> bool:
    return bool(RATE_LIMIT_PATTERN.fullmatch(value.strip()))


def validate_endpoint(base_url: str, path: str) -> tuple[bool, str]:
    try:
        with urlopen(f"{base_url.rstrip('/')}{path}", timeout=5) as response:
            payload = json.loads(response.read())
        if path.endswith("/ready"):
            healthy = payload.get("ready") is True
        elif path.endswith("/dependencies") or path == "/health":
            healthy = payload.get("status") == "healthy"
        else:
            healthy = payload.get("status") == "alive"
        return response.status == 200 and healthy, str(payload.get("status", "missing status"))
    except (OSError, URLError, ValueError) as error:
        return False, str(error)


def run_validation() -> dict[str, dict[str, object]]:
    results: dict[str, dict[str, object]] = {}

    def check(name: str, operation) -> None:
        try:
            value = operation()
            passed, detail = value if isinstance(value, tuple) else (bool(value), str(value))
            results[name] = {"ok": passed, "detail": detail}
        except Exception as error:
            results[name] = {"ok": False, "detail": f"{type(error).__name__}: {error}"}

    def check_database():
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, "connected"

    def check_chroma():
        get_collection().count()
        return True, "connected"

    def check_scheduler():
        was_running = scheduler.running
        if not was_running and settings.BACKGROUND_JOBS_ENABLED:
            start_scheduler()
        running = scheduler.running or not settings.BACKGROUND_JOBS_ENABLED
        if not was_running and scheduler.running:
            stop_scheduler()
        return running, "running" if running else "disabled unexpectedly"

    def check_tools():
        names = [tool["name"] for tool in get_tool_registry().list_tools()]
        return bool(names) and len(names) == len(set(names)), f"{len(names)} unique tools"

    def check_jobs():
        names = [job["name"] for job in get_job_registry().list_jobs()]
        return bool(names) and len(names) == len(set(names)), f"{len(names)} unique jobs"

    def check_migrations():
        state = _migration_details()
        return state["status"] == "up_to_date" and len(state["latest_heads"]) == 1, state

    def check_environment():
        required = {"DATABASE_URL": settings.DATABASE_URL, "GROQ_API_KEY": settings.GROQ_API_KEY}
        missing = [key for key, value in required.items() if not value or value.startswith("replace-with-")]
        if not settings.METRICS_ADMIN_TOKEN:
            missing.append("METRICS_ADMIN_TOKEN")
        return not missing, "configured" if not missing else ", ".join(missing)

    def check_storage():
        paths = [BACKEND_ROOT / "uploads", BACKEND_ROOT / settings.CHROMA_PERSISTENT_DIRECTORY]
        problems = [str(path) for path in paths if not path.exists() or not os.access(path, os.W_OK)]
        return not problems, "writable" if not problems else f"not writable: {', '.join(problems)}"

    def check_rate_limits():
        configured = {
            "CHAT_RATE_LIMIT": settings.CHAT_RATE_LIMIT,
            "RAG_RATE_LIMIT": settings.RAG_RATE_LIMIT,
            "CONNECTOR_SYNC_RATE_LIMIT": settings.CONNECTOR_SYNC_RATE_LIMIT,
            "ALERT_GENERATION_RATE_LIMIT": settings.ALERT_GENERATION_RATE_LIMIT,
            "UPLOAD_RATE_LIMIT": settings.UPLOAD_RATE_LIMIT,
        }
        invalid = [name for name, value in configured.items() if not validate_rate_limit(value)]
        return not invalid, "valid" if not invalid else f"invalid: {', '.join(invalid)}"

    check("database", check_database)
    check("chromadb", check_chroma)
    check("scheduler", check_scheduler)
    check("tool_registry", check_tools)
    check("job_registration", check_jobs)
    check("migrations", check_migrations)
    check("environment", check_environment)
    check("storage_paths", check_storage)
    check("rate_limits", check_rate_limits)
    check("audit_logging", lambda: ("audit_logs" in inspect(engine).get_table_names(), "audit_logs table present"))

    base_url = os.getenv("HEALTHCHECK_BASE_URL", "http://127.0.0.1:8000")
    check("health_live", lambda: validate_endpoint(base_url, "/health/live"))
    check("health_ready", lambda: validate_endpoint(base_url, "/health/ready"))
    check("health_dependencies", lambda: validate_endpoint(base_url, "/health/dependencies"))
    return results


def main() -> int:
    results = run_validation()
    print(json.dumps(results, indent=2, default=str))
    failed = [name for name, result in results.items() if not result["ok"]]
    if failed:
        print(f"Production validation failed: {', '.join(failed)}", file=sys.stderr)
        return 1
    print("Production validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())