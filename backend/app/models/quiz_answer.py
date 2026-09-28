from sqlalchemy import Column, Integer, ForeignKey, Text, Boolean, DateTime, func
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class QuizAnswer(Base):
    __tablename__ = "quiz_answers"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("quiz_questions.id", ondelete="CASCADE"), nullable=False, index=True)
    student_answer = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    answered_at = Column(DateTime(timezone=True), server_default=func.now())

    question = relationship("QuizQuestion", back_populates="answers")
