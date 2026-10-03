"""Validate production configuration and live backend dependencies."""

import json
import os
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import inspect, text  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.metrics import metrics  # noqa: E402
from app.db.database import engine  # noqa: E402
from app.jobs.registry import get_job_registry  # noqa: E402
from app.jobs.scheduler import scheduler, start_scheduler, stop_scheduler  # noqa: E402
from app.services.system_health_service import _migration_details  # noqa: E402
from app.services.vector_service import CHROMA_HOST, get_collection  # noqa: E402
from app.tools.registry import get_tool_registry  # noqa: E402


def environment_status() -> tuple[bool, str]:
    missing = []
    for name, value in (
        ("DATABASE_URL", settings.DATABASE_URL),
        ("GROQ_API_KEY", settings.GROQ_API_KEY),
        ("GOOGLE_CLIENT_ID", settings.GOOGLE_CLIENT_ID),
        ("JWT_SECRET_KEY", settings.JWT_SECRET_KEY),
        ("METRICS_ADMIN_TOKEN", settings.METRICS_ADMIN_TOKEN),
    ):
        if not value or value.strip().startswith("replace-with-"):
            missing.append(name)
    if not settings.REQUIRE_AUTHENTICATED_STUDENT:
        missing.append("REQUIRE_AUTHENTICATED_STUDENT must be true")
    if settings.JWT_ALGORITHM not in {"HS256", "HS384", "HS512"}:
        missing.append("JWT_ALGORITHM must be HS256, HS384, or HS512")
    if not settings.JWT_SECRET_KEY or len(settings.JWT_SECRET_KEY.encode("utf-8")) < 32:
        missing.append("JWT_SECRET_KEY must contain at least 32 bytes")
    if settings.ACCESS_TOKEN_EXPIRE_MINUTES < 1 or settings.REFRESH_TOKEN_EXPIRE_DAYS < 1:
        missing.append("JWT token lifetimes must be positive")
    if not settings.BACKGROUND_JOBS_ENABLED:
        missing.append("BACKGROUND_JOBS_ENABLED must be true")
    return not missing, "configured" if not missing else "; ".join(missing)


def authentication_status() -> tuple[bool, str]:
    if not settings.REQUIRE_AUTHENTICATED_STUDENT:
        return False, "REQUIRE_AUTHENTICATED_STUDENT must be true"
    if not settings.GOOGLE_CLIENT_ID:
        return False, "GOOGLE_CLIENT_ID is missing"
    if not settings.JWT_SECRET_KEY or len(settings.JWT_SECRET_KEY.encode("utf-8")) < 32:
        return False, "JWT_SECRET_KEY must contain at least 32 bytes"
    return True, f"Google OAuth configured; JWT {settings.JWT_ALGORITHM}"


def health_status(base_url: str, path: str) -> tuple[bool, str]:
    try:
        with urlopen(f"{base_url.rstrip('/')}{path}", timeout=8) as response:
            payload = json.loads(response.read())
        if (
            not isinstance(payload, dict)
            or payload.get("success") is not True
            or not isinstance(payload.get("data"), dict)
        ):
            return False, "Invalid health response envelope"
        health = payload["data"]
        if path.endswith("/live"):
            passed = health.get("status") == "alive"
        elif path.endswith("/ready"):
            passed = health.get("ready") is True
        elif path == "/system/health":
            passed = health.get("overall") == "healthy"
        else:
            passed = health.get("status") == "healthy"
        details = ", ".join(
            f"{name}={value}"
            for name, value in health.items()
            if name not in {"status", "ready"}
        )
        return response.status == 200 and passed, details or str(health.get("status"))
    except (OSError, URLError, ValueError) as error:
        return False, f"{type(error).__name__}: endpoint unavailable or returned invalid health data"


def run_validation(base_url: str | None = None) -> dict[str, dict[str, object]]:
    base_url = base_url or os.getenv("HEALTHCHECK_BASE_URL", "http://127.0.0.1:8000")
    results: dict[str, dict[str, object]] = {}

    def check(name: str, operation) -> None:
        try:
            passed, detail = operation()
            results[name] = {"ok": bool(passed), "detail": str(detail)}
        except Exception as error:
            results[name] = {"ok": False, "detail": f"{type(error).__name__}: check failed; see service logs"}

    check("environment", environment_status)
    check("authentication", authentication_status)
    check(
        "database",
        lambda: _database_status(),
    )
    check("chromadb", lambda: _chroma_status())
    check("migrations", lambda: _migration_status())
    check("storage", lambda: _storage_status())
    check("scheduler", lambda: _scheduler_status())
    check("tool_registry", lambda: _tool_status())
    check("job_registry", lambda: _job_status())
    check("metrics", lambda: _metrics_status())
    check("audit_logging", lambda: _audit_status())
    check("health_live", lambda: health_status(base_url, "/health/live"))
    check("health_ready", lambda: health_status(base_url, "/health/ready"))
    check("health_dependencies", lambda: health_status(base_url, "/health/dependencies"))
    check("health", lambda: health_status(base_url, "/health"))
    check("system_health", lambda: health_status(base_url, "/system/health"))
    return results


