import json
import unittest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db.models import Course, Student, StudyMaterial, Subject
from app.schemas.topic import TopicCreate
from app.schemas.flashcard import FlashcardCreate, FlashcardDeckCreate
from app.schemas.quiz import QuizSessionCreate, QuizQuestionCreate, QuizAnswerCreate
from app.schemas.mastery_learning import MasteryCreate
from app.services.topic_service import TopicService
from app.services.topic_extraction_service import TopicExtractionService
from app.services.flashcard_service import FlashcardService
from app.services.flashcard_generation_service import FlashcardGenerationService
from app.services.quiz_service import QuizService
from app.services.mastery_service import MasteryService
from app.services.learning_session_service import LearningSessionService


class Phase14ServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

        self.student = Student(name="Service Student", email="services@example.com")
        self.course = Course(name="CS", student=self.student)
        self.subject = Subject(name="Databases", course=self.course)
        self.db.add(self.student)
        self.db.add(self.subject)
        self.db.commit()
        self.db.refresh(self.student)
        self.db.refresh(self.subject)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_topic_service_crud(self):
        svc = TopicService(self.db)
        topic = svc.create_topic(self.subject.id, TopicCreate(name="Relational Algebra", description="Math foundation"))
        self.assertEqual(topic.name, "Relational Algebra")

        fetched = svc.get_topic(topic.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.name, "Relational Algebra")

        subject_topics = svc.get_subject_topics(self.subject.id)
        self.assertEqual(len(subject_topics), 1)

        all_topics = svc.get_topics()
        self.assertEqual(len(all_topics), 1)

        svc.delete_topic(topic.id)
        self.assertIsNone(svc.get_topic(topic.id))

    def test_topic_extraction_service_with_mocked_groq(self):
        material = StudyMaterial(
            title="Database Intro",
            file_path="mock/path.pdf",
            subject_id=self.subject.id,
        )
        self.db.add(material)
        self.db.commit()
        self.db.refresh(material)

        fake_groq_response = MagicMock()
        fake_groq_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(["ACID Properties", "Normalization", "Indexing"])
                    }
                }
            ]
        }
        fake_groq_response.raise_for_status = MagicMock()

        svc = TopicExtractionService(self.db)
        with patch("httpx.post", return_value=fake_groq_response):
            created_topics = svc.extract_and_store(material.id, self.subject.id)

        self.assertEqual(len(created_topics), 3)
        names = [t.name for t in created_topics]
        self.assertIn("ACID Properties", names)
        self.assertIn("Normalization", names)
        self.assertIn("Indexing", names)

    def test_flashcard_service_crud(self):
        fc_svc = FlashcardService(self.db)
        deck = fc_svc.create_deck(self.subject.id, FlashcardDeckCreate(name="SQL Basics"))
        self.assertEqual(deck.name, "SQL Basics")

        topic = TopicService(self.db).create_topic(self.subject.id, TopicCreate(name="SQL DDL"))
        card = fc_svc.create_flashcard(
            deck.id,
            topic.id,
            FlashcardCreate(question="What is DROP TABLE?", answer="Removes a table definition", difficulty="easy"),
        )
        self.assertEqual(card.question, "What is DROP TABLE?")

        cards_in_deck = fc_svc.get_flashcards_by_deck(deck.id)
        self.assertEqual(len(cards_in_deck), 1)

        cards_in_topic = fc_svc.get_flashcards_by_topic(topic.id)
        self.assertEqual(len(cards_in_topic), 1)

        decks = fc_svc.get_decks_by_subject(self.subject.id)
        self.assertEqual(len(decks), 1)

    def test_flashcard_generation_service_with_mocked_groq(self):
        deck = FlashcardService(self.db).create_deck(self.subject.id, FlashcardDeckCreate(name="Generated Deck"))
        fake_groq_response = MagicMock()
        fake_groq_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps([
                            {"question": "Q1", "answer": "A1", "difficulty": "easy"},
                            {"question": "Q2", "answer": "A2", "difficulty": "hard"},
                        ])
                    }
                }
            ]
        }
        fake_groq_response.raise_for_status = MagicMock()

        gen_svc = FlashcardGenerationService(self.db)
        with patch("httpx.post", return_value=fake_groq_response):
            cards = gen_svc.generate_and_store(deck.id, ["Transactions"])

        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0].question, "Q1")
        self.assertEqual(cards[1].answer, "A2")

    def test_quiz_service(self):
        svc = QuizService(self.db)
        session = svc.create_session(
            QuizSessionCreate(student_id=self.student.id, subject_id=self.subject.id, total_questions=1)
        )
        self.assertIsNotNone(session.id)

        question = svc.add_question(
            session.id,
            QuizQuestionCreate(
                session_id=session.id,
                question="What does SQL stand for?",
                question_type="short_answer",
                correct_answer="Structured Query Language",
            ),
        )
        self.assertEqual(question.correct_answer, "Structured Query Language")

        answer = svc.submit_answer(
            question.id,
            QuizAnswerCreate(question_id=question.id, student_answer="Structured Query Language", is_correct=True),
        )
        self.assertTrue(answer.is_correct)

        fetched_questions = svc.get_questions(session.id)
        self.assertEqual(len(fetched_questions), 1)
        fetched_answers = svc.get_answers(question.id)
        self.assertEqual(len(fetched_answers), 1)

    def test_mastery_service(self):
        topic = TopicService(self.db).create_topic(self.subject.id, TopicCreate(name="B-Trees"))
        svc = MasteryService(self.db)

        m1 = svc.set_mastery(MasteryCreate(student_id=self.student.id, topic_id=topic.id, mastery_score=60.0))
        self.assertEqual(m1.mastery_score, 60.0)
        self.assertEqual(m1.attempt_count, 1)

        m2 = svc.set_mastery(MasteryCreate(student_id=self.student.id, topic_id=topic.id, mastery_score=85.0))
        self.assertEqual(m2.mastery_score, 85.0)
        self.assertEqual(m2.attempt_count, 2)

        record = svc.get_mastery(self.student.id, topic.id)
        self.assertIsNotNone(record)
        self.assertEqual(record.mastery_score, 85.0)

        records = svc.list_mastery_for_student(self.student.id)
        self.assertEqual(len(records), 1)

    def test_learning_session_service(self):
        svc = LearningSessionService(self.db)
        s1 = svc.create_session(
            student_id=self.student.id,
            subject_id=self.subject.id,
            activity_type="quiz",
            duration_minutes=15.0,
            score=80.0,
        )
        self.assertIsNotNone(s1.id)

        sessions = svc.list_for_student(self.student.id)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0].activity_type, "quiz")

        fetched = svc.get_session(s1.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.score, 80.0)


if __name__ == "__main__":
    unittest.main()
