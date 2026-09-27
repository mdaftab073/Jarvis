import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.database import Base
from app.db.models import Course, ExamQuestion, StudyMaterial, Student, Subject
from app.services import pyq_service


class PYQIntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        student = Student(name="Student", email="pyq-test@example.com")
        course = Course(name="Computer Science", student=student)
        self.subject = Subject(name="DBMS", course=course)
        self.db.add(self.subject)
        self.db.commit()
        self.db.refresh(self.subject)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _add_material(self, year, text):
        material = StudyMaterial(
            title=f"DBMS PYQ {year}",
            file_path=f"paper-{year}.pdf",
            subject_id=self.subject.id,
            material_type="PYQ",
        )
        material.subject = self.subject
        self.db.add(material)
        self.db.commit()
        self.db.refresh(material)
        classifications = []
        for question in pyq_service.extract_questions(text):
            text_lower = question["question_text"].lower()
            if "bcnf" in text_lower or "normal" in text_lower:
                topic = "Normalization"
            elif "transaction" in text_lower or "acid" in text_lower:
                topic = "Transactions"
            else:
                topic = "Indexing"
            classifications.append(
                {
                    **question,
                    "topic": topic,
                    "unit": "Unit 1",
                    "marks": 8,
                }
            )
        with patch.object(
            pyq_service,
            "classify_questions",
            return_value=classifications,
        ):
            pyq_service.analyze_pyq_material(self.db, material, text)
        return material

    def test_extract_questions_keeps_subparts_with_parent(self):
        extracted = pyq_service.extract_questions(
            "Q1 Explain BCNF.\n(a) Give an example.\n(b) State a benefit.\n"
            "Q2 Explain ACID transactions."
        )

        self.assertEqual(len(extracted), 2)
        self.assertIn("(a) Give an example.", extracted[0]["question_text"])
        self.assertIn("(b) State a benefit.", extracted[0]["question_text"])
        self.assertEqual(extracted[1]["question_number"], 2)

    def test_three_year_analysis_produces_frequency_and_trends(self):
        self._add_material(2022, "Q1 Explain BCNF normalization.")
        self._add_material(2023, "Q1 Explain normalization.\nQ2 Explain ACID transactions.")
        self._add_material(2024, "Q1 Explain BCNF normalization.\nQ2 Explain B-tree indexing.")

        frequencies = pyq_service.get_topic_frequency(self.db, self.subject.id)
        trends = pyq_service.analyze_exam_trends(self.db, self.subject.id)
        important = pyq_service.generate_important_topics(self.db, self.subject.id)
        revision = pyq_service.create_revision_plan(self.db, self.subject.id)

        self.assertEqual(frequencies["Normalization"], 3)
        self.assertEqual(frequencies["Transactions"], 1)
        self.assertEqual(frequencies["Indexing"], 1)
        self.assertIn("Indexing", trends["new_topics"])
        self.assertEqual(trends["declining_topics"][0]["topic"], "Transactions")
        self.assertEqual(important[0]["topic"], "Normalization")
        self.assertIn("Normalization", [item["topic"] for item in revision["high_priority"]])
        self.assertEqual(trends["yearly_frequencies"][2024]["Normalization"], 1)

    def test_practice_generation_uses_context_and_validates_difficulty(self):
        note = StudyMaterial(
            title="DBMS Notes",
            file_path="notes.pdf",
            subject_id=self.subject.id,
            material_type="NOTES",
        )
        note.subject = self.subject
        self.db.add(note)
        self.db.commit()

        generated = [
            {
                "question": "Explain a transaction schedule.",
                "difficulty": "hard",
                "topic": "Transactions",
                "marks": 10,
            },
            {
                "question": "Define a relation.",
                "difficulty": "Unknown",
                "topic": "Relational model",
                "marks": 2,
            },
        ]
        response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=json.dumps(generated))
                )
            ]
        )
        with (
            patch.object(pyq_service, "extract_text_from_pdf", return_value="Database notes"),
            patch("app.services.rag_service.build_context", return_value=("RAG facts", [])),
            patch.object(pyq_service.client.chat.completions, "create", return_value=response) as llm_call,
        ):
            result = pyq_service.generate_practice_questions(
                self.db,
                self.subject.id,
                count=2,
            )

        self.assertEqual(len(result["questions"]), 2)
        self.assertEqual(result["questions"][0]["difficulty"], "Hard")
        self.assertEqual(result["questions"][1]["difficulty"], "Medium")
        self.assertIn("RAG facts", llm_call.call_args.kwargs["messages"][0]["content"])

    def test_material_type_and_question_persistence_fields(self):
        material = self._add_material(2024, "Q1 Explain BCNF.")
        question = (
            self.db.query(ExamQuestion)
            .filter(ExamQuestion.study_material_id == material.id)
            .one()
        )

        self.assertEqual(material.material_type, "PYQ")
        self.assertEqual(question.year, 2024)
        self.assertEqual(question.topic, "Normalization")
        self.assertEqual(question.marks, 8)


if __name__ == "__main__":
    unittest.main()
