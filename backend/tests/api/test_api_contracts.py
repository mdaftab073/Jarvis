import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.routes import director as director_route
from app.db.database import Base, get_db
from app.db.models import Course, Student, Subject
from app.main import app


class APIContractTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.student = Student(name="API Student", email="api@example.com")
        self.subject = Subject(name="DBMS", course=Course(name="CS", student=self.student))
        self.db.add(self.subject)
        self.db.commit()
        self.db.refresh(self.subject)

        def override_get_db():
            yield self.db

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_director_academic_success_and_response_contract(self):
        director_result = {
            "agent_name": "director",
            "summary": "DBMS strategy ready.",
            "recommendations": ["Review transactions"],
            "data": {"selected_agents": ["analytics", "study"]},
            "risks": [],
        }
        with patch.object(director_route.director, "execute", return_value=director_result):
            response = self.client.post(
                "/api/director/academic",
                json={"student_id": self.student.id, "goal": "DBMS exam in 10 days"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["agent_name"], "director")
        self.assertEqual(response.json()["data"]["recommendations"], ["Review transactions"])

    def test_director_request_validation_returns_422(self):
        response = self.client.post(
            "/api/director/academic",
            json={"student_id": self.student.id, "goal": ""},
        )

        self.assertEqual(response.status_code, 422)

    def test_director_debug_includes_plan_and_execution(self):
        director_result = {
            "agent_name": "director",
            "summary": "Plan complete.",
            "recommendations": [],
            "data": {
                "selected_agents": ["analytics", "semester", "study", "pyq"],
                "execution_order": ["analytics", "semester", "study", "pyq"],
                "failures": [],
            },
            "risks": [],
        }
        with patch.object(director_route.director, "execute", return_value=director_result):
            response = self.client.get(
                "/api/director/debug-plan",
                params={"student_id": self.student.id, "goal": "DBMS exam in 10 days"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["goal_type"], "exam_preparation")
        self.assertEqual(response.json()["data"]["execution_order"][0], "analytics")

    def test_semester_creation_returns_201_and_invalid_student_404(self):
        payload = {
            "student_id": self.student.id,
            "semester_number": 1,
            "start_date": "2026-09-01",
            "end_date": "2027-01-31",
            "target_cgpa": 8.5,
            "subjects": [{"subject_id": self.subject.id, "target_score": 85}],
        }
        created = self.client.post("/api/semester", json=payload)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["data"]["subjects"][0]["subject_name"], "DBMS")

        payload["student_id"] = 9999
        missing = self.client.post("/api/semester", json=payload)
        self.assertEqual(missing.status_code, 404)

    def test_semester_date_and_milestone_validation_returns_422(self):
        invalid_semester = self.client.post(
            "/api/semester",
            json={
                "student_id": self.student.id,
                "semester_number": 1,
                "start_date": "2027-02-01",
                "end_date": "2027-01-01",
            },
        )
        self.assertEqual(invalid_semester.status_code, 422)

        semester = self.client.post(
            "/api/semester",
            json={
                "student_id": self.student.id,
                "semester_number": 1,
                "start_date": "2026-09-01",
                "end_date": "2027-01-31",
            },
        ).json()["data"]
        invalid_milestone = self.client.post(
            f"/api/semester/{semester['id']}/milestone",
            json={"title": "Midterm", "due_date": "2027-02-01"},
        )
        self.assertEqual(invalid_milestone.status_code, 422)

    def test_missing_semester_returns_404(self):
        response = self.client.get("/api/semester/9999")

        self.assertEqual(response.status_code, 404)

    def test_system_health_endpoint_returns_dependency_status(self):
        health = {
            "database": "healthy",
            "chroma": "healthy",
            "groq": "configured",
            "migrations": "up_to_date",
            "overall": "healthy",
        }
        with patch("app.api.routes.system.get_system_health", return_value=health):
            response = self.client.get("/system/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"success": True, "data": health})


if __name__ == "__main__":
    unittest.main()