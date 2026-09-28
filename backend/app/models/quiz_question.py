from sqlalchemy import Column, Integer, ForeignKey, String, Text, DateTime, func
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("quiz_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="SET NULL"), nullable=True, index=True)
    question = Column(Text, nullable=False)
    question_type = Column(String(20), nullable=False)  # e.g., MCQ, True/False, Short Answer
    correct_answer = Column(Text, nullable=False)

    session = relationship("QuizSession", back_populates="questions")
    topic = relationship("Topic", backref="quiz_questions")
    answers = relationship("QuizAnswer", back_populates="question", cascade="all, delete-orphan")
