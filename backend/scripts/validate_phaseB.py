from __future__ import annotations

import subprocess
import sys
import importlib
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.agents.agent_registry import create_default_registry
from app.agents.director_agent import create_execution_plan
from app.db.database import Base
from app.main import app as fastapi_app
importlib.import_module("app.db.models")

HEAD = "e6b2d8a4c913"


def main() -> None:
    script = ScriptDirectory.from_config(Config(str(BACKEND / "alembic.ini")))
    if script.get_heads() != [HEAD]:
        raise RuntimeError(f"Expected one Phase B/C migration head {HEAD}: {script.get_heads()}")

    required_tables = {
        "student_goals", "goal_milestones", "goal_progress", "habits", "habit_logs",
        "habit_streaks", "student_connectors", "sync_jobs", "sync_history", "study_blocks",
    }
    missing_tables = required_tables.difference(Base.metadata.tables)
    if missing_tables:
        raise RuntimeError(f"Missing Phase B/C models: {sorted(missing_tables)}")

    paths = fastapi_app.openapi()["paths"]
    required_paths = {
        "/api/goals/{student_id}", "/api/milestones/{goal_id}",
        "/api/progress/{goal_id}", "/api/habits/{student_id}",
        "/api/habits/{habit_id}/logs", "/api/connectors/{student_id}",
        "/api/connectors/{connector_id}/sync", "/api/connectors/{connector_id}/history",
        "/api/schedule/{student_id}/intelligent", "/api/calendar/{student_id}/today",
        "/api/calendar/{student_id}/tomorrow", "/api/calendar/{student_id}/week",
    }
    missing_paths = required_paths.difference(paths)
    if missing_paths:
        raise RuntimeError(f"Missing Phase B/C routes: {sorted(missing_paths)}")

    agents = set(create_default_registry().names())
    if not {"productivity", "semester_copilot"}.issubset(agents):
        raise RuntimeError("Productivity and semester copilot agents must be registered")
    for phrase, expected in (
        ("goal habit productivity consistency focus routine", "productivity"),
        ("exam command center readiness forecast", "semester_copilot"),
    ):
        if expected not in create_execution_plan(phrase)["agents"]:
            raise RuntimeError(f"Director does not route {phrase!r} to {expected}")

    subprocess.run(
        [sys.executable, "-W", "ignore", "-m", "unittest", "tests.test_phaseB_C", "-q"],
        cwd=BACKEND,
        check=True,
    )
    print("Goals, habits, scheduler, notifications, productivity, dashboard, connectors, and director verified")
    print("PHASE B VALIDATION PASSED")


if __name__ == "__main__":
    main()
