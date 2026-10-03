import unittest
from datetime import date, datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.db.models import CalendarEvent, Course, DigitalTwinSnapshot, Semester, SemesterSubject, Student, Subject
from app.main import app
from app.services.calendar_service import get_agenda
from app.services.habit_service import create_habit, log_habit
from app.services.notification_service import generate_alerts
from app.services.productivity_service import analyze_productivity
from app.services.scheduler_service import generate_intelligent_schedule
from app.services.time_service import utc_now_naive


class PhaseBCIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.student = Student(name="Phase BC", email="phasebc@example.test")
        self.course = Course(name="CS", student=self.student)
        self.subject = Subject(name="Algorithms", course=self.course)
        self.db.add(self.subject)
        self.db.commit()
        self.db.refresh(self.student)
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

    def test_goals_milestones_progress_api(self):
        goal = self.client.post(
            f"/api/goals/{self.student.id}",
            json={"title": "Reach CPI target", "goal_type": "CPI", "target_value": 8.5, "target_unit": "CPI"},
        )
        self.assertEqual(goal.status_code, 200)
        goal_id = goal.json()["data"]["id"]
        milestone = self.client.post(
            f"/api/milestones/{goal_id}",
            json={"title": "Complete semester", "target_value": 1},
        )
        self.assertEqual(milestone.status_code, 200)
        progress = self.client.post(f"/api/progress/{goal_id}", json={"progress_value": 8.5})
        self.assertEqual(progress.status_code, 200)
        self.assertEqual(self.client.get(f"/api/goals/{self.student.id}").json()["data"][0]["progress_percent"], 100.0)
        self.assertEqual(len(self.client.get(f"/api/progress/{goal_id}").json()["data"]), 1)

    def test_habit_streak_completion_and_consistency(self):
        habit = create_habit(self.db, self.student.id, "Daily study", "DAILY_STUDY", 7)
        today = utc_now_naive().date()
        for days_ago in (2, 1, 0):
            log_habit(self.db, self.student.id, habit.id, today - timedelta(days=days_ago), duration_minutes=40)
        self.db.refresh(habit)
        self.assertEqual(habit.streak.current_streak, 3)
        self.assertEqual(habit.streak.longest_streak, 3)
        self.assertGreater(habit.streak.completion_rate, 0)
        self.assertGreater(habit.streak.consistency_score, 0)
        # A second write for the same habit/day updates the unique daily log.
        log_habit(self.db, self.student.id, habit.id, today, completed=False)
        self.assertEqual(len(habit.logs), 3)

    def test_goal_habit_and_agenda_http_routes(self):
        goal = self.client.post(f"/api/goals/{self.student.id}", json={"title": "Study", "goal_type": "STUDY_HOURS", "target_value": 12})
        self.assertEqual(goal.status_code, 200)
        habit = self.client.post(f"/api/habits/{self.student.id}", json={"habit_name": "PYQ practice", "category": "PYQ_PRACTICE", "target_per_week": 3})
        self.assertEqual(habit.status_code, 200)
        habit_id = habit.json()["data"]["id"]
        log = self.client.post(f"/api/habits/{habit_id}/logs", json={"completed": True, "duration_minutes": 30})
        self.assertEqual(log.status_code, 200)
        self.assertIn("/api/calendar/{student_id}/today", app.openapi()["paths"])
        self.assertIn("items", self.client.get(f"/api/calendar/{self.student.id}/today").json()["data"])

    def test_semester_copilot_returns_readiness_exam_and_revision_data(self):
        from app.agents.semester_copilot_agent import SemesterCopilotAgent
        from app.db.models import AcademicDeadline, Topic, TopicMastery
        from app.services.academic_profile_service import create_or_update_profile

        create_or_update_profile(self.db, self.student.id, {"semester": 2})
        semester = Semester(
            student_id=self.student.id,
            semester_number=2,
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() + timedelta(days=90),
            target_cgpa=8.0,
            subjects=[SemesterSubject(subject=self.subject, target_score=80)],
        )
        self.db.add(semester)
        self.db.add(DigitalTwinSnapshot(student_id=self.student.id, academic_profile_id=1, overall_readiness=55, risk_level="MEDIUM"))
        topic = Topic(subject_id=self.subject.id, name="Graph traversal")
        self.db.add(topic)
        self.db.flush()
        self.db.add(TopicMastery(student_id=self.student.id, topic_id=topic.id, mastery_score=20, attempt_count=1))
        self.db.add(AcademicDeadline(student_id=self.student.id, academic_profile_id=1, title="Final exam", type="EXAM", due_date=datetime.utcnow() + timedelta(days=5), priority="HIGH"))
        self.db.commit()
        result = SemesterCopilotAgent().execute({"db": self.db, "student_id": self.student.id})
        self.assertEqual(result["agent_name"], "semester_copilot")
        self.assertEqual(result["data"]["readiness_forecast"]["current_readiness"], 55)
        self.assertTrue(result["data"]["exam_countdowns"])
        self.assertTrue(result["data"]["revision_roadmap"])

    def test_agenda_unifies_calendar_study_deadline_and_reminder(self):
        from app.db.models import Reminder
        from app.services.deadline_service import create_deadline
        from app.services.scheduler_service import create_study_block

        from app.services.academic_profile_service import create_or_update_profile

        create_or_update_profile(self.db, self.student.id, {})
        today = utc_now_naive().date()
        start = datetime.combine(today, datetime.min.time()) + timedelta(hours=10)
        CalendarEvent(student_id=self.student.id, title="Lecture", start_time=start, end_time=start + timedelta(hours=1), event_type="CLASS")
        self.db.add(CalendarEvent(student_id=self.student.id, title="Lecture", start_time=start, end_time=start + timedelta(hours=1), event_type="CLASS"))
        self.db.add(Reminder(student_id=self.student.id, title="Review", trigger_time=start + timedelta(hours=3)))
        self.db.commit()
        create_deadline(self.db, self.student.id, {"title": "Quiz", "type": "QUIZ", "due_date": start + timedelta(hours=2)})
        create_study_block(self.db, self.student.id, {"title": "Revision", "block_type": "REVISION", "start_time": start + timedelta(hours=4), "end_time": start + timedelta(hours=4, minutes=45), "planned_duration": 45})
        agenda = get_agenda(self.db, self.student.id, today)
        self.assertEqual({item["kind"] for item in agenda["items"]}, {"CALENDAR", "DEADLINE", "REMINDER", "STUDY_BLOCK"})
        self.assertEqual([item["start_time"] for item in agenda["items"]], sorted(item["start_time"] for item in agenda["items"]))

    def test_intelligent_schedule_uses_priority_and_avoids_calendar_conflicts(self):
        from app.services.academic_profile_service import create_or_update_profile
        from app.services.attendance_service import upsert_attendance
        from app.services.deadline_service import create_deadline

        create_or_update_profile(self.db, self.student.id, {})
        upsert_attendance(self.db, self.student.id, self.subject.id, 5, 10)
        now = utc_now_naive() + timedelta(days=1)
        self.db.add(CalendarEvent(student_id=self.student.id, title="Busy", start_time=now, end_time=now + timedelta(hours=1), event_type="CLASS"))
        self.db.commit()
        create_deadline(self.db, self.student.id, {"title": "Exam", "type": "EXAM", "due_date": now + timedelta(days=2), "priority": "CRITICAL", "subject_id": self.subject.id})
        blocks = generate_intelligent_schedule(self.db, self.student.id, now, available_hours=1, horizon_days=2, session_minutes=30)
        self.assertTrue(blocks)
        self.assertTrue(all(block.end_time > block.start_time for block in blocks))
        self.assertTrue(all(not (block.start_time < now + timedelta(hours=1) and block.end_time > now) for block in blocks))
        self.assertTrue(all(block.title and block.block_type for block in blocks))

    def test_productivity_agent_data_and_notification_intelligence(self):
        from app.agents.productivity_agent import ProductivityAgent
        from app.db.models import Topic, TopicMastery

        create_habit(self.db, self.student.id, "Review", "REVISION", 7)
        topic = Topic(subject_id=self.subject.id, name="Graphs")
        self.db.add(topic)
        self.db.flush()
        self.db.add(TopicMastery(student_id=self.student.id, topic_id=topic.id, mastery_score=20, attempt_count=1))
        self.db.commit()
        data = analyze_productivity(self.db, self.student.id)
        self.assertIn("productivity_score", data)
        result = ProductivityAgent().execute({"db": self.db, "student_id": self.student.id})
        self.assertEqual(result["agent_name"], "productivity")
        alerts = generate_alerts(self.db, self.student.id)
        self.assertTrue(any(item.title == "Weak topic" for item in alerts))
        self.assertTrue(any(item.title == "Missed habit" for item in alerts))
        self.assertEqual(generate_alerts(self.db, self.student.id), [])

if __name__ == "__main__":
    unittest.main()
