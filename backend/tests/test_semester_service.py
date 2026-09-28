import unittest
from datetime import date, datetime
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.database import Base
from app.db.models import (
    Course,
    Semester,
    SemesterMilestone,
    SemesterSubject,
    Student,
    StudyPlan,
    StudyTask,
    Subject,
)
from app.services import copilot_service, semester_service


class SemesterServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.student = Student(name="Semester Student", email="semester@example.com")
        self.subject = Subject(
            name="DBMS",
            course=Course(name="Computer Science", student=self.student),
        )
        self.db.add(self.subject)
        self.db.commit()
        self.db.refresh(self.subject)
        self.semester = Semester(
            student_id=self.student.id,
            semester_number=3,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            target_cgpa=8.5,
        )
        self.semester.subjects.append(
            SemesterSubject(
                subject=self.subject,
                target_score=85,
                current_readiness=0,
            )
        )
        self.db.add(self.semester)
        self.db.commit()
        self.db.refresh(self.semester)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_create_semester_with_subject_targets(self):
        created = semester_service.create_semester(
            self.db,
            student_id=self.student.id,
            semester_number=4,
            start_date=date(2026, 9, 1),
            end_date=date(2027, 1, 31),
            target_cgpa=9.0,
            subjects=[{"subject_id": self.subject.id, "target_score": 90}],
        )

        self.assertEqual(created["status"], "ACTIVE")
        self.assertEqual(created["target_cgpa"], 9.0)
        self.assertEqual(created["subjects"][0]["target_score"], 90)

    def test_duplicate_semester_subjects_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "only be enrolled once"):
            semester_service.create_semester(
                self.db,
                student_id=self.student.id,
                semester_number=4,
                start_date=date(2026, 9, 1),
                end_date=date(2027, 1, 31),
                subjects=[
                    {"subject_id": self.subject.id},
                    {"subject_id": self.subject.id},
                ],
            )

    def test_semester_health_uses_readiness_plans_milestones_and_weak_topics(self):
        self.db.add(
            StudyPlan(
                student_id=self.student.id,
                subject_id=self.subject.id,
                exam_date=date(2026, 12, 1),
                hours_per_day=2,
                created_at=datetime(2026, 9, 1),
                tasks=[
                    StudyTask(day_number=1, topic="A", priority=1, estimated_hours=1, status="COMPLETED"),
                    StudyTask(day_number=2, topic="B", priority=1, estimated_hours=1, status="PENDING"),
                ],
            )
        )
        self.semester.milestones = [
            SemesterMilestone(
                title="Midterm",
                due_date=date(2026, 9, 20),
                completed=True,
                completed_at=datetime(2026, 9, 20),
            ),
            SemesterMilestone(title="Assignment", due_date=date(2026, 10, 1)),
        ]
        self.db.commit()
        with (
            patch.object(
                semester_service,
                "calculate_exam_readiness",
                return_value={"readiness_score": 70},
            ),
            patch.object(
                semester_service,
                "get_weak_topics",
                return_value=[{"topic": "Transactions"}],
            ),
        ):
            health = semester_service.calculate_semester_health(
                self.db,
                self.semester.id,
                today=date(2026, 9, 28),
            )

        self.assertEqual(health["health_score"], 64)
        self.assertEqual(health["category"], "Stable")
        self.assertEqual(health["factors"]["weak_topic_count"], 1)
        self.assertEqual(health["factors"]["plan_completion"], 50)

    def test_risk_detection_reports_low_readiness_and_overdue_items(self):
        old_plan = StudyPlan(
            student_id=self.student.id,
            subject_id=self.subject.id,
            exam_date=date(2026, 12, 1),
            hours_per_day=2,
            created_at=datetime(2026, 9, 1),
            tasks=[
                StudyTask(day_number=1, topic="A", priority=1, estimated_hours=1, status="PENDING"),
                StudyTask(day_number=2, topic="B", priority=1, estimated_hours=1, status="PENDING"),
                StudyTask(day_number=3, topic="C", priority=1, estimated_hours=1, status="PENDING"),
            ],
        )
        self.db.add(old_plan)
        self.db.add(
            SemesterMilestone(
                semester_id=self.semester.id,
                title="Lab Exam",
                due_date=date(2026, 9, 10),
            )
        )
        self.db.commit()
        with (
            patch.object(
                semester_service,
                "calculate_exam_readiness",
                return_value={"readiness_score": 35},
            ),
            patch.object(
                semester_service,
                "get_weak_topics",
                return_value=[{"topic": "T1"}, {"topic": "T2"}, {"topic": "T3"}],
            ),
        ):
            risks = semester_service.detect_academic_risks(
                self.db,
                self.semester.id,
                today=date(2026, 9, 28),
            )

        self.assertTrue(any("critically low" in item["risk"] and item["severity"] == "HIGH" for item in risks))
        self.assertTrue(any("overdue study-plan" in item["risk"] for item in risks))
        self.assertTrue(any("Lab Exam" in item["risk"] and item["severity"] == "HIGH" for item in risks))

    def test_weekly_review_separates_recently_completed_and_due_milestones(self):
        self.db.add_all(
            [
                SemesterMilestone(
                    semester_id=self.semester.id,
                    title="Midterm",
                    due_date=date(2026, 10, 2),
                    completed=True,
                    completed_at=datetime(2026, 10, 7),
                ),
                SemesterMilestone(
                    semester_id=self.semester.id,
                    title="Assignment",
                    due_date=date(2026, 10, 12),
                ),
            ]
        )
        self.db.commit()
        with patch.object(semester_service, "_refresh_subject_metrics", return_value=[]):
            review = semester_service.generate_weekly_review(
                self.db,
                self.semester.id,
                today=date(2026, 10, 10),
            )

        self.assertEqual(review["completed_goals"][0]["title"], "Midterm")
        self.assertEqual(review["pending_goals"][0]["title"], "Assignment")
        self.assertTrue(review["recommended_actions"])

    def test_semester_goals_are_trackable_milestones(self):
        goal = semester_service.create_semester_goal(
            self.db,
            self.semester.id,
            "Achieve 8.5 CGPA",
            description="Maintain a semester GPA of at least 8.5",
        )
        completed = semester_service.update_milestone_completion(
            self.db,
            self.semester.id,
            goal["id"],
            True,
        )

        self.assertEqual(goal["due_date"], date(2026, 12, 31))
        self.assertTrue(completed["completed"])
        self.assertIsNotNone(completed["completed_at"])

    def test_copilot_guidance_prioritizes_subjects_and_risks(self):
        with (
            patch.object(copilot_service, "calculate_semester_health", return_value={
                "health_score": 72,
                "category": "Stable",
                "subjects": [
                    {
                        "subject_id": self.subject.id,
                        "subject_name": "DBMS",
                        "readiness": 55,
                        "plan_completion": 60,
                        "weak_topic_count": 2,
                    }
                ],
            }),
            patch.object(copilot_service, "detect_academic_risks", return_value=[
                {"risk": "DBMS needs work", "severity": "MEDIUM"}
            ]),
        ):
            guidance = copilot_service.generate_copilot_guidance(
                self.db,
                self.semester.id,
            )

        self.assertEqual(guidance["semester_health"], 72)
        self.assertEqual(guidance["priority_subjects"][0]["subject_name"], "DBMS")
        self.assertEqual(guidance["risks"][0]["severity"], "MEDIUM")
        self.assertTrue(guidance["next_actions"])


if __name__ == "__main__":
    unittest.main()