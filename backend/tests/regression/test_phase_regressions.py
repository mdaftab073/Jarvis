import unittest

from app.agents.agent_registry import create_default_registry
from app.agents.director_agent import create_execution_plan
from app.main import app


class PhaseRegressionTests(unittest.TestCase):
    def test_existing_rag_and_learning_routes_remain_registered(self):
        paths = set(app.openapi()["paths"])
        expected = {
            "/api/rag/ask",
            "/api/rag/debug-search",
            "/api/pyq/trends/{subject_id}",
            "/api/study-plans/generate",
            "/api/analytics/readiness/{student_id}/{subject_id}",
            "/api/agent/academic",
            "/api/profile/{student_id}",
            "/api/semester/{semester_id}/copilot",
            "/api/director/academic",
            "/api/topics",
            "/api/flashcards/generate",
            "/api/quizzes/generate",
            "/api/mastery/student/{student_id}",
            "/api/learning/session",
        }
        self.assertTrue(expected <= paths)

    def test_director_default_registry_covers_all_specialist_domains(self):
        self.assertEqual(
            set(create_default_registry().names()),
            {
                "analytics", "study", "pyq", "retrieval", "memory", "semester", "learning",
                "academic_profile", "attendance", "deadline", "notification", "calendar",
                "scheduler", "reminder",
                "productivity",
                "semester_copilot",
            },
        )

    def test_exam_goal_delegation_order_is_stable(self):
        self.assertEqual(
            create_execution_plan("My DBMS exam is in 10 days.")["agents"],
            ["analytics", "semester", "study", "pyq"],
        )


if __name__ == "__main__":
    unittest.main()