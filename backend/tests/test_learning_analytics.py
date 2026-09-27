import unittest
from datetime import date, datetime, timedelta
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.database import Base
from app.db.models import (
    Course,
    ExamQuestion,
    PracticeQuestionAttempt,
    PracticeSession,
    Student,
    StudentTopicPerformance,
    StudyPlan,
    StudyTask,
    Subject,
)
from app.schemas.analytics import PracticeQuestion, PracticeStartResponse
from app.services import analytics_service, performance_service


class LearningAnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.student = Student(name="Analytics Student", email="analytics@example.com")
        self.course = Course(name="Computer Science", student=self.student)
        self.subject = Subject(name="DBMS", course=self.course)
        self.db.add(self.subject)
        self.db.commit()
        self.db.refresh(self.subject)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _add_topic_performance(self, topic, correct, incorrect, confidence):
        attempts = correct + incorrect
        row = StudentTopicPerformance(
            student_id=self.student.id,
            subject_id=self.subject.id,
            topic=topic,
            attempts=attempts,
            correct_answers=correct,
            incorrect_answers=incorrect,
            confidence_score=confidence,
            mastery_score=performance_service._calculate_mastery(
                attempts=attempts,
                correct_answers=correct,
                confidence_score=confidence,
                last_practiced_at=datetime(2026, 9, 27),
            ),
            last_practiced_at=datetime(2026, 9, 27),
        )
        self.db.add(row)
        self.db.commit()
        return row

    def test_mastery_uses_accuracy_confidence_evidence_and_recency(self):
        now = datetime(2026, 9, 27)
        recent = performance_service._calculate_mastery(
            attempts=5,
            correct_answers=4,
            confidence_score=80,
            last_practiced_at=now,
            now=now,
        )
        stale = performance_service._calculate_mastery(
            attempts=5,
            correct_answers=4,
            confidence_score=80,
            last_practiced_at=now - timedelta(days=180),
            now=now,
        )
        few_attempts = performance_service._calculate_mastery(
            attempts=1,
            correct_answers=1,
            confidence_score=80,
            last_practiced_at=now,
            now=now,
        )

        self.assertGreaterEqual(recent, stale)
        self.assertGreater(recent, few_attempts)
        self.assertLessEqual(recent, 100)

    def test_mastery_update_tracks_counts_and_weighted_confidence(self):
        first = performance_service.update_topic_mastery(
            self.db,
            self.student.id,
            self.subject.id,
            "Normalization",
            True,
            confidence_score=90,
        )
        first_score = first.mastery_score
        second = performance_service.update_topic_mastery(
            self.db,
            self.student.id,
            self.subject.id,
            "Normalization",
            False,
            confidence_score=30,
        )
        self.db.commit()

        self.assertEqual(second.attempts, 2)
        self.assertEqual(second.correct_answers, 1)
        self.assertEqual(second.incorrect_answers, 1)
        self.assertEqual(second.confidence_score, 60)
        self.assertGreater(first_score, second.mastery_score)

    def test_readiness_combines_mastery_plan_and_pyq_coverage(self):
        self._add_topic_performance("Normalization", 4, 1, 90)
        material = __import__("app.db.models", fromlist=["StudyMaterial"]).StudyMaterial(
            title="DBMS PYQ",
            file_path="dbms.pdf",
            subject_id=self.subject.id,
            material_type="PYQ",
        )
        self.db.add(material)
        self.db.commit()
        for topic in ("Normalization", "Transactions"):
            self.db.add(
                ExamQuestion(
                    subject_id=self.subject.id,
                    study_material_id=material.id,
                    question_text=f"Explain {topic}",
                    year=2024,
                    topic=topic,
                )
            )
        plan = StudyPlan(
            student_id=self.student.id,
            subject_id=self.subject.id,
            exam_date=date(2026, 12, 20),
            hours_per_day=2,
            created_at=datetime(2026, 9, 27),
        )
        plan.tasks = [
            StudyTask(
                day_number=1,
                topic="Normalization",
                priority=1,
                estimated_hours=1,
                status="COMPLETED",
            ),
            StudyTask(
                day_number=2,
                topic="Transactions",
                priority=2,
                estimated_hours=1,
                status="PENDING",
            ),
        ]
        self.db.add(plan)
        self.db.commit()

        readiness = performance_service.calculate_exam_readiness(
            self.db,
            self.student.id,
            self.subject.id,
        )

        self.assertEqual(readiness["plan_completion"], 50)
        self.assertEqual(readiness["pyq_coverage"], 50)
        self.assertGreater(readiness["readiness_score"], 60)
        self.assertEqual(readiness["status"], "Good")

    def test_weak_strong_topics_and_adaptive_recommendations(self):
        self._add_topic_performance("Transactions", 1, 4, 35)
        self._add_topic_performance("Normalization", 9, 1, 90)
        material = __import__("app.db.models", fromlist=["StudyMaterial"]).StudyMaterial(
            title="DBMS PYQ",
            file_path="dbms.pdf",
            subject_id=self.subject.id,
            material_type="PYQ",
        )
        self.db.add(material)
        self.db.commit()
        for topic in ["Transactions"] * 5 + ["Normalization"] * 3:
            self.db.add(
                ExamQuestion(
                    subject_id=self.subject.id,
                    study_material_id=material.id,
                    question_text=f"Explain {topic}",
                    year=2024,
                    topic=topic,
                )
            )
        plan = StudyPlan(
            student_id=self.student.id,
            subject_id=self.subject.id,
            exam_date=date(2026, 10, 3),
            hours_per_day=2,
            created_at=datetime(2026, 9, 27),
        )
        plan.tasks = [
            StudyTask(
                day_number=1,
                topic="Transactions",
                priority=1,
                estimated_hours=1,
                status="PENDING",
            )
        ]
        self.db.add(plan)
        self.db.commit()

        weak = performance_service.get_weak_topics(self.db, self.student.id, self.subject.id)
        strong = performance_service.get_strong_topics(self.db, self.student.id, self.subject.id)
        recommendations = performance_service.generate_personalized_recommendations(
            self.db,
            self.student.id,
            self.subject.id,
            today=date(2026, 9, 27),
        )

        self.assertEqual(weak[0]["topic"], "Transactions")
        self.assertEqual(strong[0]["topic"], "Normalization")
        self.assertTrue(any("Transactions" in item for item in recommendations))
        self.assertTrue(any("PYQ" in item for item in recommendations))
        self.assertTrue(any("task(s) remain" in item for item in recommendations))

    def test_practice_session_grades_answers_and_updates_mastery(self):
        generated_questions = {
            "questions": [
                {
                    "question": "Explain ACID.",
                    "expected_answer": "Atomicity, consistency, isolation, durability.",
                    "topic": "Transactions",
                    "difficulty": "Medium",
                    "marks": 4,
                },
                {
                    "question": "Explain BCNF.",
                    "expected_answer": "Every determinant is a candidate key.",
                    "topic": "Normalization",
                    "difficulty": "Hard",
                    "marks": 6,
                },
            ]
        }
        with patch.object(
            performance_service,
            "generate_practice_questions",
            return_value=generated_questions,
        ):
            created = performance_service.create_practice_session(
                self.db,
                self.student.id,
                self.subject.id,
                count=2,
            )

        attempts = created["attempts"]
        session_id = created["session"].id
        public_response = PracticeStartResponse(
            session_id=session_id,
            student_id=self.student.id,
            subject_id=self.subject.id,
            started_at=created["session"].started_at,
            total_questions=len(attempts),
            questions=[
                PracticeQuestion(
                    attempt_id=attempt.id,
                    question=attempt.question_text,
                    topic=attempt.topic,
                    difficulty=attempt.difficulty,
                )
                for attempt in attempts
            ],
        )
        self.assertNotIn(
            "Atomicity, consistency",
            public_response.model_dump_json(),
        )
        grades = {
            attempts[0].id: {
                "is_correct": True,
                "score": 95,
                "feedback": "Correct core points.",
            },
            attempts[1].id: {
                "is_correct": False,
                "score": 20,
                "feedback": "Include the candidate key condition.",
            },
        }
        with patch.object(performance_service, "_grade_attempts", return_value=grades):
            result = performance_service.complete_practice_session(
                self.db,
                session_id,
                [
                    {
                        "attempt_id": attempts[0].id,
                        "student_answer": "All four ACID properties",
                        "confidence_score": 80,
                    },
                    {
                        "attempt_id": attempts[1].id,
                        "student_answer": "A normal form condition",
                        "confidence_score": 40,
                    },
                ],
            )

        persisted = self.db.query(PracticeSession).filter_by(id=session_id).one()
        stored_attempts = (
            self.db.query(PracticeQuestionAttempt)
            .filter_by(practice_session_id=session_id)
            .all()
        )
        mastery = {
            item.topic: item
            for item in self.db.query(StudentTopicPerformance).all()
        }

        self.assertEqual(persisted.correct_answers, 1)
        self.assertEqual(persisted.score, 50)
        self.assertIsNotNone(persisted.completed_at)
        self.assertEqual(result["topic_coverage"], ["Normalization", "Transactions"])
        self.assertTrue(all(item.student_answer for item in stored_attempts))
        self.assertTrue(all(item.expected_answer for item in stored_attempts))
        self.assertEqual(mastery["Transactions"].correct_answers, 1)
        self.assertEqual(mastery["Normalization"].incorrect_answers, 1)

    def test_dashboard_returns_subject_mastery_and_practice_trend(self):
        self._add_topic_performance("Normalization", 4, 1, 80)
        session = PracticeSession(
            student_id=self.student.id,
            subject_id=self.subject.id,
            started_at=datetime(2026, 9, 27, 10),
            completed_at=datetime(2026, 9, 27, 10, 20),
            score=80,
            total_questions=5,
            correct_answers=4,
        )
        self.db.add(session)
        self.db.commit()

        dashboard = analytics_service.get_student_dashboard(self.db, self.student.id)

        self.assertEqual(dashboard["subjects"][0]["subject_name"], "DBMS")
        self.assertEqual(dashboard["subjects"][0]["topic_mastery"][0]["topic"], "Normalization")
        self.assertEqual(dashboard["practice_score_trend"][0]["score"], 80)


if __name__ == "__main__":
    unittest.main()
