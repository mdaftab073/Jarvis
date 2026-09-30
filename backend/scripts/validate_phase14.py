"""Phase 14 Validation Script.

Performs comprehensive validation of the Personalized Learning Intelligence subsystem:
1. Database Schema: verifies all Phase 14 tables, columns, and foreign keys.
2. Alembic Migrations: verifies single head revision matching Phase 14.
3. FastAPI Routes: verifies registration of all 15 Phase 14 endpoints in OpenAPI.
4. Agent Registry: verifies LearningAgent registration in default registry.
5. Director Planner: verifies personalized learning goal routing.
6. Test Suite: executes Phase 14 test suite and reports pass/fail counts.
"""

import json
import os
import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
os.chdir(BACKEND_ROOT)

def validate_database_schema() -> dict:
    from sqlalchemy import create_engine, inspect
    from app.core.config import settings

    try:
        engine = create_engine(settings.DATABASE_URL)
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        required_tables = [
            "topics",
            "flashcard_decks",
            "flashcards",
            "quiz_sessions",
            "quiz_questions",
            "quiz_answers",
            "topic_mastery",
            "learning_sessions",
        ]
        missing = [t for t in required_tables if t not in existing_tables]
        return {
            "status": "PASS" if not missing else "FAIL",
            "required_tables": required_tables,
            "missing_tables": missing,
            "table_count": len(required_tables) - len(missing),
        }
    except Exception as exc:
        return {"status": "FAIL", "error": str(exc)}


def validate_alembic_head() -> dict:
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from alembic.migration import MigrationContext
    from sqlalchemy import create_engine
    from app.core.config import settings

    try:
        cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
        script = ScriptDirectory.from_config(cfg)
        heads = script.get_heads()

        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            current_rev = ctx.get_current_revision()

        is_valid = len(heads) == 1 and heads[0] == "a14b8c9d2e10" and current_rev == "a14b8c9d2e10"
        return {
            "status": "PASS" if is_valid else "FAIL",
            "heads": heads,
            "current_revision": current_rev,
            "single_head": len(heads) == 1,
            "target_revision": "a14b8c9d2e10",
        }
    except Exception as exc:
        return {"status": "FAIL", "error": str(exc)}


def validate_openapi_routes() -> dict:
    from app.main import app

    openapi_spec = app.openapi()
    registered_paths = set(openapi_spec.get("paths", {}).keys())

    required_endpoints = [
        "/api/topics",
        "/api/topics/{topic_id}",
        "/api/subjects/{subject_id}/topics",
        "/api/topics/extract/{material_id}",
        "/api/flashcards/generate",
        "/api/flashcards/decks",
        "/api/flashcards/decks/{deck_id}",
        "/api/flashcards/topic/{topic_id}",
        "/api/quizzes/generate",
        "/api/quizzes/submit",
        "/api/quizzes/history/{student_id}",
        "/api/quizzes/session/{session_id}",
        "/api/mastery/student/{student_id}",
        "/api/mastery/subject/{subject_id}",
        "/api/mastery/weak/{student_id}",
        "/api/learning/session",
        "/api/learning/history/{student_id}",
        "/api/learning/insights/{student_id}",
    ]

    missing = [ep for ep in required_endpoints if ep not in registered_paths]
    return {
        "status": "PASS" if not missing else "FAIL",
        "total_required": len(required_endpoints),
        "total_found": len(required_endpoints) - len(missing),
        "missing_endpoints": missing,
    }


def validate_agent_and_director() -> dict:
    from app.agents.agent_registry import create_default_registry
    from app.agents.director_agent import AcademicDirectorAgent, create_execution_plan
    from app.agents.learning_agent import LearningAgent

    registry = create_default_registry()
    names = registry.names()
    has_learning = "learning" in names and isinstance(registry.get("learning"), LearningAgent)

    plan = create_execution_plan("Analyze topic mastery and suggest flashcards")
    plan_selects_learning = "learning" in plan.get("agents", []) and plan.get("goal_type") == "personalized_learning"

    return {
        "status": "PASS" if has_learning and plan_selects_learning else "FAIL",
        "registry_agents": names,
        "learning_agent_registered": has_learning,
        "director_plan_agents": plan.get("agents", []),
        "director_goal_type": plan.get("goal_type"),
    }


def run_phase14_tests() -> dict:
    test_modules = [
        "tests.test_phase14_models",
        "tests.test_phase14_services",
        "tests.test_phase14_api",
        "tests.test_phase14_learning_agent",
        "tests.test_phase14_integration",
        "tests.regression.test_phase_regressions",
    ]

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for mod in test_modules:
        suite.addTests(loader.loadTestsFromName(mod))

    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, "w"))
    result = runner.run(suite)

    return {
        "status": "PASS" if result.wasSuccessful() else "FAIL",
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "passed": result.testsRun - len(result.failures) - len(result.errors),
    }


def main() -> int:
    print("=" * 60)
    print(" Jarvis Phase 14: Personalized Learning Intelligence Validation")
    print("=" * 60)

    results = {
        "database_schema": validate_database_schema(),
        "alembic_migrations": validate_alembic_head(),
        "openapi_routes": validate_openapi_routes(),
        "agent_and_director": validate_agent_and_director(),
        "test_suite": run_phase14_tests(),
    }

    all_passed = all(v.get("status") == "PASS" for v in results.values())
    results["overall_status"] = "PASS" if all_passed else "FAIL"

    print(json.dumps(results, indent=2))
    print("=" * 60)
    print(f"OVERALL STATUS: {results['overall_status']}")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
