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
    
class StudyMaterial(Base):
    __tablename__ = "study_materials"

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

    subject_id = Column(
        Integer,
        ForeignKey("subjects.id"),
        nullable=False,
    )

    subject = relationship(
        "Subject",
        back_populates="materials",
    )