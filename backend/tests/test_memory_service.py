import unittest
from datetime import date, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.database import Base
from app.db.models import Course, Student, StudentTopicPerformance, Subject
from app.services import memory_service
from app.services.performance_service import (
    calculate_exam_readiness,
    get_strong_topics,
    get_weak_topics,
)
from app.services.study_plan_service import complete_study_task, generate_study_plan


class StudentMemoryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.student = Student(name="Memory Student", email="memory@example.com")
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

    def test_memory_crud_upserts_by_type_and_key(self):
        first = memory_service.store_memory(
            self.student.id,
            "WEAKNESS",
            "Transactions",
            {"mastery": 35},
            db=self.db,
        )
        second = memory_service.store_memory(
            self.student.id,
            "weakness",
            "Transactions",
            {"mastery": 42},
            db=self.db,
        )

        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(memory_service.get_memories(self.student.id, db=self.db)), 1)
        self.assertEqual(second["memory_value"]["mastery"], 42)
        updated = memory_service.update_memory(
            self.student.id,
            second["id"],
            {"mastery": 48},
            db=self.db,
        )
        self.assertEqual(updated["memory_value"]["mastery"], 48)
        self.assertTrue(memory_service.delete_memory(self.student.id, second["id"], db=self.db))
        self.assertEqual(memory_service.get_memories(self.student.id, db=self.db), [])

    def test_readiness_snapshots_and_profile_trend(self):
        for score in (61, 66, 72, 81):
            memory_service.record_readiness_snapshot(
                self.student.id,
                self.subject.id,
                score,
                db=self.db,
            )
        memory_service.store_memory(
            self.student.id,
            "STRENGTH",
            "Normalization",
            {"subject_id": self.subject.id},
            db=self.db,
        )
        memory_service.store_memory(
            self.student.id,
            "WEAKNESS",
            "Transactions",
            {"subject_id": self.subject.id},
            db=self.db,
        )
        memory_service.store_memory(
            self.student.id,
            "HABIT",
            "study_time",
            "Evenings",
            db=self.db,
        )

        profile = memory_service.build_student_profile(self.student.id, db=self.db)
        summary = memory_service.generate_profile_summary(self.student.id, db=self.db)

        self.assertEqual(profile["readiness_trend"], [61, 66, 72, 81])
        self.assertEqual(profile["strengths"], ["Normalization"])
        self.assertEqual(profile["weaknesses"], ["Transactions"])
        self.assertEqual(profile["study_habits"], ["study_time: Evenings"])
        self.assertIn("Strong in Normalization", summary["summary"])
        self.assertIn("Needs improvement in Transactions", summary["summary"])

    def test_performance_reads_automatically_capture_topics_and_readiness(self):
        self.db.add_all(
            [
                StudentTopicPerformance(
                    student_id=self.student.id,
                    subject_id=self.subject.id,
                    topic="Transactions",
                    attempts=5,
                    correct_answers=1,
                    incorrect_answers=4,
                    confidence_score=30,
                    mastery_score=35,
                ),
                StudentTopicPerformance(
                    student_id=self.student.id,
                    subject_id=self.subject.id,
                    topic="Normalization",
                    attempts=5,
                    correct_answers=5,
                    incorrect_answers=0,
                    confidence_score=95,
                    mastery_score=90,
                ),
            ]
        )
        self.db.commit()

        weak = get_weak_topics(self.db, self.student.id, self.subject.id)
        strong = get_strong_topics(self.db, self.student.id, self.subject.id)
        readiness = calculate_exam_readiness(self.db, self.student.id, self.subject.id)
        memories = memory_service.get_memories(self.student.id, db=self.db)

        self.assertEqual(weak[0]["topic"], "Transactions")
        self.assertEqual(strong[0]["topic"], "Normalization")
        self.assertTrue(any(item["memory_type"] == "WEAKNESS" for item in memories))
        self.assertTrue(any(item["memory_type"] == "STRENGTH" for item in memories))
        self.assertEqual(
            memory_service.get_readiness_trend(self.student.id, db=self.db)["history"],
            [readiness["readiness_score"]],
        )

    def test_plan_creation_and_completion_record_study_habits(self):
        today = date(2026, 9, 28)
        plan = generate_study_plan(
            self.db,
            self.student.id,
            self.subject.id,
            exam_date=today + timedelta(days=4),
            hours_per_day=2,
            today=today,
        )
        profile = memory_service.build_student_profile(self.student.id, db=self.db)
        self.assertEqual(profile["preferred_study_hours"], 2)
        self.assertTrue(any("planned_study_hours" in habit for habit in profile["study_habits"]))

        task_ids = [task.id for task in plan.tasks]
        for task_id in task_ids:
            complete_study_task(self.db, task_id)
        memories = memory_service.get_memories(
            self.student.id,
            memory_type="HABIT",
            db=self.db,
        )
        self.assertTrue(
            any(item["memory_key"] == f"completed_study_plan:{plan.id}" for item in memories)
        )


if __name__ == "__main__":
    unittest.main()