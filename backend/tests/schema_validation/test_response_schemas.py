import unittest
from datetime import date, datetime

from app.schemas.analytics import AnalyticsResponse
from app.schemas.director import AgentResponse
from app.schemas.profile import ProfileResponse
from app.schemas.semester import SemesterResponse
from app.schemas.study_plan import StudyPlanResponse


class ResponseSchemaTests(unittest.TestCase):
    def test_agent_response_serializes_standard_contract(self):
        response = AgentResponse(
            agent_name="analytics",
            summary="Readiness calculated.",
            recommendations=["Review Transactions"],
        )
        self.assertEqual(response.model_dump()["agent_name"], "analytics")

    def test_study_plan_response_serializes_nested_agenda(self):
        response = StudyPlanResponse(
            id=1,
            student_id=2,
            subject_id=3,
            subject_name="DBMS",
            exam_date=date(2026, 10, 10),
            start_date=date(2026, 9, 28),
            hours_per_day=2,
            created_at=datetime(2026, 9, 28),
            progress={"completion": 50, "tasks_done": 1, "tasks_remaining": 1},
            daily_agenda=[{
                "day_number": 1,
                "date": date(2026, 9, 28),
                "tasks": [{
                    "id": 1,
                    "day_number": 1,
                    "scheduled_date": date(2026, 9, 28),
                    "topic": "Transactions",
                    "priority": 1,
                    "estimated_hours": 1,
                    "status": "PENDING",
                }],
            }],
        )
        self.assertEqual(response.model_dump(mode="json")["daily_agenda"][0]["tasks"][0]["topic"], "Transactions")

    def test_analytics_dashboard_serializes(self):
        response = AnalyticsResponse(
            student_id=1,
            readiness_score=72,
            status="Good",
            plan_completion=50,
            weak_topics=[],
            strong_topics=[],
            recommendations=[],
            subjects=[],
            practice_score_trend=[],
        )
        self.assertEqual(response.model_dump()["readiness_score"], 72)

    def test_profile_response_serializes(self):
        response = ProfileResponse(
            student_id=1,
            preferred_subjects=["DBMS"],
            strengths=["SQL"],
            weaknesses=["Transactions"],
            study_habits=["Evenings"],
            readiness_trend=[61, 72],
        )
        self.assertEqual(response.model_dump()["readiness_trend"], [61, 72])

    def test_semester_response_serializes(self):
        response = SemesterResponse(
            id=1,
            student_id=2,
            semester_number=3,
            start_date=date(2026, 9, 1),
            end_date=date(2027, 1, 31),
            target_cgpa=8.5,
            status="ACTIVE",
            created_at=datetime(2026, 9, 1),
            subjects=[],
            milestones=[],
        )
        self.assertEqual(response.model_dump(mode="json")["status"], "ACTIVE")


if __name__ == "__main__":
    unittest.main()