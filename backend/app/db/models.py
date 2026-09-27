from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
)
from app.db.database import Base
from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy import CheckConstraint, Float

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)

    email = Column(String, unique=True, nullable=False)
    
    courses = relationship(
        "Course",
        back_populates="student",
        cascade="all, delete",
    )

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)

    description = Column(String, nullable=True)

    student_id = Column(
        Integer,
        ForeignKey("students.id"),
        nullable=False,
    )

    student = relationship(
        "Student",
        back_populates="courses",
    )
    
    subjects = relationship(
        "Subject",
        back_populates="course",
        cascade="all, delete",
    )

class Subject(Base):
    __tablename__ = "subjects"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    name = Column(
        String,
        nullable=False,
    )

    description = Column(
        String,
        nullable=True,
    )

    course_id = Column(
        Integer,
        ForeignKey("courses.id"),
        nullable=False,
    )

    course = relationship(
        "Course",
        back_populates="subjects",
    )
    
    materials = relationship(
        "StudyMaterial",
        back_populates="subject",
        cascade="all, delete",
    )

    exam_questions = relationship(
        "ExamQuestion",
        back_populates="subject",
        cascade="all, delete-orphan",
    )
    
class StudyMaterial(Base):
    __tablename__ = "study_materials"
    __table_args__ = (
        CheckConstraint(
            "material_type IN ('NOTES', 'PYQ', 'SYLLABUS', 'REFERENCE')",
            name="ck_study_materials_material_type",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    title = Column(
        String,
        nullable=False,
    )

    file_path = Column(
        String,
        nullable=False,
    )

    uploaded_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    embedding_status = Column(
        String,
        nullable=False,
        default="pending",
    )

    material_type = Column(
        String,
        nullable=False,
        default="NOTES",
        server_default="NOTES",
    )

    subject_id = Column(
        Integer,
        ForeignKey("subjects.id"),
        nullable=False,
    )

    subject = relationship(
        "Subject",
        back_populates="materials",
    )

    exam_questions = relationship(
        "ExamQuestion",
        back_populates="study_material",
        cascade="all, delete-orphan",
    )


class ExamQuestion(Base):
    __tablename__ = "exam_questions"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(
        Integer,
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    study_material_id = Column(
        Integer,
        ForeignKey("study_materials.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_text = Column(String, nullable=False)
    year = Column(Integer, nullable=True, index=True)
    unit = Column(String, nullable=True)
    topic = Column(String, nullable=True, index=True)
    marks = Column(Float, nullable=True)

    subject = relationship("Subject", back_populates="exam_questions")
    study_material = relationship(
        "StudyMaterial",
        back_populates="exam_questions",
    )