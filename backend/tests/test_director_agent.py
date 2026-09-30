import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.agents.agent_registry import AgentRegistry, create_default_registry
from app.agents.analytics_agent import AnalyticsAgent
from app.agents.director_agent import (
    AcademicDirectorAgent,
    aggregate_agent_outputs,
    create_execution_plan,
)
from app.agents.memory_agent import MemoryAgent
from app.agents.pyq_agent import PYQAgent
from app.agents.retrieval_agent import RetrievalAgent
from app.agents.semester_agent import SemesterAgent
from app.agents.study_agent import StudyAgent
from app.agents.learning_agent import LearningAgent
from app.db.database import Base
from app.db.models import Course, Student, Subject


class StubAgent:
    def __init__(self, name, output=None, error=None, calls=None):
        self.name = name
        self.output = output or {
            "agent_name": name,
            "summary": f"{name} summary",
            "recommendations": [f"{name} recommendation"],
            "data": {},
            "risks": [],
        }
        self.error = error
        self.calls = calls if calls is not None else []

    def execute(self, context):
        self.calls.append(self.name)
        if self.error:
            raise self.error
        return self.output


class DirectorAgentTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.student = Student(name="Director Student", email="director@example.com")
        self.subject = Subject(
            name="DBMS",
            course=Course(name="Computer Science", student=self.student),
        )
        self.db.add(self.subject)
        self.db.commit()
        self.db.refresh(self.subject)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_exam_goal_selects_expected_agents_in_order(self):
        plan = create_execution_plan("My DBMS exam is in 10 days.")

        self.assertEqual(plan["goal_type"], "exam_preparation")
        self.assertEqual(plan["agents"], ["analytics", "semester", "study", "pyq"])

    def test_planner_adds_specialists_for_goal_types(self):
        self.assertIn("retrieval", create_execution_plan("Explain this in my notes") ["agents"])
        self.assertIn("pyq", create_execution_plan("Make me a practice quiz")["agents"])
        self.assertIn("memory", create_execution_plan("Show my academic history")["agents"])
        self.assertIn("semester", create_execution_plan("What are my semester risks?")["agents"])

    def test_general_readiness_goal_uses_analytics_and_memory(self):
        self.assertEqual(
            create_execution_plan("How ready am I for DBMS?")["agents"],
            ["analytics", "memory"],
        )

    def test_default_registry_registers_and_resolves_every_agent(self):
        registry = create_default_registry()

        self.assertEqual(
            registry.names(),
            ["analytics", "study", "pyq", "retrieval", "memory", "semester", "learning"],
        )
        self.assertIsInstance(registry.get("analytics"), AnalyticsAgent)
        self.assertIsInstance(registry.get("learning"), LearningAgent)
        with self.assertRaisesRegex(KeyError, "not registered"):
            registry.get("unknown")

    def test_analytics_agent_uses_existing_performance_services(self):
        with (
            patch("app.agents.analytics_agent.calculate_exam_readiness", return_value={"readiness_score": 75}),
            patch("app.agents.analytics_agent.get_weak_topics", return_value=[{"topic": "Transactions"}]),
            patch("app.agents.analytics_agent.get_strong_topics", return_value=[{"topic": "Normalization"}]),
            patch("app.agents.analytics_agent.generate_personalized_recommendations", return_value=["Review Transactions"]),
        ):
            result = AnalyticsAgent().execute(
                {"db": self.db, "student_id": self.student.id, "goal": "DBMS readiness"}
            )

        self.assertEqual(result["agent_name"], "analytics")
        self.assertEqual(result["data"]["subjects"][0]["readiness"]["readiness_score"], 75)

    def test_study_agent_produces_balanced_workload_and_contract(self):
        with patch(
            "app.agents.study_agent.rank_topics_for_study",
            return_value=[{"topic": "Normalization", "priority": 1}],
        ):
            result = StudyAgent().execute(
                {"db": self.db, "student_id": self.student.id, "goal": "DBMS revision"}
            )

        self.assertEqual(result["agent_name"], "study")
        self.assertEqual(result["data"]["workloads"][0]["ranked_topics"][0]["topic"], "Normalization")
        self.assertTrue(result["recommendations"])

    def test_study_agent_defaults_missing_hours_for_deadline_plan(self):
        generated_plan = type("Plan", (), {"id": 17})()
        with (
            patch(
                "app.agents.study_agent.rank_topics_for_study",
                return_value=[{"topic": "Transactions", "priority": 1}],
            ),
            patch("app.agents.study_agent.generate_study_plan", return_value=generated_plan) as generate,
            patch("app.agents.study_agent.get_study_plan", return_value={"id": 17}),
        ):
            StudyAgent().execute(
                {
                    "db": self.db,
                    "student_id": self.student.id,
                    "goal": "DBMS exam in 10 days",
                    "hours_per_day": None,
                }
            )

        self.assertEqual(generate.call_args.kwargs["hours_per_day"], 2.0)

    def test_pyq_agent_returns_frequency_and_revision_priorities(self):
        with (
            patch("app.agents.pyq_agent.analyze_exam_trends", return_value={"most_repeated_topics": []}),
            patch("app.agents.pyq_agent.generate_important_topics", return_value=[{"topic": "Normalization", "score": 90}]),
            patch("app.agents.pyq_agent.get_topic_frequency", return_value={"Normalization": 3}),
        ):
            result = PYQAgent().execute(
                {"db": self.db, "student_id": self.student.id, "goal": "DBMS exam"}
            )

        self.assertEqual(result["agent_name"], "pyq")
        self.assertEqual(result["data"]["subjects"][0]["topic_frequency"]["Normalization"], 3)
        self.assertTrue(result["recommendations"])

    def test_retrieval_agent_delegates_question_to_rag_service(self):
        rag_result = {
            "answer": "A transaction is a unit of work.",
            "results": [{"metadata": {"material_id": 5, "title": "DBMS notes"}}],
            "stats": {"subject_detected": "DBMS"},
        }
        with patch("app.agents.retrieval_agent.ask_question", return_value=rag_result) as ask:
            result = RetrievalAgent().execute(
                {"db": self.db, "goal": "Explain transactions", "subject_id": self.subject.id}
            )

        ask.assert_called_once_with(
            question="Explain transactions",
            db=self.db,
            subject_id=self.subject.id,
        )
        self.assertEqual(result["data"]["sources"][0]["material_id"], 5)

    def test_memory_agent_returns_profile_memories_and_trend(self):
        with (
            patch("app.agents.memory_agent.build_student_profile", return_value={"strengths": ["SQL"], "weaknesses": ["Transactions"]}),
            patch("app.agents.memory_agent.get_memories", return_value=[{"memory_key": "SQL"}]),
            patch("app.agents.memory_agent.get_readiness_trend", return_value={"history": [60, 70]}),
            patch("app.agents.memory_agent.generate_profile_summary", return_value={"summary": "Improving."}),
        ):
            result = MemoryAgent().execute({"db": self.db, "student_id": self.student.id})

        self.assertEqual(result["agent_name"], "memory")
        self.assertEqual(result["data"]["readiness_trend"]["history"], [60, 70])

    def test_semester_agent_exposes_guidance_and_risks(self):
        guidance = [{"semester_health": 70, "next_actions": ["Finish assignment"], "risks": [{"risk": "Low readiness", "severity": "MEDIUM"}]}]
        with patch("app.agents.semester_agent.get_active_semester_guidance", return_value=guidance):
            result = SemesterAgent().execute({"db": self.db, "student_id": self.student.id})

        self.assertEqual(result["agent_name"], "semester")
        self.assertEqual(result["risks"][0]["severity"], "MEDIUM")
        self.assertIn("Finish assignment", result["recommendations"])

    def test_aggregation_combines_readiness_plans_recommendations_and_risks(self):
        outputs = [
            {
                "agent_name": "analytics",
                "summary": "Readiness 55%",
                "recommendations": ["Review Transactions"],
                "risks": [],
                "data": {
                    "subjects": [{
                        "subject_id": self.subject.id,
                        "subject_name": "DBMS",
                        "readiness": {"readiness_score": 55},
                        "weak_topics": [{"topic": "Transactions"}],
                        "strong_topics": [],
                    }]
                },
            },
            {
                "agent_name": "semester",
                "summary": "At risk",
                "recommendations": ["Complete midterm"],
                "risks": [{"risk": "Milestone overdue", "severity": "HIGH"}],
                "data": {"semesters": []},
            },
            {
                "agent_name": "study",
                "summary": "Plan ready",
                "recommendations": ["Review Transactions"],
                "risks": [],
                "data": {"plans": [{"id": 2}]},
            },
            {
                "agent_name": "pyq",
                "summary": "PYQ ranked",
                "recommendations": [],
                "risks": [],
                "data": {"subjects": [{"important_topics": [{"topic": "BCNF"}]}]},
            },
        ]

        aggregate = aggregate_agent_outputs(outputs)

        self.assertEqual(aggregate["readiness"][0]["readiness_score"], 55)
        self.assertEqual(aggregate["weak_topics"][0]["topic"], "Transactions")
        self.assertEqual(aggregate["plans"], [{"id": 2}])
        self.assertEqual(aggregate["revision_priorities"], ["BCNF"])
        self.assertEqual(aggregate["recommendations"], ["Review Transactions", "Complete midterm"])
        self.assertEqual(aggregate["risks"][0]["severity"], "HIGH")

    def test_director_executes_in_order_and_returns_standard_strategy(self):
        calls = []
        registry = AgentRegistry(
            [StubAgent(name, calls=calls) for name in ("analytics", "semester", "study", "pyq")]
        )
        director = AcademicDirectorAgent(registry)
        strategy = {
            "summary": "DBMS plan is ready.",
            "priority_actions": ["Review Transactions"],
            "recommended_topics": ["Transactions"],
            "next_steps": ["Take a practice test"],
        }
        with patch("app.agents.director_agent.generate_agent_response", return_value=strategy):
            result = director.run(
                {"db": self.db, "student_id": self.student.id, "goal": "DBMS exam in 10 days"}
            )

        self.assertEqual(calls, ["analytics", "semester", "study", "pyq"])
        self.assertEqual(result["execution_order"], calls)
        self.assertEqual(result["summary"], "DBMS plan is ready.")
        self.assertEqual(result["failures"], [])

    def test_director_delegates_notes_questions_to_retrieval_agent(self):
        calls = []
        registry = AgentRegistry([StubAgent("retrieval", calls=calls)])
        strategy = {
            "summary": "Answer grounded in DBMS notes.",
            "priority_actions": [],
            "recommended_topics": [],
            "next_steps": [],
        }
        with patch("app.agents.director_agent.generate_agent_response", return_value=strategy):
            result = AcademicDirectorAgent(registry).run(
                {
                    "db": self.db,
                    "student_id": self.student.id,
                    "goal": "Explain the DBMS notes on transactions",
                }
            )

        self.assertEqual(result["selected_agents"], ["retrieval"])
        self.assertEqual(calls, ["retrieval"])

    def test_director_fallback_formats_aggregated_readiness(self):
        analytics_output = {
            "agent_name": "analytics",
            "summary": "DBMS readiness 65%",
            "recommendations": [],
            "risks": [],
            "data": {
                "subjects": [{
                    "subject_id": self.subject.id,
                    "subject_name": "DBMS",
                    "readiness": {"readiness_score": 65, "status": "Good"},
                    "weak_topics": [],
                    "strong_topics": [],
                }]
            },
        }
        registry = AgentRegistry(
            [
                StubAgent("analytics", output=analytics_output),
                StubAgent("memory"),
            ]
        )
        captured = {}

        def generate_from_context(goal, context):
            captured.update(context)
            return __import__(
                "app.services.academic_agent_service",
                fromlist=["_fallback_agent_response"],
            )._fallback_agent_response(goal, context)

        with patch("app.agents.director_agent.generate_agent_response", side_effect=generate_from_context):
            result = AcademicDirectorAgent(registry).run(
                {"db": self.db, "student_id": self.student.id, "goal": "How ready am I for DBMS?"}
            )

        self.assertEqual(captured["readiness"][0], {"subject": "DBMS", "score": 65})
        self.assertIn("65%", result["summary"])

    def test_director_isolates_agent_failure_and_reports_failure(self):
        registry = AgentRegistry(
            [
                StubAgent("analytics", error=RuntimeError("analytics unavailable")),
                StubAgent("semester"),
                StubAgent("study"),
                StubAgent("pyq"),
            ]
        )
        with patch(
            "app.agents.director_agent.generate_agent_response",
            return_value={"summary": "Partial strategy", "priority_actions": [], "next_steps": []},
        ):
            result = AcademicDirectorAgent(registry).run(
                {"db": self.db, "student_id": self.student.id, "goal": "DBMS exam in 10 days"}
            )

        self.assertEqual(result["failures"][0]["agent_name"], "analytics")
        self.assertEqual(len(result["agent_outputs"]), 4)


if __name__ == "__main__":
    unittest.main()