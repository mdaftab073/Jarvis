import unittest
from datetime import date, timedelta
from io import BytesIO
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.agents.director_agent import AcademicDirectorAgent
from app.agents.pyq_agent import PYQAgent
from app.agents.retrieval_agent import RetrievalAgent
from app.api.routes.study_materials import embed_material, upload_material
from app.core.material_types import MaterialType
from app.db.database import Base
from app.db.models import Course, Student, StudentTopicPerformance, Subject
from app.services.memory_service import build_student_profile, get_memories
from app.services.performance_service import calculate_exam_readiness
from app.services.study_plan_service import complete_study_task, generate_study_plan
from starlette.datastructures import UploadFile


class AcademicWorkflowE2ETests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.student = Student(name="E2E Student", email="e2e@example.com")
        self.subject = Subject(name="DBMS", course=Course(name="CS", student=self.student))
        self.db.add(self.subject)
        self.db.commit()
        self.db.refresh(self.subject)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_notes_embedding_then_rag_answer(self):
        upload = UploadFile(filename="notes.pdf", file=BytesIO(b"mock PDF upload"))
        with patch("app.api.routes.study_materials.save_uploaded_file", return_value="uploads/notes.pdf"):
            material = upload_material(
                title="DBMS Notes",
                subject_id=self.subject.id,
                material_type=MaterialType.NOTES,
                file=upload,
                db=self.db,
            )
        with (
            patch("app.api.routes.study_materials.extract_text_from_pdf", return_value="ACID transactions ensure reliable database operations."),
            patch("app.api.routes.study_materials.vector_service.delete_material_chunks"),
            patch("app.api.routes.study_materials.delete_keyword_chunks"),
            patch("app.api.routes.study_materials.vector_service.add_chunks_to_vector_db", return_value=1) as embeddings,
            patch("app.api.routes.study_materials.replace_material_chunks"),
        ):
            embedded = embed_material(material.id, self.db)

        self.assertEqual(embedded.chunks_stored, 1)
        self.assertEqual(material.embedding_status, "embedded")
        embeddings.assert_called_once()
        with patch(
            "app.agents.retrieval_agent.ask_question",
            return_value={
                "answer": "ACID properties support reliable transactions.",
                "results": [{"metadata": {"material_id": material.id, "title": material.title}}],
                "stats": {"subject_detected": "DBMS"},
            },
        ):
            answer = RetrievalAgent().execute(
                {"db": self.db, "goal": "Explain ACID", "subject_id": self.subject.id}
            )
        self.assertIn("ACID", answer["summary"])

    def test_pyq_embedding_then_topics_and_revision_recommendations(self):
        upload = UploadFile(filename="pyq.pdf", file=BytesIO(b"mock PYQ upload"))
        with patch("app.api.routes.study_materials.save_uploaded_file", return_value="uploads/pyq.pdf"):
            material = upload_material(
                title="DBMS PYQ",
                subject_id=self.subject.id,
                material_type=MaterialType.PYQ,
                file=upload,
                db=self.db,
            )
        with (
            patch("app.api.routes.study_materials.extract_text_from_pdf", return_value="Q1 Explain BCNF normalization."),
            patch("app.api.routes.study_materials.vector_service.delete_material_chunks"),
            patch("app.api.routes.study_materials.delete_keyword_chunks"),
            patch("app.api.routes.study_materials.vector_service.add_chunks_to_vector_db", return_value=1),
            patch("app.api.routes.study_materials.replace_material_chunks"),
            patch("app.api.routes.study_materials.analyze_pyq_material", return_value=[{"topic": "Normalization"}]),
        ):
            embedded = embed_material(material.id, self.db)
        self.assertEqual(embedded.questions_extracted, 1)

        with (
            patch("app.agents.pyq_agent.analyze_exam_trends", return_value={"most_repeated_topics": [{"topic": "Normalization", "frequency": 4}]}),
            patch("app.agents.pyq_agent.generate_important_topics", return_value=[{"topic": "Normalization", "score": 90}]),
            patch("app.agents.pyq_agent.get_topic_frequency", return_value={"Normalization": 4}),
        ):
            result = PYQAgent().execute(
                {"db": self.db, "student_id": self.student.id, "goal": "DBMS exam"}
            )
        self.assertTrue(any("Normalization" in item for item in result["recommendations"]))

    def test_study_plan_tasks_completed_and_progress_updates(self):
        today = date.today()
        plan = generate_study_plan(
            self.db,
            self.student.id,
            self.subject.id,
            exam_date=today + timedelta(days=4),
            hours_per_day=2,
            today=today,
        )
        self.assertTrue(plan.tasks)
        for task in list(plan.tasks):
            complete_study_task(self.db, task.id)
        self.assertTrue(all(task.status == "COMPLETED" for task in plan.tasks))

    def test_readiness_calculation_updates_memory_and_profile(self):
        self.db.add(
            StudentTopicPerformance(
                student_id=self.student.id,
                subject_id=self.subject.id,
                topic="Transactions",
                attempts=4,
                correct_answers=1,
                incorrect_answers=3,
                confidence_score=30,
                mastery_score=35,
            )
        )
        self.db.commit()
        calculate_exam_readiness(self.db, self.student.id, self.subject.id)
        profile = build_student_profile(self.student.id, db=self.db)

        self.assertTrue(profile["readiness_trend"])
        self.assertTrue(
            any(
                memory["memory_type"] == "READINESS"
                for memory in get_memories(self.student.id, db=self.db)
            )
        )

    def test_director_exam_strategy_executes_specialists_without_failures(self):
        with patch(
            "app.agents.director_agent.generate_agent_response",
            return_value={
                "summary": "DBMS strategy built.",
                "priority_actions": ["Review Transactions"],
                "recommended_topics": ["Normalization"],
                "next_steps": ["Take a mock test"],
            },
        ):
            result = AcademicDirectorAgent().run(
                {
                    "db": self.db,
                    "student_id": self.student.id,
                    "goal": "My DBMS exam is in 10 days",
                }
            )

        self.assertEqual(result["selected_agents"], ["analytics", "semester", "study", "pyq"])
        self.assertEqual(result["failures"], [])
        self.assertEqual(result["summary"], "DBMS strategy built.")
        self.assertTrue(result["study_strategy"])


if __name__ == "__main__":
    unittest.main()