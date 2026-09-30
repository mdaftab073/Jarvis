import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db.models import Course, Student, Subject
from app.models import Topic, TopicMastery, QuizSession, LearningSession
from app.agents.learning_agent import LearningAgent


class Phase14LearningAgentTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

        self.student = Student(name="Agent Learner", email="agentlearner@example.com")
        self.course = Course(name="CS", student=self.student)
        self.subject = Subject(name="Distributed Systems", course=self.course)
        self.db.add(self.student)
        self.db.add(self.subject)
        self.db.commit()
        self.db.refresh(self.student)
        self.db.refresh(self.subject)

        self.agent = LearningAgent()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_missing_context_returns_error(self):
        res = self.agent.execute({})
        self.assertIn("Missing db or student_id", res["summary"])
        self.assertTrue(res["risks"])

    def test_empty_learning_state(self):
        res = self.agent.execute({"db": self.db, "student_id": self.student.id})
        self.assertEqual(res["agent_name"], "learning")
        self.assertEqual(res["data"]["average_mastery"], 0.0)
        self.assertEqual(res["data"]["weak_topics"], [])
        self.assertEqual(res["data"]["strong_topics"], [])
        self.assertEqual(res["data"]["overall_readiness"], "LOW")
        self.assertTrue(len(res["recommendations"]) > 0)

    def test_weak_and_strong_topics_detection(self):
        t1 = Topic(subject_id=self.subject.id, name="Consensus Algorithms")
        t2 = Topic(subject_id=self.subject.id, name="Vector Clocks")
        t3 = Topic(subject_id=self.subject.id, name="RPC Protocols")
        self.db.add_all([t1, t2, t3])
        self.db.commit()

        # t1 weak (30%), t2 strong (85%), t3 medium (60%)
        m1 = TopicMastery(student_id=self.student.id, topic_id=t1.id, mastery_score=30.0, attempt_count=2)
        m2 = TopicMastery(student_id=self.student.id, topic_id=t2.id, mastery_score=85.0, attempt_count=5)
        m3 = TopicMastery(student_id=self.student.id, topic_id=t3.id, mastery_score=60.0, attempt_count=3)
        self.db.add_all([m1, m2, m3])

        # Add sessions
        s1 = LearningSession(student_id=self.student.id, subject_id=self.subject.id, activity_type="flashcard_review", duration_minutes=40.0)
        s2 = LearningSession(student_id=self.student.id, subject_id=self.subject.id, activity_type="quiz", duration_minutes=30.0, score=75.0)
        self.db.add_all([s1, s2])
        self.db.commit()

        res = self.agent.execute({"db": self.db, "student_id": self.student.id})
        data = res["data"]

        # Weak topics check
        weak_names = [w["topic_name"] for w in data["weak_topics"]]
        self.assertIn("Consensus Algorithms", weak_names)
        self.assertNotIn("Vector Clocks", weak_names)

        # Strong topics check
        strong_names = [s["topic_name"] for s in data["strong_topics"]]
        self.assertIn("Vector Clocks", strong_names)
        self.assertNotIn("Consensus Algorithms", strong_names)

        # Average mastery = (30 + 85 + 60) / 3 = 58.33
        self.assertAlmostEqual(data["average_mastery"], 58.33, delta=0.1)
        self.assertEqual(data["overall_readiness"], "MEDIUM")
        self.assertEqual(data["total_time_minutes"], 70.0)

        # Recommendations contain weak topic reference
        rec_text = " ".join(res["recommendations"])
        self.assertIn("Consensus Algorithms", rec_text)

    def test_critically_low_mastery_triggers_risk(self):
        t1 = Topic(subject_id=self.subject.id, name="Byzantine Fault Tolerance")
        self.db.add(t1)
        self.db.commit()

        m1 = TopicMastery(student_id=self.student.id, topic_id=t1.id, mastery_score=20.0, attempt_count=1)
        self.db.add(m1)
        self.db.commit()

        res = self.agent.execute({"db": self.db, "student_id": self.student.id})
        risk_msgs = [r["message"] for r in res["risks"]]
        self.assertTrue(any("critically low" in msg.lower() for msg in risk_msgs))


if __name__ == "__main__":
    unittest.main()
