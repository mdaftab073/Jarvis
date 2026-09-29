from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    JSON,
    Text,
)
from app.db.database import Base
from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy import CheckConstraint, Float
from sqlalchemy import Date
from sqlalchemy import Boolean, UniqueConstraint

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

    study_plans = relationship(
        "StudyPlan",
        back_populates="student",
        cascade="all, delete-orphan",
    )

    topic_performances = relationship(
        "StudentTopicPerformance",
        back_populates="student",
        cascade="all, delete-orphan",
    )
    practice_sessions = relationship(
        "PracticeSession",
        back_populates="student",
        cascade="all, delete-orphan",
    )
    profile = relationship(
        "StudentProfile",
        back_populates="student",
        cascade="all, delete-orphan",
        uselist=False,
    )
    memories = relationship(
        "StudentMemory",
        back_populates="student",
        cascade="all, delete-orphan",
    )
    readiness_snapshots = relationship(
        "ReadinessSnapshot",
        back_populates="student",
        cascade="all, delete-orphan",
    )
    semesters = relationship(
        "Semester",
        back_populates="student",
        cascade="all, delete-orphan",
    )
    quiz_sessions = relationship(
        "QuizSession",
        back_populates="student",
        cascade="all, delete-orphan",
    )
    topic_masteries = relationship(
        "TopicMastery",
        back_populates="student",
        cascade="all, delete-orphan",
    )
    learning_sessions = relationship(
        "LearningSession",
        back_populates="student",
        cascade="all, delete-orphan",
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

    study_plans = relationship(
        "StudyPlan",
        back_populates="subject",
        cascade="all, delete-orphan",
    )

    topic_performances = relationship(
        "StudentTopicPerformance",
        back_populates="subject",
        cascade="all, delete-orphan",
    )
    practice_sessions = relationship(
        "PracticeSession",
        back_populates="subject",
        cascade="all, delete-orphan",
    )
    readiness_snapshots = relationship(
        "ReadinessSnapshot",
        back_populates="subject",
        cascade="all, delete-orphan",
    )
    semester_links = relationship(
        "SemesterSubject",
        back_populates="subject",
        cascade="all, delete-orphan",
    )
    topics = relationship(
        "Topic",
        back_populates="subject",
        cascade="all, delete-orphan",
    )
    flashcard_decks = relationship(
        "FlashcardDeck",
        back_populates="subject",
        cascade="all, delete-orphan",
    )
    quiz_sessions = relationship(
        "QuizSession",
        back_populates="subject",
        cascade="all, delete-orphan",
    )
    learning_sessions = relationship(
        "LearningSession",
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


class StudyPlan(Base):
    __tablename__ = "study_plans"
    __table_args__ = (
        CheckConstraint("hours_per_day > 0", name="ck_study_plans_hours_per_day"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_id = Column(
        Integer,
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exam_date = Column(Date, nullable=False)
    hours_per_day = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    student = relationship("Student", back_populates="study_plans")
    subject = relationship("Subject", back_populates="study_plans")
    tasks = relationship(
        "StudyTask",
        back_populates="study_plan",
        cascade="all, delete-orphan",
        order_by="StudyTask.day_number, StudyTask.priority, StudyTask.id",
    )


class StudyTask(Base):
    __tablename__ = "study_tasks"
    __table_args__ = (
        CheckConstraint("day_number >= 1", name="ck_study_tasks_day_number"),
        CheckConstraint("priority >= 1", name="ck_study_tasks_priority"),
        CheckConstraint("estimated_hours > 0", name="ck_study_tasks_estimated_hours"),
        CheckConstraint(
            "status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED')",
            name="ck_study_tasks_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    study_plan_id = Column(
        Integer,
        ForeignKey("study_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day_number = Column(Integer, nullable=False)
    topic = Column(String, nullable=False)
    priority = Column(Integer, nullable=False)
    estimated_hours = Column(Float, nullable=False)
    status = Column(
        String,
        nullable=False,
        default="PENDING",
        server_default="PENDING",
    )

    study_plan = relationship("StudyPlan", back_populates="tasks")


class StudentTopicPerformance(Base):
    __tablename__ = "student_topic_performance"
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "subject_id",
            "topic",
            name="uq_student_topic_performance_topic",
        ),
        CheckConstraint("attempts >= 0", name="ck_topic_performance_attempts"),
        CheckConstraint(
            "correct_answers >= 0",
            name="ck_topic_performance_correct_answers",
        ),
        CheckConstraint(
            "incorrect_answers >= 0",
            name="ck_topic_performance_incorrect_answers",
        ),
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 100",
            name="ck_topic_performance_confidence",
        ),
        CheckConstraint(
            "mastery_score >= 0 AND mastery_score <= 100",
            name="ck_topic_performance_mastery",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_id = Column(
        Integer,
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic = Column(String, nullable=False)
    attempts = Column(Integer, nullable=False, default=0, server_default="0")
    correct_answers = Column(Integer, nullable=False, default=0, server_default="0")
    incorrect_answers = Column(Integer, nullable=False, default=0, server_default="0")
    confidence_score = Column(Float, nullable=False, default=50, server_default="50")
    mastery_score = Column(Float, nullable=False, default=0, server_default="0")
    last_practiced_at = Column(DateTime, nullable=True)

    student = relationship("Student", back_populates="topic_performances")
    subject = relationship("Subject", back_populates="topic_performances")


class PracticeSession(Base):
    __tablename__ = "practice_sessions"
    __table_args__ = (
        CheckConstraint(
            "total_questions >= 0",
            name="ck_practice_sessions_total_questions",
        ),
        CheckConstraint(
            "correct_answers >= 0",
            name="ck_practice_sessions_correct_answers",
        ),
        CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 100)",
            name="ck_practice_sessions_score",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_id = Column(
        Integer,
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    score = Column(Float, nullable=True)
    total_questions = Column(Integer, nullable=False, default=0, server_default="0")
    correct_answers = Column(Integer, nullable=False, default=0, server_default="0")

    student = relationship("Student", back_populates="practice_sessions")
    subject = relationship("Subject", back_populates="practice_sessions")
    attempts = relationship(
        "PracticeQuestionAttempt",
        back_populates="practice_session",
        cascade="all, delete-orphan",
        order_by="PracticeQuestionAttempt.id",
    )


class PracticeQuestionAttempt(Base):
    __tablename__ = "practice_question_attempts"
    __table_args__ = (
        CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 100)",
            name="ck_practice_attempt_score",
        ),
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 100",
            name="ck_practice_attempt_confidence",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    practice_session_id = Column(
        Integer,
        ForeignKey("practice_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_text = Column(String, nullable=False)
    topic = Column(String, nullable=True, index=True)
    difficulty = Column(String, nullable=False)
    expected_answer = Column(String, nullable=True)
    student_answer = Column(String, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    score = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=False, default=50, server_default="50")

    practice_session = relationship("PracticeSession", back_populates="attempts")


class StudentProfile(Base):
    __tablename__ = "student_profiles"
    __table_args__ = (
        UniqueConstraint("student_id", name="uq_student_profiles_student"),
        CheckConstraint(
            "preferred_study_hours IS NULL OR preferred_study_hours > 0",
            name="ck_student_profiles_preferred_study_hours",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    preferred_study_hours = Column(Float, nullable=True)
    preferred_subjects = Column(JSON, nullable=False, default=list)
    current_goal = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    student = relationship("Student", back_populates="profile")


class StudentMemory(Base):
    __tablename__ = "student_memories"
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "memory_type",
            "memory_key",
            name="uq_student_memories_student_type_key",
        ),
        CheckConstraint(
            "memory_type IN ('STRENGTH', 'WEAKNESS', 'GOAL', 'HABIT', 'RECOMMENDATION', 'READINESS')",
            name="ck_student_memories_memory_type",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    memory_type = Column(String, nullable=False)
    memory_key = Column(String, nullable=False)
    memory_value = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    student = relationship("Student", back_populates="memories")


class ReadinessSnapshot(Base):
    __tablename__ = "readiness_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_id = Column(
        Integer,
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    readiness_score = Column(Integer, nullable=False)
    captured_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    student = relationship("Student", back_populates="readiness_snapshots")
    subject = relationship("Subject", back_populates="readiness_snapshots")


class Semester(Base):
    __tablename__ = "semesters"
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "semester_number",
            name="uq_semesters_student_number",
        ),
        CheckConstraint("semester_number > 0", name="ck_semesters_number_positive"),
        CheckConstraint("end_date >= start_date", name="ck_semesters_date_range"),
        CheckConstraint(
            "target_cgpa IS NULL OR target_cgpa > 0",
            name="ck_semesters_target_cgpa_positive",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'COMPLETED', 'ARCHIVED')",
            name="ck_semesters_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    semester_number = Column(Integer, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    target_cgpa = Column(Float, nullable=True)
    status = Column(String, nullable=False, default="ACTIVE", server_default="ACTIVE")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    student = relationship("Student", back_populates="semesters")
    subjects = relationship(
        "SemesterSubject",
        back_populates="semester",
        cascade="all, delete-orphan",
        order_by="SemesterSubject.id",
    )
    milestones = relationship(
        "SemesterMilestone",
        back_populates="semester",
        cascade="all, delete-orphan",
        order_by="SemesterMilestone.due_date, SemesterMilestone.id",
    )


class SemesterSubject(Base):
    __tablename__ = "semester_subjects"
    __table_args__ = (
        UniqueConstraint(
            "semester_id",
            "subject_id",
            name="uq_semester_subjects_semester_subject",
        ),
        CheckConstraint(
            "target_score IS NULL OR (target_score >= 0 AND target_score <= 100)",
            name="ck_semester_subjects_target_score",
        ),
        CheckConstraint(
            "current_readiness >= 0 AND current_readiness <= 100",
            name="ck_semester_subjects_current_readiness",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    semester_id = Column(
        Integer,
        ForeignKey("semesters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_id = Column(
        Integer,
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_score = Column(Float, nullable=True)
    current_readiness = Column(Integer, nullable=False, default=0, server_default="0")

    semester = relationship("Semester", back_populates="subjects")
    subject = relationship("Subject", back_populates="semester_links")


class SemesterMilestone(Base):
    __tablename__ = "semester_milestones"
    __table_args__ = (
        CheckConstraint(
            "completed IN (true, false)",
            name="ck_semester_milestones_completed",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    semester_id = Column(
        Integer,
        ForeignKey("semesters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(Date, nullable=False, index=True)
    completed = Column(Boolean, nullable=False, default=False, server_default="0")
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    semester = relationship("Semester", back_populates="milestones")