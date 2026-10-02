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
from sqlalchemy.orm import relationship, synonym
from sqlalchemy import CheckConstraint, Float
from sqlalchemy import Date
from sqlalchemy import Boolean, UniqueConstraint
from sqlalchemy import event
from sqlalchemy.orm import Session as OrmSession

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
    academic_profile = relationship(
        "StudentAcademicProfile",
        back_populates="student",
        cascade="all, delete-orphan",
        uselist=False,
    )
    notifications = relationship("StudentNotification", back_populates="student", cascade="all, delete-orphan")
    calendar_events = relationship("CalendarEvent", back_populates="student", cascade="all, delete-orphan")
    study_blocks = relationship("StudyBlock", back_populates="student", cascade="all, delete-orphan")
    reminders = relationship("Reminder", back_populates="student", cascade="all, delete-orphan")
    goals = relationship("StudentGoal", back_populates="student", cascade="all, delete-orphan")
    preferences = relationship("StudentPreference", back_populates="student", cascade="all, delete-orphan", uselist=False)
    habits = relationship("StudentHabit", back_populates="student", cascade="all, delete-orphan")
    goal_milestones = relationship("GoalMilestone", back_populates="student", cascade="all, delete-orphan")
    goal_progress = relationship("GoalProgress", back_populates="student", cascade="all, delete-orphan")
    habit_records = relationship("Habit", back_populates="student", cascade="all, delete-orphan")
    habit_logs = relationship("HabitLog", back_populates="student", cascade="all, delete-orphan")
    habit_streaks = relationship("HabitStreak", back_populates="student", cascade="all, delete-orphan")
    connectors = relationship("StudentConnector", back_populates="student", cascade="all, delete-orphan")
    sync_jobs = relationship("SyncJob", back_populates="student", cascade="all, delete-orphan")
    sync_history = relationship("SyncHistory", back_populates="student", cascade="all, delete-orphan")
    mis_profile = relationship(
        "MISStudentProfile",
        back_populates="student",
        cascade="all, delete-orphan",
        uselist=False,
    )
    chat_sessions = relationship(
        "ChatSession",
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


# ── Phase 15: Student Digital Twin & Academic Operating System ────────────────

class StudentAcademicProfile(Base):
    """Core academic identity record for each student."""
    __tablename__ = "student_academic_profiles"
    __table_args__ = (
        UniqueConstraint("student_id", name="uq_student_academic_profiles_student"),
        CheckConstraint(
            "academic_status IN ('ACTIVE', 'PROBATION', 'GRADUATED', 'SUSPENDED', 'DROPOUT')",
            name="ck_academic_profiles_status",
        ),
        CheckConstraint(
            "current_cpi IS NULL OR (current_cpi >= 0 AND current_cpi <= 10)",
            name="ck_academic_profiles_cpi",
        ),
        CheckConstraint(
            "current_spi IS NULL OR (current_spi >= 0 AND current_spi <= 10)",
            name="ck_academic_profiles_spi",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(
        Integer, ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    enrollment_number = Column(String(50), nullable=True, index=True)
    branch = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)
    semester = Column(Integer, nullable=True)
    section = Column(String(20), nullable=True)
    batch_year = Column(Integer, nullable=True)
    current_cpi = Column(Float, nullable=True)
    current_spi = Column(Float, nullable=True)
    total_credits = Column(Integer, nullable=True, default=0)
    earned_credits = Column(Integer, nullable=True, default=0)
    academic_status = Column(String(20), nullable=False, default="ACTIVE", server_default="ACTIVE")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    student = relationship("Student", back_populates="academic_profile")
    attendance_records = relationship(
        "AttendanceRecord", back_populates="academic_profile", cascade="all, delete-orphan",
    )
    grade_records = relationship(
        "GradeRecord", back_populates="academic_profile", cascade="all, delete-orphan",
    )
    deadline_items = relationship(
        "AcademicDeadline", back_populates="academic_profile", cascade="all, delete-orphan",
    )
    study_activity_logs = relationship(
        "StudyActivityLog", back_populates="academic_profile", cascade="all, delete-orphan",
    )
    digital_twin_snapshots = relationship(
        "DigitalTwinSnapshot", back_populates="academic_profile", cascade="all, delete-orphan",
        order_by="DigitalTwinSnapshot.captured_at",
    )


class AttendanceRecord(Base):
    """Per-subject attendance tracking for the digital twin."""
    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint(
            "academic_profile_id", "subject_id",
            name="uq_attendance_records_profile_subject",
        ),
        CheckConstraint("attended_classes >= 0", name="ck_attendance_attended_nonneg"),
        CheckConstraint("total_classes >= 0", name="ck_attendance_total_nonneg"),
        CheckConstraint(
            "attendance_percentage IS NULL OR (attendance_percentage >= 0 AND attendance_percentage <= 100)",
            name="ck_attendance_percentage",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_profile_id = Column(
        Integer, ForeignKey("student_academic_profiles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    subject_id = Column(
        Integer, ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    attended_classes = Column(Integer, nullable=False, default=0, server_default="0")
    total_classes = Column(Integer, nullable=False, default=0, server_default="0")
    attendance_percentage = Column(Float, nullable=True)
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    academic_profile = relationship("StudentAcademicProfile", back_populates="attendance_records")
    student = relationship("Student")
    subject = relationship("Subject")


class GradeRecord(Base):
    """Component marks and classified final course grades."""
    __tablename__ = "grade_records"
    __table_args__ = (
        CheckConstraint(
            "component_type IN ('CT1', 'CT2', 'CT3', 'ASSIGNMENT', 'LAB', 'END_SEM', 'MID_SEM', 'VIVA', 'PROJECT', 'OTHER')",
            name="ck_grade_records_component_type",
        ),
        CheckConstraint(
            "obtained_marks IS NULL OR obtained_marks >= 0",
            name="ck_grade_records_obtained_marks_nonneg",
        ),
        CheckConstraint(
            "max_marks > 0",
            name="ck_grade_records_max_marks_pos",
        ),
        CheckConstraint("grade_type IN ('COMPONENT', 'FINAL')", name="ck_grade_records_grade_type"),
        CheckConstraint("credits IS NULL OR credits >= 0", name="ck_grade_records_credits_nonneg"),
        CheckConstraint("semester IS NULL OR semester >= 1", name="ck_grade_records_semester_positive"),
        CheckConstraint("grade_points IS NULL OR (grade_points >= 0 AND grade_points <= 10)", name="ck_grade_records_grade_points_range"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_profile_id = Column(
        Integer, ForeignKey("student_academic_profiles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    subject_id = Column(
        Integer, ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    component_type = Column(String(20), nullable=False, default="OTHER", server_default="OTHER")
    obtained_marks = Column(Float, nullable=True)
    max_marks = Column(Float, nullable=False, default=100)
    grade = Column("grade_letter", String(5), nullable=True)
    grade_type = Column(String(10), nullable=False, default="COMPONENT", server_default="COMPONENT")
    semester = Column(Integer, nullable=True)
    credits = Column(Float, nullable=True)
    grade_points = Column(Float, nullable=True)
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    academic_profile = relationship("StudentAcademicProfile", back_populates="grade_records")
    student = relationship("Student")
    subject = relationship("Subject")
    grade_letter = synonym("grade")


class AcademicDeadline(Base):
    """Upcoming deadlines, exams, submissions tracked per student."""
    __tablename__ = "deadline_items"
    __table_args__ = (
        CheckConstraint(
            "item_type IN ('EXAM', 'ASSIGNMENT', 'PROJECT', 'LAB_SUBMISSION', 'QUIZ', 'PRESENTATION', 'OTHER')",
            name="ck_deadline_items_type",
        ),
        CheckConstraint(
            "priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_deadline_items_priority",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_profile_id = Column(
        Integer, ForeignKey("student_academic_profiles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    subject_id = Column(
        Integer, ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    type = Column("item_type", String(30), nullable=False, default="OTHER")
    due_date = Column(DateTime, nullable=False, index=True)
    priority = Column(String(10), nullable=False, default="MEDIUM")
    completed = Column("is_completed", Boolean, nullable=False, default=False, server_default="0")
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    academic_profile = relationship("StudentAcademicProfile", back_populates="deadline_items")
    student = relationship("Student")
    subject = relationship("Subject")
    item_type = synonym("type")
    is_completed = synonym("completed")


class StudentNotification(Base):
    __tablename__ = "student_notifications"
    __table_args__ = (CheckConstraint("notification_type IN ('INFO', 'SUCCESS', 'WARNING', 'CRITICAL', 'REMINDER')", name="ck_student_notifications_type"),)

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(20), nullable=False, default="INFO", server_default="INFO")
    read = Column(Boolean, nullable=False, default=False, server_default="0")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    student = relationship("Student", back_populates="notifications")


class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    __table_args__ = (CheckConstraint("end_time > start_time", name="ck_calendar_events_time_order"),)

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False)
    event_type = Column(String(30), nullable=False, default="OTHER", server_default="OTHER")
    student = relationship("Student", back_populates="calendar_events")


class StudyBlock(Base):
    __tablename__ = "study_blocks"
    __table_args__ = (
        CheckConstraint("end_time > start_time", name="ck_study_blocks_time_order"),
        CheckConstraint("planned_duration >= 0", name="ck_study_blocks_duration_nonneg"),
        CheckConstraint("block_type IN ('STUDY', 'REVISION', 'ATTENDANCE_RECOVERY', 'DEADLINE_PREP', 'GOAL')", name="ck_study_blocks_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=True, index=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False)
    planned_duration = Column(Integer, nullable=False)
    title = Column(String(255), nullable=True)
    block_type = Column(String(30), nullable=False, default="STUDY", server_default="STUDY")
    completed = Column(Boolean, nullable=False, default=False, server_default="0")
    student = relationship("Student", back_populates="study_blocks")
    subject = relationship("Subject")


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    trigger_time = Column(DateTime, nullable=False, index=True)
    completed = Column(Boolean, nullable=False, default=False, server_default="0")
    student = relationship("Student", back_populates="reminders")


class StudentGoal(Base):
    __tablename__ = "student_goals"
    __table_args__ = (
        CheckConstraint("goal_type IN ('SEMESTER', 'CPI', 'ATTENDANCE', 'PLACEMENT', 'STUDY_HOURS')", name="ck_student_goals_type"),
        CheckConstraint("target_value IS NULL OR target_value >= 0", name="ck_student_goals_target_nonneg"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    goal_type = Column(String(20), nullable=False, default="STUDY_HOURS", server_default="STUDY_HOURS")
    target_value = Column(Float, nullable=True)
    target_unit = Column(String(30), nullable=True)
    target_date = Column(Date, nullable=True)
    completed = Column(Boolean, nullable=False, default=False, server_default="0")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    student = relationship("Student", back_populates="goals")
    milestones = relationship("GoalMilestone", back_populates="goal", cascade="all, delete-orphan")
    progress_entries = relationship("GoalProgress", back_populates="goal", cascade="all, delete-orphan", order_by="GoalProgress.recorded_at")


class GoalMilestone(Base):
    __tablename__ = "goal_milestones"
    __table_args__ = (CheckConstraint("target_value IS NULL OR target_value >= 0", name="ck_goal_milestones_target_nonneg"),)

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    goal_id = Column(Integer, ForeignKey("student_goals.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    target_value = Column(Float, nullable=True)
    target_date = Column(Date, nullable=True)
    completed = Column(Boolean, nullable=False, default=False, server_default="0")
    completed_at = Column(DateTime, nullable=True)
    student = relationship("Student", back_populates="goal_milestones")
    goal = relationship("StudentGoal", back_populates="milestones")


class GoalProgress(Base):
    __tablename__ = "goal_progress"
    __table_args__ = (CheckConstraint("progress_value >= 0", name="ck_goal_progress_nonneg"),)

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    goal_id = Column(Integer, ForeignKey("student_goals.id", ondelete="CASCADE"), nullable=False, index=True)
    progress_value = Column(Float, nullable=False)
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    notes = Column(Text, nullable=True)
    student = relationship("Student", back_populates="goal_progress")
    goal = relationship("StudentGoal", back_populates="progress_entries")


class StudentPreference(Base):
    __tablename__ = "student_preferences"
    __table_args__ = (UniqueConstraint("student_id", name="uq_student_preferences_student"),)

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    preferred_study_time = Column(String(30), nullable=True)
    preferred_session_length = Column(Integer, nullable=True)
    study_style = Column(String(100), nullable=True)
    student = relationship("Student", back_populates="preferences")


class StudentHabit(Base):
    __tablename__ = "student_habits"
    __table_args__ = (CheckConstraint("streak >= 0", name="ck_student_habits_streak_nonneg"), CheckConstraint("completion_rate >= 0 AND completion_rate <= 100", name="ck_student_habits_completion_rate"))

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    habit_name = Column(String(120), nullable=False)
    streak = Column(Integer, nullable=False, default=0, server_default="0")
    completion_rate = Column(Float, nullable=False, default=0, server_default="0")
    student = relationship("Student", back_populates="habits")


class Habit(Base):
    __tablename__ = "habits"
    __table_args__ = (
        UniqueConstraint("student_id", "habit_name", "category", name="uq_habits_student_name_category"),
        CheckConstraint("category IN ('DAILY_STUDY', 'REVISION', 'PYQ_PRACTICE', 'ATTENDANCE_CHECK', 'ASSIGNMENT_COMPLETION', 'OTHER')", name="ck_habits_category"),
        CheckConstraint("target_per_week > 0 AND target_per_week <= 7", name="ck_habits_target_per_week"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    habit_name = Column(String(120), nullable=False)
    category = Column(String(30), nullable=False)
    target_per_week = Column(Integer, nullable=False, default=7, server_default="7")
    active = Column(Boolean, nullable=False, default=True, server_default="1")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    student = relationship("Student", back_populates="habit_records")
    logs = relationship("HabitLog", back_populates="habit", cascade="all, delete-orphan")
    streak = relationship("HabitStreak", back_populates="habit", cascade="all, delete-orphan", uselist=False)


class HabitLog(Base):
    __tablename__ = "habit_logs"
    __table_args__ = (
        UniqueConstraint("habit_id", "log_date", name="uq_habit_logs_habit_day"),
        CheckConstraint("duration_minutes IS NULL OR duration_minutes >= 0", name="ck_habit_logs_duration_nonneg"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    habit_id = Column(Integer, ForeignKey("habits.id", ondelete="CASCADE"), nullable=False, index=True)
    log_date = Column(Date, nullable=False, index=True)
    completed = Column(Boolean, nullable=False, default=True, server_default="1")
    duration_minutes = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    student = relationship("Student", back_populates="habit_logs")
    habit = relationship("Habit", back_populates="logs")


class HabitStreak(Base):
    __tablename__ = "habit_streaks"
    __table_args__ = (
        UniqueConstraint("habit_id", name="uq_habit_streaks_habit"),
        CheckConstraint("current_streak >= 0 AND longest_streak >= 0", name="ck_habit_streaks_nonneg"),
        CheckConstraint("completion_rate >= 0 AND completion_rate <= 100", name="ck_habit_streaks_completion_rate"),
        CheckConstraint("consistency_score >= 0 AND consistency_score <= 100", name="ck_habit_streaks_consistency_score"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    habit_id = Column(Integer, ForeignKey("habits.id", ondelete="CASCADE"), nullable=False, index=True)
    current_streak = Column(Integer, nullable=False, default=0, server_default="0")
    longest_streak = Column(Integer, nullable=False, default=0, server_default="0")
    completion_rate = Column(Float, nullable=False, default=0, server_default="0")
    consistency_score = Column(Float, nullable=False, default=0, server_default="0")
    last_completed_date = Column(Date, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    student = relationship("Student", back_populates="habit_streaks")
    habit = relationship("Habit", back_populates="streak")


class StudentConnector(Base):
    __tablename__ = "student_connectors"
    __table_args__ = (
        UniqueConstraint("student_id", "connector_type", name="uq_student_connectors_type"),
        CheckConstraint("status IN ('READY', 'SYNCING', 'ERROR', 'DISABLED')", name="ck_student_connectors_status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    connector_type = Column(String(60), nullable=False)
    endpoint_url = Column(String(500), nullable=False)
    encrypted_credentials = Column(Text, nullable=False)
    configuration = Column(JSON, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True, server_default="1")
    sync_interval_minutes = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, default="READY", server_default="READY")
    last_sync_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    student = relationship("Student", back_populates="connectors")
    jobs = relationship("SyncJob", back_populates="connector", cascade="all, delete-orphan")
    history = relationship("SyncHistory", back_populates="connector", cascade="all, delete-orphan")


class SyncJob(Base):
    __tablename__ = "sync_jobs"
    __table_args__ = (CheckConstraint("status IN ('QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED')", name="ck_sync_jobs_status"),)

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    connector_id = Column(Integer, ForeignKey("student_connectors.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="QUEUED", server_default="QUEUED")
    scheduled_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    error = Column(Text, nullable=True)
    student = relationship("Student", back_populates="sync_jobs")
    connector = relationship("StudentConnector", back_populates="jobs")


class SyncHistory(Base):
    __tablename__ = "sync_history"
    __table_args__ = (CheckConstraint("status IN ('SUCCEEDED', 'FAILED')", name="ck_sync_history_status"),)

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    connector_id = Column(Integer, ForeignKey("student_connectors.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), nullable=False)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=False)
    duration_seconds = Column(Float, nullable=False)
    records_processed = Column(Integer, nullable=False, default=0, server_default="0")
    summary = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    student = relationship("Student", back_populates="sync_history")
    connector = relationship("StudentConnector", back_populates="history")


# Backward-compatible class name for Phase 15 callers.
DeadlineItem = AcademicDeadline


class StudyActivityLog(Base):
    """Daily/session-level study activity log for the digital twin."""
    __tablename__ = "study_activity_logs"
    __table_args__ = (
        CheckConstraint(
            "activity_type IN ('READING', 'FLASHCARD', 'QUIZ', 'PROBLEM_SOLVING', 'VIDEO', 'REVISION', 'GROUP_STUDY', 'OTHER')",
            name="ck_study_activity_type",
        ),
        CheckConstraint("duration_minutes >= 0", name="ck_study_activity_duration_nonneg"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_profile_id = Column(
        Integer, ForeignKey("student_academic_profiles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    subject_id = Column(
        Integer, ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )
    activity_type = Column(String(30), nullable=False)
    duration_minutes = Column(Float, nullable=False, default=0)
    topics_covered = Column(JSON, nullable=True)
    productivity_score = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    logged_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    academic_profile = relationship("StudentAcademicProfile", back_populates="study_activity_logs")
    student = relationship("Student")
    subject = relationship("Subject")


class DigitalTwinSnapshot(Base):
    """Point-in-time snapshot of a student's complete academic state."""
    __tablename__ = "digital_twin_snapshots"
    __table_args__ = (
        CheckConstraint(
            "risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_snapshot_risk_level",
        ),
        CheckConstraint(
            "overall_readiness IS NULL OR (overall_readiness >= 0 AND overall_readiness <= 100)",
            name="ck_snapshot_overall_readiness",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_profile_id = Column(
        Integer, ForeignKey("student_academic_profiles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    overall_readiness = Column(Float, nullable=True)
    risk_level = Column(String(10), nullable=False, default="LOW")
    mastery_summary = Column(JSON, nullable=True)          # {subject_id: avg_mastery}
    attendance_summary = Column(JSON, nullable=True)       # {subject_id: pct}
    grade_summary = Column(JSON, nullable=True)            # {subject_id: {component: marks}}
    upcoming_deadlines = Column(JSON, nullable=True)       # list of deadline dicts
    ai_recommendations = Column(JSON, nullable=True)       # AI-generated recommendations
    study_streak_days = Column(Integer, nullable=False, default=0)
    total_study_minutes_week = Column(Float, nullable=False, default=0)
    captured_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    academic_profile = relationship("StudentAcademicProfile", back_populates="digital_twin_snapshots")
    student = relationship("Student")


# Phase 14 models import to resolve mapper relationship names
from app.models import (  # noqa: E402, F401
    Topic,
    FlashcardDeck,
    Flashcard,
    QuizSession,
    QuizQuestion,
    QuizAnswer,
    TopicMastery,
    LearningSession,
)


@event.listens_for(OrmSession, "before_flush")
def _synchronize_profile_owned_student_ids(session, _flush_context, _instances):
    profile_owned_models = (
        AttendanceRecord,
        GradeRecord,
        DeadlineItem,
        StudyActivityLog,
        DigitalTwinSnapshot,
    )
    for record in session.new.union(session.dirty):
        if not isinstance(record, profile_owned_models):
            continue
        profile = record.academic_profile
        if profile is None and record.academic_profile_id is not None:
            profile = session.get(StudentAcademicProfile, record.academic_profile_id)
        if profile is None:
            continue
        owner_id = profile.student_id
        if owner_id is None and profile.student is not None:
            record.student = profile.student
        elif record.student_id is None:
            record.student_id = owner_id
        elif owner_id is not None and record.student_id != owner_id:
            raise ValueError("student_id must match the owning academic profile")