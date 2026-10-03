import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.db.models import Course, Student, Subject
from app.models import Topic, FlashcardDeck, Flashcard, TopicMastery
from app.agents.director_agent import AcademicDirectorAgent, create_execution_plan
from app.main import app


class Phase14EndToEndIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

        self.student = Student(name="E2E Student", email="e2e@example.com")
        self.course = Course(name="Software Engineering", student=self.student)
        self.subject = Subject(name="Web Architecture", course=self.course)
        self.db.add(self.student)
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

    def test_full_learning_lifecycle_and_director_integration(self):
        # 1. Create Topics
        t1 = Topic(subject_id=self.subject.id, name="RESTful APIs", description="API design principles")
        t2 = Topic(subject_id=self.subject.id, name="GraphQL Schemas", description="Query language")
        self.db.add_all([t1, t2])
        self.db.commit()

        # 2. Add Flashcard Deck & Cards
        deck = FlashcardDeck(subject_id=self.subject.id, name="Web Services")
        self.db.add(deck)
        self.db.commit()
        card = Flashcard(
            deck_id=deck.id,
            topic_id=t1.id,
            question="What is idempotency?",
            answer="Same result on repeated requests",
            difficulty="easy",
        )
        self.db.add(card)
        self.db.commit()

        # 3. Create and Submit Quiz
        quiz_res = self.client.post(
            "/api/quizzes/generate",
            json={
                "student_id": self.student.id,
                "subject_id": self.subject.id,
                "questions": [
                    {
                        "topic_id": t1.id,
                        "question": "Is GET idempotent?",
                        "question_type": "true_false",
                        "correct_answer": "true",
                    },
                    {
                        "topic_id": t2.id,
                        "question": "Does GraphQL prevent over-fetching?",
                        "question_type": "true_false",
                        "correct_answer": "true",
                    },
                ],
            },
        )
        self.assertEqual(quiz_res.status_code, 200)
        session_id = quiz_res.json()["data"]["session"]["id"]
        q_ids = [q["id"] for q in quiz_res.json()["data"]["questions"]]

        # Submit answers: 1 right, 1 wrong
        submit_res = self.client.post(
            "/api/quizzes/submit",
            json={
                "session_id": session_id,
                "answers": [
                    {"question_id": q_ids[0], "student_answer": "true"},  # correct for t1
                    {"question_id": q_ids[1], "student_answer": "false"}, # wrong for t2
                ],
                "update_mastery": True,
            },
        )
        self.assertEqual(submit_res.status_code, 200)
        self.assertEqual(submit_res.json()["data"]["score"], 1)

        # 4. Verify Topic Mastery was updated in database
        mastery_t1 = self.db.query(TopicMastery).filter(TopicMastery.topic_id == t1.id).first()
        mastery_t2 = self.db.query(TopicMastery).filter(TopicMastery.topic_id == t2.id).first()
        self.assertIsNotNone(mastery_t1)
        self.assertIsNotNone(mastery_t2)
        self.assertGreater(mastery_t1.mastery_score, mastery_t2.mastery_score)

        # 5. Record a Learning Session via API
        session_res = self.client.post(
            "/api/learning/session",
            json={
                "student_id": self.student.id,
                "subject_id": self.subject.id,
                "activity_type": "flashcard_review",
                "duration_minutes": 45.0,
                "score": 90.0,
            },
        )
        self.assertEqual(session_res.status_code, 200)

        # 6. Verify Learning Insights via API
        insights_res = self.client.get(f"/api/learning/insights/{self.student.id}")
        self.assertEqual(insights_res.status_code, 200)
        insights = insights_res.json()["data"]
        self.assertEqual(insights["student_id"], self.student.id)
        self.assertTrue(len(insights["weak_topics"]) > 0)

        # 7. Test Director Planner selects learning agent for personalized learning goal
        plan = create_execution_plan("Analyze my topic mastery and learning progress")
        self.assertEqual(plan["goal_type"], "personalized_learning")
        self.assertIn("learning", plan["agents"])

        # 8. Run Director Agent with mocked LLM strategy generation
        director = AcademicDirectorAgent()
        context = {
            "db": self.db,
            "student_id": self.student.id,
            "goal": "Analyze my topic mastery and learning progress",
        }
        with patch("app.agents.director_agent.generate_agent_response") as mock_gen:
            mock_gen.return_value = {
                "summary": "Mastery analysis indicates weak performance on GraphQL Schemas.",
                "priority_actions": ["Review GraphQL Schemas using flashcards."],
                "next_steps": ["Complete a targeted revision quiz."],
            }
            director_result = director.execute(context)

        self.assertEqual(director_result["agent_name"], "director")
        self.assertIn("Mastery analysis", director_result["summary"])
        data = director_result["data"]
        self.assertIn("learning", data["selected_agents"])
        # Ensure learning weak topics are aggregated into director data
        weak_topics = data["weak_topics"]
        self.assertTrue(any("GraphQL" in str(wt) for wt in weak_topics))


if __name__ == "__main__":
    unittest.main()
