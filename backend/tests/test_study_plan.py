import unittest
from datetime import date, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.material_types import MaterialType
from app.core.study_plan_types import StudyTaskStatus
from app.db.database import Base
from app.db.models import (
    Course,
    ExamQuestion,
    StudyMaterial,
    StudyPlan,
    StudyTask,
    Student,
    Subject,
)
from app.services.study_plan_service import (
    calculate_plan_progress,
    complete_study_task,
    generate_study_plan,
    get_study_plan,
    rank_topics_for_study,
    recalculate_plan,
)


class StudyPlanTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.student = Student(name="Planner Student", email="planner@example.com")
        self.course = Course(name="Computer Science", student=self.student)
        self.subject = Subject(name="DBMS", course=self.course)
        self.db.add(self.subject)
        self.db.commit()
        self.db.refresh(self.subject)
        self.material = StudyMaterial(
            title="DBMS PYQ Set",
            file_path="dbms-pyq.pdf",
            subject_id=self.subject.id,
            material_type=MaterialType.PYQ.value,
        )
        self.db.add(self.material)
        self.db.commit()
        self.db.refresh(self.material)
        for year, topic, count in (
            (2022, "Normalization", 3),
            (2023, "Normalization", 2),
            (2024, "Normalization", 2),
            (2023, "Transactions", 1),
            (2024, "Transactions", 1),
            (2024, "Indexing", 1),
        ):
            for index in range(count):
                self.db.add(
                    ExamQuestion(
                        subject_id=self.subject.id,
                        study_material_id=self.material.id,
                        question_text=f"{topic} question {year}-{index}",
                        year=year,
                        topic=topic,
                    )
                )
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_priority_uses_pyq_importance_and_frequency(self):
        ranked = rank_topics_for_study(self.db, self.subject.id)

        self.assertEqual(ranked[0]["topic"], "Normalization")
        self.assertEqual(ranked[0]["priority"], 1)
        self.assertGreater(ranked[0]["frequency"], ranked[-1]["frequency"])

    def test_generate_agenda_reserves_revision_days_and_respects_daily_hours(self):
        today = date(2026, 10, 1)
        exam_date = today + timedelta(days=10)
        plan = generate_study_plan(
            self.db,
            student_id=self.student.id,
            subject_id=self.subject.id,
            exam_date=exam_date,
            hours_per_day=3,
            subject_difficulty=4,
            today=today,
        )
        view = get_study_plan(self.db, plan.id)
        agenda = view["daily_agenda"]

        self.assertEqual(agenda[-1]["date"], exam_date - timedelta(days=1))
        self.assertTrue(any("mock test" in task["topic"].lower() for day in agenda for task in day["tasks"]))
        self.assertTrue(any("revision" in task["topic"].lower() for day in agenda for task in day["tasks"]))
        for day in agenda:
            self.assertLessEqual(
                sum(task["estimated_hours"] for task in day["tasks"]),
                plan.hours_per_day + 1e-6,
            )
        task_hours = {}
        for task in plan.tasks:
            if task.topic in {"Normalization", "Transactions", "Indexing"}:
                task_hours[task.topic] = task_hours.get(task.topic, 0) + task.estimated_hours
        self.assertGreater(task_hours["Normalization"], task_hours["Indexing"])

    def test_completion_updates_plan_progress(self):
        today = date(2026, 10, 1)
        plan = generate_study_plan(
            self.db,
            self.student.id,
            self.subject.id,
            today + timedelta(days=6),
            2,
            today=today,
        )
        task_id = plan.tasks[0].id

        updated_plan = complete_study_task(self.db, task_id)
        persisted_task = self.db.query(StudyTask).filter(StudyTask.id == task_id).one()

        self.assertEqual(persisted_task.status, StudyTaskStatus.COMPLETED.value)
        self.assertEqual(updated_plan["progress"]["tasks_done"], 1)
        self.assertEqual(
            updated_plan["progress"]["tasks_done"]
            + updated_plan["progress"]["tasks_remaining"],
            len(plan.tasks),
        )

    def test_recalculate_compresses_and_moves_missed_tasks(self):
        today = date(2026, 10, 4)
        start_date = today - timedelta(days=3)
        plan = StudyPlan(
            student_id=self.student.id,
            subject_id=self.subject.id,
            exam_date=today + timedelta(days=2),
            hours_per_day=2,
            created_at=datetime.combine(start_date, datetime.min.time()),
        )
        plan.tasks = [
            StudyTask(
                day_number=1,
                topic="Normalization",
                priority=1,
                estimated_hours=2,
                status="PENDING",
            ),
            StudyTask(
                day_number=2,
                topic="Transactions",
                priority=2,
                estimated_hours=2,
                status="PENDING",
            ),
            StudyTask(
                day_number=4,
                topic="Mock test",
                priority=1,
                estimated_hours=2,
                status="PENDING",
            ),
        ]
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)

        result, rescheduled_count = recalculate_plan(
            self.db,
            plan.id,
            today=today,
        )
        reloaded = self.db.query(StudyPlan).filter(StudyPlan.id == plan.id).one()
        daily_hours = {}
        for task in reloaded.tasks:
            self.assertGreaterEqual(task.day_number, 4)
            self.assertLess(task.day_number, (plan.exam_date - start_date).days + 1)
            daily_hours[task.day_number] = daily_hours.get(task.day_number, 0) + task.estimated_hours

        self.assertGreater(rescheduled_count, 0)
        self.assertTrue(result["daily_agenda"])
        self.assertTrue(all(hours <= plan.hours_per_day + 1e-6 for hours in daily_hours.values()))

    def test_progress_for_empty_plan_is_zero(self):
        plan = StudyPlan(
            student_id=self.student.id,
            subject_id=self.subject.id,
            exam_date=date(2026, 12, 20),
            hours_per_day=2,
            created_at=datetime(2026, 10, 1),
        )
        self.assertEqual(
            calculate_plan_progress(plan),
            {"completion": 0, "tasks_done": 0, "tasks_remaining": 0},
        )


if __name__ == "__main__":
    unittest.main()