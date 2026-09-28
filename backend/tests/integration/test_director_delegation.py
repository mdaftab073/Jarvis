import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.agents.agent_registry import AgentRegistry
from app.agents.base import BaseAgent
from app.agents.director_agent import AcademicDirectorAgent
from app.db.database import Base
from app.db.models import Course, Student, Subject


class RecordingAgent(BaseAgent):
    def __init__(self, name, shared):
        self.name = name
        self.shared = shared

    def execute(self, context):
        self.shared.append((self.name, context["goal"], context["student_id"], context["db"]))
        return self.response(
            f"{self.name} completed",
            [f"{self.name} action"],
            data={"agent_context_subject_id": context.get("subject_id")},
            risks=[{"risk": f"{self.name} risk", "severity": "LOW"}],
        )


class DirectorDelegationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.student = Student(name="Integration", email="director-integration@example.com")
        self.db.add(Subject(name="DBMS", course=Course(name="CS", student=self.student)))
        self.db.commit()
        self.db.refresh(self.student)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_director_passes_shared_context_to_ordered_specialists(self):
        shared = []
        names = ["analytics", "semester", "study", "pyq"]
        registry = AgentRegistry([RecordingAgent(name, shared) for name in names])
        strategy = {
            "summary": "Unified strategy",
            "priority_actions": [],
            "recommended_topics": [],
            "next_steps": [],
        }
        context = {
            "db": self.db,
            "student_id": self.student.id,
            "subject_id": 11,
            "goal": "DBMS exam in 10 days",
        }
        with patch("app.agents.director_agent.generate_agent_response", return_value=strategy):
            result = AcademicDirectorAgent(registry).run(context)

        self.assertEqual([item[0] for item in shared], names)
        self.assertTrue(all(item[1] == context["goal"] for item in shared))
        self.assertTrue(all(item[3] is self.db for item in shared))
        self.assertEqual(len(result["risks"]), 4)
        self.assertEqual(len(result["recommended_actions"]), 4)

    def test_director_continues_after_one_specialist_failure(self):
        shared = []

        class FailingAgent(RecordingAgent):
            def execute(self, context):
                raise RuntimeError("offline agent")

        agents = [
            FailingAgent("analytics", shared),
            RecordingAgent("semester", shared),
            RecordingAgent("study", shared),
            RecordingAgent("pyq", shared),
        ]
        with patch(
            "app.agents.director_agent.generate_agent_response",
            return_value={"summary": "Partial", "priority_actions": [], "next_steps": []},
        ):
            result = AcademicDirectorAgent(AgentRegistry(agents)).run(
                {"db": self.db, "student_id": self.student.id, "goal": "DBMS exam in 10 days"}
            )

        self.assertEqual(len(result["failures"]), 1)
        self.assertEqual(result["execution_order"], ["analytics", "semester", "study", "pyq"])


if __name__ == "__main__":
    unittest.main()