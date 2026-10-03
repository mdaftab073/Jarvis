from __future__ import annotations

import importlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from app.agents.agent_registry import create_default_registry  # noqa: E402
from app.db.database import Base  # noqa: E402
import app.db.models  # noqa: E402, F401
from app.main import app  # noqa: E402


def validate_migrations() -> None:
    alembic_config = Config(str(BACKEND / "alembic.ini"))
    script = ScriptDirectory.from_config(alembic_config)
    heads = script.get_heads()
    if heads != ["e6b2d8a4c913"]:
        raise RuntimeError(f"Expected one Phase A head, found {heads}")

    with tempfile.TemporaryDirectory(prefix="jarvis-phase-a-") as directory:
        database_path = Path(directory) / "validation.sqlite"
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite:///{database_path.as_posix()}"
        env.setdefault("GROQ_API_KEY", "phase-a-validation")
        for command in (
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            [sys.executable, "-m", "alembic", "downgrade", "b25c9e1f3a40"],
            [sys.executable, "-m", "alembic", "upgrade", "head"],
        ):
            subprocess.run(command, cwd=BACKEND, env=env, check=True, capture_output=True, text=True)


def validate_application() -> int:
    expected_tables = {
        "student_academic_profiles", "attendance_records", "grade_records", "deadline_items",
        "student_notifications", "calendar_events", "study_blocks", "reminders",
        "student_goals", "student_preferences", "student_habits",
    }
    missing_tables = expected_tables.difference(Base.metadata.tables)
    if missing_tables:
        raise RuntimeError(f"Missing ORM tables: {sorted(missing_tables)}")

    expected_routes = {
        "/api/academic-profiles/{student_id}", "/api/attendance/{student_id}",
        "/api/grades/{student_id}", "/api/deadlines/{student_id}",
        "/api/notifications/{student_id}", "/api/calendar/{student_id}",
        "/api/schedule/{student_id}", "/api/dashboard/{student_id}",
    }
    openapi_paths = app.openapi()["paths"]
    missing_routes = expected_routes.difference(openapi_paths)
    if missing_routes:
        raise RuntimeError(f"Missing OpenAPI routes: {sorted(missing_routes)}")

    service_names = (
        "academic_profile_service", "attendance_service", "grade_service", "deadline_service",
        "notification_service", "calendar_service", "scheduler_service", "reminder_service",
        "dashboard_service",
    )
    for name in service_names:
        importlib.import_module(f"app.services.{name}")

    expected_agents = {
        "academic_profile", "attendance", "deadline", "notification", "calendar", "scheduler", "reminder",
    }
    actual_agents = set(create_default_registry().names())
    if not expected_agents.issubset(actual_agents):
        raise RuntimeError(f"Missing registered agents: {sorted(expected_agents - actual_agents)}")

    if not (BACKEND / "tests" / "test_phaseA_student_os.py").exists():
        raise RuntimeError("Phase A test module is missing")
    return len([path for path in openapi_paths if path.startswith("/api/")])


def main() -> None:
    validate_migrations()
    route_count = validate_application()
    subprocess.run(
        [sys.executable, "-W", "ignore", "-m", "unittest", "tests.test_phaseA_student_os"],
        cwd=BACKEND,
        check=True,
    )
    print(f"Phase A migration lifecycle verified; API routes: {route_count}")
    print("Models, services, agents, dashboard, and tests verified")
    print("PHASE A VALIDATION PASSED")


if __name__ == "__main__":
    main()
