import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.agents.agent_registry import create_default_registry
from app.agents.director_agent import create_execution_plan
from app.db.database import Base, get_db
from app.db.models import CalendarEvent, Course, Student, Subject
from app.schemas.digital_twin import StudentAcademicProfileResponse
from app.schemas.student_os import ProfileInput
from app.main import app
from app.services.academic_profile_service import create_or_update_profile
from app.services.attendance_service import attendance_risk, classes_to_recover, upsert_attendance
from app.services.deadline_service import create_deadline, upcoming_deadlines
from app.services.calendar_service import create_event
from app.services.dashboard_service import get_dashboard
from app.services.grade_service import add_grade, grade_analytics
from app.services.scheduler_service import create_study_block, generate_study_schedule
from app.api.student_scope import require_record_owner
from fastapi import HTTPException


class PhaseAStudentOSTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.student = Student(name="Phase A Student", email="phasea@example.com")
        self.subject = Subject(name="Algorithms", course=Course(name="CS", student=self.student))
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

    def _profile(self):
        return create_or_update_profile(self.db, self.student.id, {"semester": 2})

    def test_relationships_and_database_constraints(self):
        profile = self._profile()
        record = upsert_attendance(self.db, self.student.id, self.subject.id, 8, 10)
        self.assertEqual(record.academic_profile.student_id, self.student.id)
        self.assertIn(record, profile.attendance_records)
        self.db.add(CalendarEvent(student_id=self.student.id, title="Invalid", start_time=datetime(2026, 10, 2), end_time=datetime(2026, 10, 1), event_type="OTHER"))
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

    def test_attendance_thresholds_recovery_and_grade_analytics(self):
        self._profile()
        other_subject = Subject(name="Networks", course=self.subject.course)
        self.db.add(other_subject)
        self.db.commit()
        self.assertEqual([attendance_risk(value) for value in (None, 75, 74, 65, 64)], ["UNKNOWN", "SAFE", "WARNING", "WARNING", "CRITICAL"])
        self.assertEqual(classes_to_recover(6, 10), 6)
        self.assertEqual(classes_to_recover(15, 20), 0)
        upsert_attendance(self.db, self.student.id, self.subject.id, 7, 10)
        add_grade(self.db, self.student.id, {"subject_id": self.subject.id, "semester": 2, "credits": 3, "grade": "A", "grade_points": 8, "grade_type": "FINAL", "component_type": "OTHER", "obtained_marks": 80, "max_marks": 100, "grade_letter": "A"})
        add_grade(self.db, self.student.id, {"subject_id": other_subject.id, "semester": 2, "credits": 1, "grade": "A+", "grade_points": 9, "grade_type": "FINAL", "component_type": "OTHER", "obtained_marks": 90, "max_marks": 100, "grade_letter": "A+"})
        self.assertEqual(grade_analytics(self.db, self.student.id)["spi_by_semester"][2], 8.25)
        self.assertEqual(grade_analytics(self.db, self.student.id)["cpi"], 8.25)
        from app.services.digital_twin_service import build_and_save_snapshot

        snapshot = build_and_save_snapshot(self.db, self._profile().id)
        self.assertEqual(len(snapshot.grade_summary[str(self.subject.id)]["final_grades"]), 1)

    def test_component_and_repeat_final_grades_do_not_double_count(self):
        self._profile()
        add_grade(self.db, self.student.id, {"subject_id": self.subject.id, "semester": 1, "credits": 3, "grade_points": 10, "grade_type": "COMPONENT", "component_type": "CT1"})
        self.assertIsNone(grade_analytics(self.db, self.student.id)["cpi"])
        add_grade(self.db, self.student.id, {"subject_id": self.subject.id, "semester": 1, "credits": 3, "grade_points": 7, "grade_type": "FINAL"})
        add_grade(self.db, self.student.id, {"subject_id": self.subject.id, "semester": 1, "credits": 3, "grade_points": 9, "grade_type": "FINAL"})
        self.assertEqual(grade_analytics(self.db, self.student.id)["spi_by_semester"][1], 9.0)
        self.assertEqual(grade_analytics(self.db, self.student.id)["cpi"], 9.0)

    def test_deadline_priority_and_schedule_conflict_detection(self):
        self._profile()
        now = datetime.utcnow()
        create_deadline(self.db, self.student.id, {"title": "Soon", "type": "ASSIGNMENT", "due_date": now + timedelta(days=2), "priority": "LOW"})
        create_deadline(self.db, self.student.id, {"title": "Exam", "type": "EXAM", "due_date": now + timedelta(days=5), "priority": "CRITICAL"})
        self.assertEqual(upcoming_deadlines(self.db, self.student.id)[0].title, "Exam")
        calendar_start = now + timedelta(days=1)
        self.db.add(CalendarEvent(student_id=self.student.id, title="Lecture", start_time=calendar_start, end_time=calendar_start + timedelta(hours=1), event_type="CLASS"))
        self.db.commit()
        with self.assertRaisesRegex(ValueError, "conflicts"):
            generate_study_schedule(self.db, self.student.id, [self.subject.id], calendar_start + timedelta(minutes=30), 45, 15)
        blocks = generate_study_schedule(self.db, self.student.id, [self.subject.id, self.subject.id], calendar_start + timedelta(hours=1), 45, 15)
        self.assertEqual(len(blocks), 2)
        with self.assertRaisesRegex(ValueError, "conflicts"):
            create_study_block(self.db, self.student.id, {"subject_id": self.subject.id, "start_time": blocks[0].start_time, "end_time": blocks[0].end_time, "planned_duration": 45})

    def test_scheduler_timezone_boundary_and_invalid_range_edges(self):
        self._profile()
        event_start = datetime(2026, 10, 2, 9, tzinfo=timezone(timedelta(hours=2)))
        event = create_event(self.db, self.student.id, {
            "title": "Lab",
            "start_time": event_start,
            "end_time": event_start + timedelta(hours=1),
            "event_type": "CLASS",
        })
        self.assertEqual(event.start_time, datetime(2026, 10, 2, 7))
        adjacent = create_study_block(self.db, self.student.id, {
            "subject_id": self.subject.id,
            "start_time": datetime(2026, 10, 2, 8),
            "end_time": datetime(2026, 10, 2, 8, 30),
        })
        self.assertEqual(adjacent.start_time, event.end_time)
        with self.assertRaisesRegex(ValueError, "after"):
            create_study_block(self.db, self.student.id, {
                "subject_id": self.subject.id,
                "start_time": datetime(2026, 10, 2, 10),
                "end_time": datetime(2026, 10, 2, 9),
            })

    def test_api_and_dashboard_aggregation(self):
        response = self.client.put(f"/api/academic-profiles/{self.student.id}", json={"semester": 2, "branch": "CS"})
        self.assertEqual(response.status_code, 200)
        response = self.client.post(f"/api/attendance/{self.student.id}", json={"subject_id": self.subject.id, "attended_classes": 7, "total_classes": 10})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["risk"], "WARNING")
        response = self.client.post(f"/api/grades/{self.student.id}", json={"subject_id": self.subject.id, "semester": 2, "credits": 3, "grade": "A", "grade_points": 8, "grade_type": "FINAL"})
        self.assertEqual(response.status_code, 200)
        due = (datetime.utcnow() + timedelta(days=2)).isoformat()
        response = self.client.post(f"/api/deadlines/{self.student.id}", json={"title": "Quiz", "type": "QUIZ", "due_date": due, "priority": "HIGH"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["type"], "QUIZ")
        dashboard = self.client.get(f"/api/dashboard/{self.student.id}").json()["data"]
        self.assertIn("deadlines", dashboard)
        self.assertEqual(dashboard["readiness"], 70.0)
        self.assertEqual(dashboard["grades"][0]["grade_type"], "FINAL")
        self.assertEqual(dashboard["deadlines"][0]["type"], "QUIZ")
        self.assertIn("/api/dashboard/{student_id}", app.openapi()["paths"])

    def test_legacy_department_maps_to_branch_without_api_department_field(self):
        profile = create_or_update_profile(
            self.db,
            self.student.id,
            {"department": "Computer Engineering"},
        )
        legacy_payload = ProfileInput.model_validate(
            {"department": "Electrical Engineering"}
        )
        output = StudentAcademicProfileResponse.model_validate(profile).model_dump()

        self.assertEqual(profile.branch, "Computer Engineering")
        self.assertEqual(legacy_payload.branch, "Electrical Engineering")
        self.assertNotIn("department", output)

    def test_dashboard_does_not_use_stale_snapshot_readiness(self):
        profile = self._profile()
        upsert_attendance(self.db, self.student.id, self.subject.id, 5, 10)
        from app.db.models import DigitalTwinSnapshot

        self.db.add(DigitalTwinSnapshot(student_id=self.student.id, academic_profile_id=profile.id, overall_readiness=99, risk_level="LOW"))
        self.db.commit()
        dashboard = get_dashboard(self.db, self.student.id)
        self.assertEqual(dashboard["readiness"], 50.0)
        self.assertEqual(dashboard["readiness_snapshot"]["score"], 99.0)

    def test_dashboard_without_academic_profile_keeps_independent_data(self):
        from app.db.models import StudentNotification
        from app.models import Topic, TopicMastery

        topic = Topic(subject_id=self.subject.id, name="Sorting")
        self.db.add(topic)
        self.db.flush()
        self.db.add(TopicMastery(student_id=self.student.id, topic_id=topic.id, mastery_score=80, attempt_count=2))
        self.db.add(StudentNotification(student_id=self.student.id, title="Welcome", message="Ready"))
        event_start = datetime.utcnow() + timedelta(days=1)
        self.db.add(CalendarEvent(student_id=self.student.id, title="Class", start_time=event_start, end_time=event_start + timedelta(hours=1), event_type="CLASS"))
        self.db.commit()

        dashboard = get_dashboard(self.db, self.student.id)
        self.assertIsNone(dashboard["profile"])
        self.assertEqual(dashboard["readiness"], 80.0)
        self.assertEqual(len(dashboard["mastery"]), 1)
        self.assertEqual(len(dashboard["notifications"]), 1)
        self.assertEqual(len(dashboard["calendar"]), 1)

    def test_digital_twin_mastery_recommendation_uses_percentage_scale(self):
        from app.db.models import Topic, TopicMastery
        from app.services.digital_twin_service import _generate_recommendations

        profile = self._profile()
        topic = Topic(subject_id=self.subject.id, name="Graphs")
        self.db.add(topic)
        self.db.flush()
        mastery = TopicMastery(student_id=self.student.id, topic_id=topic.id, mastery_score=25, attempt_count=1)
        self.db.add(mastery)
        recommendations = _generate_recommendations(profile, [], [mastery], [], 1)
        mastery_recommendation = next(item for item in recommendations if item["type"] == "MASTERY_IMPROVEMENT")
        self.assertIn("25.0%", mastery_recommendation["message"])

    def test_legacy_profile_writes_are_visible_to_student_scoped_reads(self):
        from app.schemas.digital_twin import AttendanceRecordCreate, DeadlineItemCreate, GradeRecordCreate, StudyActivityLogCreate
        from app.services.digital_twin_service import (
            add_grade_record,
            build_and_save_snapshot,
            create_deadline as create_legacy_deadline,
            get_attendance,
            get_deadlines,
            get_grades,
            get_latest_snapshot,
            get_study_activity,
            get_or_create_academic_profile,
            log_study_activity,
            upsert_attendance as legacy_upsert_attendance,
        )
        from app.services.attendance_service import list_attendance
        from app.services.deadline_service import list_deadlines
        from app.services.grade_service import grade_analytics

        profile = get_or_create_academic_profile(self.db, self.student.id)
        legacy_upsert_attendance(self.db, profile.id, AttendanceRecordCreate(subject_id=self.subject.id, attended_classes=7, total_classes=10))
        add_grade_record(self.db, profile.id, GradeRecordCreate(subject_id=self.subject.id, component_type="CT1", obtained_marks=70, max_marks=100))
        create_legacy_deadline(self.db, profile.id, DeadlineItemCreate(title="Legacy exam", due_date=datetime.utcnow() + timedelta(days=2)))
        log_study_activity(self.db, profile.id, StudyActivityLogCreate(activity_type="READING", duration_minutes=30))
        snapshot = build_and_save_snapshot(self.db, profile.id)

        self.assertEqual([item.id for item in get_attendance(self.db, profile.id)], [item.id for item in list_attendance(self.db, self.student.id)])
        self.assertEqual([item.id for item in get_grades(self.db, profile.id)], [item.id for item in self.db.query(type(get_grades(self.db, profile.id)[0])).filter_by(student_id=self.student.id).all()])
        self.assertEqual([item.id for item in get_deadlines(self.db, profile.id)], [item.id for item in list_deadlines(self.db, self.student.id)])
        self.assertEqual(len(get_study_activity(self.db, profile.id)), 1)
        self.assertEqual(get_latest_snapshot(self.db, profile.id).id, snapshot.id)
        self.assertEqual(grade_analytics(self.db, self.student.id)["cpi"], None)
        self.assertEqual(len(get_dashboard(self.db, self.student.id)["grades"]), 1)

    def test_notifications_calendar_and_schedule_api(self):
        self._profile()
        self.assertEqual(self.client.post(f"/api/notifications/{self.student.id}", json={"title": "Hello", "message": "Welcome"}).status_code, 200)
        event_start = (datetime.utcnow() + timedelta(days=1)).replace(microsecond=0)
        self.assertEqual(self.client.post(f"/api/calendar/{self.student.id}", json={"title": "Lecture", "start_time": event_start.isoformat(), "end_time": (event_start + timedelta(hours=1)).isoformat()}).status_code, 200)
        response = self.client.post(f"/api/schedule/{self.student.id}/generate", json={"subject_ids": [self.subject.id], "start_time": (event_start + timedelta(hours=2)).isoformat(), "session_length": 30})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["data"]), 1)

    def test_reminder_crud_and_owner_scope_hook(self):
        response = self.client.post(
            f"/api/reminders/{self.student.id}",
            json={"title": "Review notes", "trigger_time": datetime.utcnow().isoformat()},
        )
        self.assertEqual(response.status_code, 200)
        reminder_id = response.json()["data"]["id"]
        self.assertEqual(len(self.client.get(f"/api/reminders/{self.student.id}").json()["data"]), 1)
        response = self.client.patch(
            f"/api/reminders/{reminder_id}",
            json={"completed": True, "title": "Review notes thoroughly"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["data"]["completed"])
        self.assertEqual(response.json()["data"]["title"], "Review notes thoroughly")
        self.assertEqual(self.client.delete(f"/api/reminders/{reminder_id}").status_code, 200)
        self.assertEqual(self.client.get(f"/api/reminders/{self.student.id}").json()["data"], [])
        with self.assertRaises(HTTPException) as error:
            require_record_owner(SimpleNamespace(state=SimpleNamespace(student_id=999)), self.student.id)
        self.assertEqual(error.exception.status_code, 403)

    def test_generated_deadline_reminder_never_has_past_trigger(self):
        self._profile()
        now = datetime.utcnow()
        create_deadline(self.db, self.student.id, {
            "title": "Due soon",
            "type": "QUIZ",
            "due_date": now + timedelta(hours=12),
        })
        from app.services.reminder_service import generate_reminders

        reminders = generate_reminders(self.db, self.student.id, now=now)
        self.assertEqual(len(reminders), 1)
        self.assertGreaterEqual(reminders[0].trigger_time, now)

    def test_new_agents_and_director_routing(self):
        self._profile()
        registry = create_default_registry()
        expected = {"academic_profile", "attendance", "deadline", "notification", "calendar", "scheduler", "reminder"}
        self.assertTrue(expected.issubset(set(registry.names())))
        for name in expected:
            output = registry.get(name).execute({"db": self.db, "student_id": self.student.id})
            self.assertEqual(output["agent_name"], name)
        for goal, agent in (("attendance status", "attendance"), ("upcoming deadlines", "deadline"), ("my calendar", "calendar"), ("schedule study blocks", "scheduler"), ("show my academic profile", "academic_profile"), ("show notifications", "notification")):
            self.assertIn(agent, create_execution_plan(goal)["agents"])


if __name__ == "__main__":
    unittest.main()
