import json
import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.db.models import Course, Student, StudyMaterial, Subject
from app.models import Topic, FlashcardDeck, Flashcard, QuizSession, QuizQuestion, TopicMastery, LearningSession
from app.main import app


class Phase14APITests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

        self.student = Student(name="API Learner", email="apilearner@example.com")
        self.course = Course(name="Computer Science", student=self.student)
        self.subject = Subject(name="Algorithms", course=self.course)
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

    # ── Topics Endpoints ──────────────────────────────────────────────
    def test_topics_crud_and_extract(self):
        # Initial empty
        res = self.client.get("/api/topics")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), [])

        # Create topic directly in DB to test GET
        topic = Topic(subject_id=self.subject.id, name="Dynamic Programming", description="Memoization & Tabulation")
        self.db.add(topic)
        self.db.commit()
        self.db.refresh(topic)

        # GET /api/topics
        res = self.client.get("/api/topics")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 1)
        self.assertEqual(res.json()[0]["name"], "Dynamic Programming")

        # GET /api/topics/{topic_id}
        res = self.client.get(f"/api/topics/{topic.id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["id"], topic.id)

        # GET /api/subjects/{subject_id}/topics
        res = self.client.get(f"/api/subjects/{self.subject.id}/topics")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 1)

        # POST /api/topics/extract/{material_id} with mocked LLM
        mat = StudyMaterial(title="Graph Algorithms", file_path="graph.pdf", subject_id=self.subject.id)
        self.db.add(mat)
        self.db.commit()
        self.db.refresh(mat)

        fake_groq = MagicMock()
        fake_groq.json.return_value = {
            "choices": [{"message": {"content": json.dumps(["Dijkstra", "Bellman-Ford"])}}]
        }
        fake_groq.raise_for_status = MagicMock()

        with patch("httpx.post", return_value=fake_groq):
            res = self.client.post(f"/api/topics/extract/{mat.id}?subject_id={self.subject.id}")
        self.assertEqual(res.status_code, 200)
        extracted = res.json()
        self.assertEqual(len(extracted), 2)
        names = [t["name"] for t in extracted]
        self.assertIn("Dijkstra", names)

    # ── Flashcards Endpoints ──────────────────────────────────────────
    def test_flashcards_flow(self):
        fake_groq = MagicMock()
        fake_groq.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps([
                            {"question": "What is greedy choice?", "answer": "Locally optimal choice", "difficulty": "easy"},
                            {"question": "What is optimal substructure?", "answer": "Optimal solution contains sub-solutions", "difficulty": "medium"}
                        ])
                    }
                }
            ]
        }
        fake_groq.raise_for_status = MagicMock()

        # POST /api/flashcards/generate
        payload = {
            "subject_id": self.subject.id,
            "deck_name": "Greedy Algorithms",
            "topics": ["Greedy Choice", "Interval Scheduling"],
            "cards_per_topic": 2,
        }
        with patch("httpx.post", return_value=fake_groq):
            res = self.client.post("/api/flashcards/generate", json=payload)
        self.assertEqual(res.status_code, 200)
        deck_data = res.json()["deck"]
        cards = res.json()["flashcards"]
        self.assertEqual(deck_data["name"], "Greedy Algorithms")
        self.assertEqual(len(cards), 2)

        deck_id = deck_data["id"]

        # GET /api/flashcards/decks
        res = self.client.get(f"/api/flashcards/decks?subject_id={self.subject.id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 1)

        # GET /api/flashcards/decks/{deck_id}
        res = self.client.get(f"/api/flashcards/decks/{deck_id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["name"], "Greedy Algorithms")

    # ── Quizzes Endpoints ─────────────────────────────────────────────
    def test_quizzes_flow_and_mastery_update(self):
        topic = Topic(subject_id=self.subject.id, name="Sorting Algorithms")
        self.db.add(topic)
        self.db.commit()
        self.db.refresh(topic)

        # POST /api/quizzes/generate
        payload = {
            "student_id": self.student.id,
            "subject_id": self.subject.id,
            "questions": [
                {
                    "topic_id": topic.id,
                    "question": "What is worst case of QuickSort?",
                    "question_type": "short_answer",
                    "correct_answer": "O(n^2)",
                },
                {
                    "topic_id": topic.id,
                    "question": "Is MergeSort stable?",
                    "question_type": "true_false",
                    "correct_answer": "true",
                },
            ],
        }
        res = self.client.post("/api/quizzes/generate", json=payload)
        self.assertEqual(res.status_code, 200)
        session_id = res.json()["session"]["id"]
        questions = res.json()["questions"]
        self.assertEqual(len(questions), 2)

        q1_id = questions[0]["id"]
        q2_id = questions[1]["id"]

        # POST /api/quizzes/submit
        submit_payload = {
            "session_id": session_id,
            "answers": [
                {"question_id": q1_id, "student_answer": "O(n^2)"},
                {"question_id": q2_id, "student_answer": "false"},
            ],
            "update_mastery": True,
        }
        res = self.client.post("/api/quizzes/submit", json=submit_payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["score"], 1)
        self.assertEqual(data["total_questions"], 2)

        # GET /api/quizzes/session/{session_id}
        res = self.client.get(f"/api/quizzes/session/{session_id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["session"]["score"], 1)

        # GET /api/quizzes/history/{student_id}
        res = self.client.get(f"/api/quizzes/history/{self.student.id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 1)

    # ── Mastery Endpoints ─────────────────────────────────────────────
    def test_mastery_endpoints(self):
        topic = Topic(subject_id=self.subject.id, name="Recursion")
        self.db.add(topic)
        self.db.commit()
        self.db.refresh(topic)

        # Add a weak mastery score
        mastery = TopicMastery(
            student_id=self.student.id,
            topic_id=topic.id,
            mastery_score=35.0,
            attempt_count=2,
        )
        self.db.add(mastery)
        self.db.commit()

        # GET /api/mastery/student/{student_id}
        res = self.client.get(f"/api/mastery/student/{self.student.id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 1)
        self.assertEqual(res.json()[0]["mastery_score"], 35.0)

        # GET /api/mastery/subject/{subject_id}?student_id={student_id}
        res = self.client.get(f"/api/mastery/subject/{self.subject.id}?student_id={self.student.id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 1)

        # GET /api/mastery/weak/{student_id}
        res = self.client.get(f"/api/mastery/weak/{self.student.id}?threshold=50.0")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 1)
        self.assertEqual(res.json()[0]["topic_name"], "Recursion")

    # ── Learning Endpoints ────────────────────────────────────────────
    def test_learning_session_and_insights(self):
        # POST /api/learning/session
        payload = {
            "student_id": self.student.id,
            "subject_id": self.subject.id,
            "activity_type": "flashcard_review",
            "duration_minutes": 30.0,
            "score": 85.0,
        }
        res = self.client.post("/api/learning/session", json=payload)
        self.assertEqual(res.status_code, 200)
        session_data = res.json()
        self.assertEqual(session_data["activity_type"], "flashcard_review")

        # GET /api/learning/history/{student_id}
        res = self.client.get(f"/api/learning/history/{self.student.id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 1)

        # GET /api/learning/insights/{student_id}
        res = self.client.get(f"/api/learning/insights/{self.student.id}")
        self.assertEqual(res.status_code, 200)
        insights = res.json()
        self.assertIn("average_mastery", insights)
        self.assertIn("recommended_actions", insights)
        self.assertIn("overall_readiness", insights)


if __name__ == "__main__":
    unittest.main()
