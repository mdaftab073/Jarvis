import unittest
from datetime import datetime
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db.models import Course, Student, Subject
from app.models import (
    Topic,
    FlashcardDeck,
    Flashcard,
    QuizSession,
    QuizQuestion,
    QuizAnswer,
    TopicMastery,
    LearningSession,
)


class Phase14ModelTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

        self.student = Student(name="Learner", email="learner@example.com")
        self.course = Course(name="CS", student=self.student)
        self.subject = Subject(name="Operating Systems", course=self.course)
        self.db.add(self.student)
        self.db.add(self.subject)
        self.db.commit()
        self.db.refresh(self.student)
        self.db.refresh(self.subject)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_topic_model_and_relationships(self):
        topic = Topic(subject_id=self.subject.id, name="Processes and Threads", description="Core OS concept")
        self.db.add(topic)
        self.db.commit()
        self.db.refresh(topic)

        self.assertIsNotNone(topic.id)
        self.assertEqual(topic.name, "Processes and Threads")
        self.assertEqual(topic.subject.name, "Operating Systems")
        self.assertIn(topic, self.subject.topics)

    def test_flashcard_deck_and_flashcards(self):
        deck = FlashcardDeck(subject_id=self.subject.id, name="OS Fundamentals")
        self.db.add(deck)
        self.db.commit()
        self.db.refresh(deck)

        topic = Topic(subject_id=self.subject.id, name="Deadlocks")
        self.db.add(topic)
        self.db.commit()
        self.db.refresh(topic)

        card = Flashcard(
            deck_id=deck.id,
            topic_id=topic.id,
            question="What are the 4 conditions for deadlock?",
            answer="Mutual exclusion, hold & wait, no preemption, circular wait",
            difficulty="medium",
        )
        self.db.add(card)
        self.db.commit()
        self.db.refresh(deck)

        self.assertEqual(len(deck.flashcards), 1)
        self.assertEqual(deck.flashcards[0].question, "What are the 4 conditions for deadlock?")
        self.assertEqual(deck.flashcards[0].topic.name, "Deadlocks")

    def test_quiz_session_and_questions(self):
        quiz = QuizSession(
            student_id=self.student.id,
            subject_id=self.subject.id,
            total_questions=2,
            score=None,
        )
        self.db.add(quiz)
        self.db.commit()
        self.db.refresh(quiz)

        q1 = QuizQuestion(
            session_id=quiz.id,
            question="Is paging used for virtual memory?",
            question_type="true_false",
            correct_answer="true",
        )
        self.db.add(q1)
        self.db.commit()
        self.db.refresh(q1)

        ans1 = QuizAnswer(
            question_id=q1.id,
            student_answer="true",
            is_correct=True,
        )
        self.db.add(ans1)
        self.db.commit()
        self.db.refresh(quiz)

        self.assertEqual(len(quiz.questions), 1)
        self.assertEqual(len(quiz.questions[0].answers), 1)
        self.assertTrue(quiz.questions[0].answers[0].is_correct)

    def test_topic_mastery_model(self):
        topic = Topic(subject_id=self.subject.id, name="Memory Management")
        self.db.add(topic)
        self.db.commit()
        self.db.refresh(topic)

        mastery = TopicMastery(
            student_id=self.student.id,
            topic_id=topic.id,
            mastery_score=85.5,
            attempt_count=4,
        )
        self.db.add(mastery)
        self.db.commit()
        self.db.refresh(mastery)

        self.assertEqual(mastery.mastery_score, 85.5)
        self.assertEqual(mastery.student.id, self.student.id)
        self.assertEqual(mastery.topic.id, topic.id)
        self.assertIn(mastery, self.student.topic_masteries)
        self.assertIn(mastery, topic.masteries)

    def test_learning_session_model(self):
        session = LearningSession(
            student_id=self.student.id,
            subject_id=self.subject.id,
            activity_type="flashcard_review",
            duration_minutes=25.0,
            score=90.0,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        self.assertIsNotNone(session.id)
        self.assertEqual(session.activity_type, "flashcard_review")
        self.assertEqual(session.duration_minutes, 25.0)
        self.assertIn(session, self.student.learning_sessions)


if __name__ == "__main__":
    unittest.main()
