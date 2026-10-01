from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from app.agents.agent_registry import create_default_registry
from app.agents.director_agent import create_execution_plan
from app.db.database import Base
from app.db.models import AcademicDeadline, DeadlineItem, GradeRecord
from app.main import app
from app.services.grade_service import calculate_cpi, calculate_spi

HEAD = "e6b2d8a4c913"
PRE_STABILIZATION_HEAD = "c82d4e6f1a30"


def _alembic(env: dict[str, str], *args: str) -> None:
    subprocess.run(
        [sys.executable, "-W", "ignore", "-m", "alembic", *args],
        cwd=BACKEND,
        env=env,
        check=True,
    )


def validate_migration_history() -> None:
    script = ScriptDirectory.from_config(Config(str(BACKEND / "alembic.ini")))
    if script.get_heads() != [HEAD]:
        raise RuntimeError(f"Expected one head {HEAD}, found {script.get_heads()}")

    with tempfile.TemporaryDirectory(prefix="jarvis-stabilization-") as directory:
        database_path = Path(directory) / "historical.sqlite"
        database_url = f"sqlite:///{database_path.as_posix()}"
        env = os.environ.copy()
        env["DATABASE_URL"] = database_url
        env.setdefault("GROQ_API_KEY", "stabilization-validation")
        _alembic(env, "upgrade", PRE_STABILIZATION_HEAD)

        engine = create_engine(database_url)
        with engine.begin() as connection:
            student_id = connection.execute(
                text("INSERT INTO students (name, email) VALUES ('Historical', 'historical@example.test')")
            ).lastrowid
            course_id = connection.execute(
                text("INSERT INTO courses (name, student_id) VALUES ('CS', :student_id)"),
                {"student_id": student_id},
            ).lastrowid
            subject_id = connection.execute(
                text("INSERT INTO subjects (name, course_id) VALUES ('Algorithms', :course_id)"),
                {"course_id": course_id},
            ).lastrowid
            profile_id = connection.execute(
                text("INSERT INTO student_academic_profiles (student_id) VALUES (:student_id)"),
                {"student_id": student_id},
            ).lastrowid
            connection.execute(
                text("INSERT INTO attendance_records (academic_profile_id, subject_id, attended_classes, total_classes, attendance_percentage) VALUES (:profile_id, :subject_id, 8, 10, 80)"),
                {"profile_id": profile_id, "subject_id": subject_id},
            )
            connection.execute(
                text("INSERT INTO grade_records (academic_profile_id, subject_id, component_type, obtained_marks, max_marks, grade_letter, grade) VALUES (:profile_id, :subject_id, 'CT1', 80, 100, 'B', 'C')"),
                {"profile_id": profile_id, "subject_id": subject_id},
            )
            connection.execute(
                text("INSERT INTO grade_records (academic_profile_id, subject_id, component_type, obtained_marks, max_marks, semester, credits, grade, grade_points) VALUES (:profile_id, :subject_id, 'OTHER', 90, 100, 2, 3, 'A', 8)"),
                {"profile_id": profile_id, "subject_id": subject_id},
            )
            connection.execute(
                text("INSERT INTO deadline_items (academic_profile_id, title, item_type, due_date, priority, is_completed) VALUES (:profile_id, 'Final', 'EXAM', '2026-10-10 09:00:00', 'HIGH', 0)"),
                {"profile_id": profile_id},
            )
            connection.execute(
                text("INSERT INTO study_activity_logs (academic_profile_id, activity_type, duration_minutes) VALUES (:profile_id, 'READING', 30)"),
                {"profile_id": profile_id},
            )
            connection.execute(
                text("INSERT INTO digital_twin_snapshots (academic_profile_id, risk_level) VALUES (:profile_id, 'LOW')"),
                {"profile_id": profile_id},
            )
            connection.execute(
                text("INSERT INTO student_habits (student_id, habit_name, streak, completion_rate) VALUES (:student_id, 'Daily review', 5, 70)"),
                {"student_id": student_id},
            )
        engine.dispose()

        _alembic(env, "upgrade", "head")
        engine = create_engine(database_url)
        with engine.connect() as connection:
            for table in ("attendance_records", "grade_records", "deadline_items", "study_activity_logs", "digital_twin_snapshots"):
                owner_ids = connection.execute(text(f"SELECT DISTINCT student_id FROM {table}")).scalars().all()
                if owner_ids != [student_id]:
                    raise RuntimeError(f"Historical ownership backfill failed for {table}: {owner_ids}")
            classifications = connection.execute(
                text("SELECT grade_type, grade_letter FROM grade_records ORDER BY id")
            ).all()
            if classifications != [("COMPONENT", "C"), ("FINAL", "A")]:
                raise RuntimeError(f"Historical grade conversion failed: {classifications}")
            if "grade" in {column["name"] for column in inspect(connection).get_columns("grade_records")}:
                raise RuntimeError("Duplicate grade storage column remains")
            habit_backfill = connection.execute(
                text("SELECT habits.category, habit_streaks.current_streak, habit_streaks.completion_rate "
                     "FROM habits JOIN habit_streaks ON habit_streaks.habit_id = habits.id "
                     "WHERE habits.student_id = :student_id AND habits.habit_name = 'Daily review'"),
                {"student_id": student_id},
            ).one_or_none()
            if habit_backfill != ("OTHER", 5, 70.0):
                raise RuntimeError(f"Historical habit summary was not preserved: {habit_backfill}")
        engine.dispose()

        _alembic(env, "downgrade", PRE_STABILIZATION_HEAD)
        _alembic(env, "upgrade", "head")