def _database_status() -> tuple[bool, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True, "connected"


def _chroma_status() -> tuple[bool, str]:
    count = get_collection().count()
    return True, f"connected; {count} embeddings"


def _migration_status() -> tuple[bool, str]:
    state = _migration_details()
    passed = state["status"] == "up_to_date" and len(state["latest_heads"]) == 1
    return passed, json.dumps(state, sort_keys=True)


def _storage_status() -> tuple[bool, str]:
    paths = [BACKEND_ROOT / "uploads"]
    if not CHROMA_HOST:
        paths.append(BACKEND_ROOT / "chroma_db")
    unavailable = [str(path) for path in paths if not path.is_dir() or not os.access(path, os.W_OK)]
    return not unavailable, "writable" if not unavailable else f"missing or not writable: {unavailable}"


def _scheduler_status() -> tuple[bool, str]:
    already_running = scheduler.running
    if not already_running:
        start_scheduler()
    registered = {job.id for job in scheduler.get_jobs()}
    required = {"reminder_generation", "analytics_refresh"}
    if not already_running and scheduler.running:
        stop_scheduler()
    missing = sorted(required - registered)
    return not missing, "registered" if not missing else f"missing jobs: {missing}"


def _tool_status() -> tuple[bool, str]:
    tools = [tool["name"] for tool in get_tool_registry().list_tools()]
    passed = bool(tools) and len(tools) == len(set(tools))
    return passed, f"{len(tools)} unique tools"


def _job_status() -> tuple[bool, str]:
    jobs = [job["name"] for job in get_job_registry().list_jobs()]
    passed = bool(jobs) and len(jobs) == len(set(jobs))
    return passed, f"{len(jobs)} unique jobs"


def _metrics_status() -> tuple[bool, str]:
    data = metrics.get_metrics()
    return isinstance(data, dict) and "total_requests" in data, "collector operational"


def _audit_status() -> tuple[bool, str]:
    present = "audit_logs" in inspect(engine).get_table_names()
    return present, "audit_logs table present" if present else "audit_logs table missing"


def format_report(results: dict[str, dict[str, object]]) -> str:
    def row(name: str) -> str:
        result = results.get(name, {"ok": False, "detail": "not run"})
        status = "PASS" if result["ok"] else "FAIL"
        return f"| {name.replace('_', ' ').title()} | {status} | {result['detail']} |"

    lines = [
        "# Jarvis Deployment Validation Report",
        "",
        "Generated from the current deployment validator run. A failed or unavailable check is not a production sign-off.",
        "",
        "## Environment Status",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for name in ("environment", "storage"):
        if name in results:
            lines.append(row(name))
    lines.extend(["", "## Migration Status", "| Check | Status | Detail |", "|---|---|---|"])
    lines.append(row("migrations"))
    lines.extend(["", "## Health Status", "| Check | Status | Detail |", "|---|---|---|"])
    for name in ("health_live", "health_ready", "health_dependencies", "health", "system_health"):
        if name in results:
            lines.append(row(name))
    lines.extend(["", "## Authentication Status", "| Check | Status | Detail |", "|---|---|---|"])
    lines.extend([row("authentication"), row("health_ready")])
    lines.extend(["", "## Scheduler, Jobs, and Metrics", "| Check | Status | Detail |", "|---|---|---|"])
    for name in ("scheduler", "job_registry", "metrics", "audit_logging", "tool_registry"):
        lines.append(row(name))
    lines.extend(
        [
            "",
            "## Known Risks",
            "- Google login requires a live Google-issued ID token and a configured OAuth client ID; the validator checks configuration, not Google user credentials.",
            "- Docker startup, end-to-end workflows, and concurrency checks must be run against the target deployment before release.",
            "",
            "## Recommendations",
            "- Resolve every failed check, apply migrations, and rerun this validator against the deployed health URL.",
            "- Run the authenticated E2E and load validation scripts with a short-lived test student token in staging.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    results = run_validation()
    report_path = Path(os.getenv("DEPLOYMENT_REPORT_PATH", REPO_ROOT / "deployment_report.md"))
    report_path.write_text(format_report(results), encoding="utf-8")
    print(json.dumps(results, indent=2))
    print(f"Report written to {report_path}")
    failed = [name for name, result in results.items() if not result["ok"]]
    if failed:
        print(f"Deployment validation failed: {', '.join(failed)}", file=sys.stderr)
        return 1
    print("Deployment validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())