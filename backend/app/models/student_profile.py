from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.database import Base


class TimestampMixin:
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class MISStudentProfile(TimestampMixin, Base):
    __tablename__ = "mis_student_profiles"
    __table_args__ = (
        UniqueConstraint("student_id", name="uq_mis_student_profiles_student"),
        CheckConstraint("semester IS NULL OR semester >= 1", name="ck_mis_student_profiles_semester"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    roll_no = Column(String(50), nullable=True, index=True)
    name = Column(String(255), nullable=True)
    department = Column(String(255), nullable=True)
    program = Column(String(255), nullable=True)
    semester = Column(Integer, nullable=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True)
    raw_json = Column(JSON, nullable=False, default=dict)
    attendance_json = Column(JSON, nullable=False, default=list)
    results_json = Column(JSON, nullable=False, default=list)
    timetable_json = Column(JSON, nullable=False, default=list)
    student = relationship("Student", back_populates="mis_profile")