def validate_contracts() -> None:
    if AcademicDeadline is not DeadlineItem:
        raise RuntimeError("Deadline compatibility alias is broken")
    if GradeRecord.grade_type.default.arg != "COMPONENT":
        raise RuntimeError("Grade classification default is not COMPONENT")

    required_owned = {
        "student_academic_profiles", "attendance_records", "grade_records", "deadline_items",
        "study_activity_logs", "digital_twin_snapshots", "student_notifications",
        "calendar_events", "study_blocks", "reminders", "student_goals",
        "student_preferences", "student_habits",
        "goal_milestones", "goal_progress", "habits", "habit_logs", "habit_streaks",
        "student_connectors", "sync_jobs", "sync_history",
    }
    for table_name in required_owned:
        table = Base.metadata.tables[table_name]
        if "student_id" not in table.c:
            raise RuntimeError(f"{table_name} has no canonical student_id")
        if table.c.student_id.nullable:
            raise RuntimeError(f"{table_name}.student_id must be non-null")

    if calculate_spi([], 1) is not None or calculate_cpi([]) is not None:
        raise RuntimeError("Empty grade collections must have null GPA results")

    paths = app.openapi()["paths"]
    reminder_ops = {method.upper() for path, methods in paths.items() if path.startswith("/api/reminders/") for method in methods}
    if not {"GET", "POST", "PATCH", "DELETE"}.issubset(reminder_ops):
        raise RuntimeError(f"Reminder CRUD routes incomplete: {reminder_ops}")
    if "/api/dashboard/{student_id}" not in paths:
        raise RuntimeError("Dashboard route missing")

    expected_agents = {
        "analytics", "study", "pyq", "retrieval", "memory", "semester", "learning",
        "academic_profile", "attendance", "deadline", "notification", "calendar", "scheduler", "reminder",
        "productivity",
        "semester_copilot",
    }
    actual_agents = set(create_default_registry().names())
    if actual_agents != expected_agents:
        raise RuntimeError(f"Agent registry mismatch: {actual_agents ^ expected_agents}")

    routes = {
        "attendance status": "attendance",
        "upcoming deadlines": "deadline",
        "calendar events": "calendar",
        "schedule study blocks": "scheduler",
        "academic profile": "academic_profile",
        "notifications": "notification",
    }
    for goal, agent in routes.items():
        if agent not in create_execution_plan(goal)["agents"]:
            raise RuntimeError(f"Director did not route {goal!r} to {agent}")


def run_tests() -> None:
    subprocess.run(
        [sys.executable, "-W", "ignore", "-m", "unittest", "discover", "-s", "tests", "-q"],
        cwd=BACKEND,
        check=True,
    )


def main() -> None:
    validate_migration_history()
    validate_contracts()
    run_tests()
    print("Migrations, ownership, grades, deadlines, dashboard, scheduler, reminders, agents, and routing verified")
    print("JARVIS STABILIZATION VALIDATION PASSED")


if __name__ == "__main__":
    main()
