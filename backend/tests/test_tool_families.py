import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db.models import CalendarEvent, Course, Student, Subject
from app.models import Topic
from app.tools.exceptions import ToolOwnershipError
from app.tools.registry import get_tool_registry, tool_registry


class ToolFamilyTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.student = Student(name="Tool Student", email="tool@example.com")
        self.subject = Subject(name="Algorithms", course=Course(name="Computer Science", student=self.student))
        self.db.add(self.subject)
        self.db.commit()
        self.registry = get_tool_registry()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def call_tool(self, name, **payload):
        return self.registry.execute_tool(name, {"db": self.db, "student_id": self.student.id, **payload}).data

    def test_discovery_covers_requested_tool_families(self):
        names = {item["name"] for item in self.registry.list_tools()}
        self.assertTrue({
            "academic_profile", "grades", "attendance_summary", "rag_search", "study_materials",
            "study_plan", "topic_mastery", "flashcards", "quizzes", "goals", "habits",
            "productivity_analytics", "calendar_events", "study_schedule", "deadlines",
            "reminders",
        }.issubset(names))
        self.assertIs(self.registry, get_tool_registry())
        self.assertTrue(all("input_schema" in item for item in self.registry.list_tools()))

    def test_academic_and_study_tool_execution(self):
        self.assertEqual(self.call_tool("academic_profile")["attendance_count"], 0)
        self.assertEqual(self.call_tool("grades")["record_count"], 0)
        self.assertEqual(self.call_tool("attendance_summary"), [])
        subjects = self.call_tool("student_subjects", goal="Algorithms")
        self.assertEqual(subjects[0]["id"], self.subject.id)
        ranked = self.call_tool("study_plan", action="rank_topics", subject_id=self.subject.id)
        self.assertTrue(ranked)
        self.assertEqual(self.call_tool("study_materials", subject_id=self.subject.id), [])
        with patch("app.tools.study.tools.ask_question", return_value={"answer": "A", "results": [], "stats": {}}):
            result = self.call_tool("rag_search", question="Explain algorithms")
        self.assertEqual(result["answer"], "A")

    def test_learning_productivity_and_calendar_execution(self):
        topic = Topic(subject_id=self.subject.id, name="Sorting")
        self.db.add(topic)
        self.db.commit()
        self.assertEqual(self.call_tool("topic_mastery"), [])
        self.assertEqual(self.call_tool("flashcards", subject_id=self.subject.id), [])
        self.assertEqual(self.call_tool("quizzes"), [])
        self.assertEqual(self.call_tool("goals"), [])
        self.assertEqual(self.call_tool("habits"), [])
        self.assertIn("productivity_score", self.call_tool("productivity_analytics"))
        event = CalendarEvent(
            student_id=self.student.id,
            title="Lecture",
            start_time=datetime.utcnow() + timedelta(days=1),
            end_time=datetime.utcnow() + timedelta(days=1, hours=1),
            event_type="CLASS",
        )
        self.db.add(event)
        self.db.commit()
        self.assertEqual(len(self.call_tool("calendar_events")), 1)
        self.assertEqual(self.call_tool("study_schedule"), [])
        self.assertEqual(self.call_tool("deadlines"), [])
        self.assertEqual(self.call_tool("reminders"), [])

    def test_tools_reject_cross_student_subject_access(self):
        other = Student(name="Other Student", email="other-tool@example.com")
        other_subject = Subject(name="Private", course=Course(name="Other", student=other))
        self.db.add(other_subject)
        self.db.commit()
        with self.assertRaises(ToolOwnershipError):
            self.registry.execute_tool("study_materials", {"db": self.db, "student_id": self.student.id, "subject_id": other_subject.id})
        with self.assertRaises(ToolOwnershipError):
            self.registry.execute_tool("academic_profile", {"db": self.db, "student_id": self.student.id, "principal_id": other.id})

    def test_exported_singleton_loads_tools_on_discovery(self):
        self.assertGreater(len(tool_registry.list_tools()), 0)


if __name__ == "__main__":
    unittest.main()