import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.database import Base
from app.db.models import Course, Student, Subject
from app.services import academic_agent_service as agent


class AcademicAgentTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.student = Student(name="Agent Student", email="agent@example.com")
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

    def test_goal_classification_and_planning(self):
        self.assertEqual(agent.classify_goal("DBMS exam in 10 days"), "exam_preparation")
        self.assertEqual(agent.classify_goal("What should I revise this week?"), "revision_planning")
        self.assertEqual(agent.classify_goal("Help me improve my weak areas"), "weak_topic_recovery")
        self.assertEqual(agent.classify_goal("Generate a practice quiz"), "practice_preparation")
        self.assertEqual(agent.classify_goal("How ready am I for DBMS?"), "general_guidance")
        self.assertEqual(
            agent.plan_goal_execution("DBMS exam in 10 days")["actions"],
            ["readiness", "weak_topics", "study_plan", "pyq_topics", "recommendations"],
        )

    def test_execute_action_calls_existing_readiness_service(self):
        with patch.object(
            agent,
            "calculate_exam_readiness",
            return_value={"readiness_score": 68, "status": "Good"},
        ) as readiness:
            result = agent.execute_action(
                self.db,
                self.student.id,
                "readiness",
                subject_id=self.subject.id,
            )

        readiness.assert_called_once_with(self.db, self.student.id, self.subject.id)
        self.assertEqual(result[0]["result"]["readiness_score"], 68)

    def test_context_aggregation_collects_agent_signals(self):
        context = agent.build_agent_context(
            {
                "readiness": [{
                    "subject_name": "DBMS",
                    "result": {"readiness_score": 68, "status": "Good", "plan_completion": 30, "pyq_coverage": 50},
                }],
                "weak_topics": [{
                    "subject_name": "DBMS",
                    "result": [{"topic": "Transactions", "mastery": 35}],
                }],
                "pyq_topics": [{
                    "subject_name": "DBMS",
                    "result": {"trends": {"most_repeated_topics": []}, "important_topics": []},
                }],
            }
        )

        self.assertEqual(context["readiness"][0]["score"], 68)
        self.assertEqual(context["weak_topics"][0]["topic"], "Transactions")
        self.assertEqual(context["pyq_trends"][0]["subject"], "DBMS")

    def test_response_generation_parses_groq_json(self):
        payload = {
            "summary": "Readiness is 68%.",
            "priority_actions": ["Review Transactions"],
            "recommended_topics": ["Transactions"],
            "next_steps": ["Take a mock test"],
        }
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
        )
        context = agent.build_agent_context({})
        with patch.object(
            agent.llm_service.client.chat.completions,
            "create",
            return_value=response,
        ) as llm_call:
            result = agent.generate_agent_response("DBMS exam", context)

        self.assertEqual(result, payload)
        self.assertIn("Academic context", llm_call.call_args.kwargs["messages"][0]["content"])

    def test_run_orchestrates_planned_actions_and_reports_debug(self):
        with (
            patch.object(agent, "execute_action", return_value=[] ) as execute,
            patch.object(agent, "generate_agent_response", return_value={
                "summary": "Ready strategy",
                "priority_actions": [],
                "recommended_topics": [],
                "next_steps": [],
            }),
        ):
            result = agent.run_academic_agent(
                self.student.id,
                "DBMS exam in 10 days",
                db=self.db,
                include_debug=True,
            )

        self.assertEqual(execute.call_count, 5)
        self.assertEqual(result["goal_type"], "exam_preparation")
        self.assertEqual(result["executed_actions"], result["planned_actions"])


if __name__ == "__main__":
    unittest.main()