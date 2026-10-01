"""Pydantic schemas for Phase 15: Student Digital Twin & Academic OS"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, validator


# ── StudentAcademicProfile ────────────────────────────────────────────────────

class StudentAcademicProfileCreate(BaseModel):
    enrollment_number: Optional[str] = None
    branch: Optional[str] = None
    department: Optional[str] = None
    semester: Optional[int] = Field(None, ge=1, le=12)
    section: Optional[str] = None
    batch_year: Optional[int] = Field(None, ge=2000, le=2100)
    current_cpi: Optional[float] = Field(None, ge=0, le=10)
    current_spi: Optional[float] = Field(None, ge=0, le=10)
    total_credits: Optional[int] = Field(None, ge=0)
    earned_credits: Optional[int] = Field(None, ge=0)
    academic_status: str = Field("ACTIVE", pattern="^(ACTIVE|PROBATION|GRADUATED|SUSPENDED|DROPOUT)$")


class StudentAcademicProfileUpdate(BaseModel):
    enrollment_number: Optional[str] = None
    branch: Optional[str] = None
    department: Optional[str] = None
    semester: Optional[int] = Field(None, ge=1, le=12)
    section: Optional[str] = None
    batch_year: Optional[int] = Field(None, ge=2000, le=2100)
    current_cpi: Optional[float] = Field(None, ge=0, le=10)
    current_spi: Optional[float] = Field(None, ge=0, le=10)
    total_credits: Optional[int] = Field(None, ge=0)
    earned_credits: Optional[int] = Field(None, ge=0)
    academic_status: Optional[str] = Field(None, pattern="^(ACTIVE|PROBATION|GRADUATED|SUSPENDED|DROPOUT)$")


class StudentAcademicProfileResponse(BaseModel):
    id: int
    student_id: int
    enrollment_number: Optional[str]
    branch: Optional[str]
    department: Optional[str]
    semester: Optional[int]
    section: Optional[str]
    batch_year: Optional[int]
    current_cpi: Optional[float]
    current_spi: Optional[float]
    total_credits: Optional[int]
    earned_credits: Optional[int]
    academic_status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── AttendanceRecord ──────────────────────────────────────────────────────────

class AttendanceRecordCreate(BaseModel):
    subject_id: int
    attended_classes: int = Field(0, ge=0)
    total_classes: int = Field(0, ge=0)

    @validator("attended_classes")
    def attended_not_exceed_total(cls, v, values):
        if "total_classes" in values and v > values["total_classes"]:
            raise ValueError("attended_classes cannot exceed total_classes")
        return v


class AttendanceRecordUpdate(BaseModel):
    attended_classes: Optional[int] = Field(None, ge=0)
    total_classes: Optional[int] = Field(None, ge=0)


class AttendanceRecordResponse(BaseModel):
    id: int
    academic_profile_id: int
    subject_id: int
    attended_classes: int
    total_classes: int
    attendance_percentage: Optional[float]
    last_updated: datetime

    class Config:
        from_attributes = True


# ── GradeRecord ───────────────────────────────────────────────────────────────

class GradeRecordCreate(BaseModel):
    subject_id: int
    component_type: str = Field(..., pattern="^(CT1|CT2|CT3|ASSIGNMENT|LAB|END_SEM|MID_SEM|VIVA|PROJECT|OTHER)$")
    obtained_marks: Optional[float] = Field(None, ge=0)
    max_marks: float = Field(100, gt=0)
    grade_letter: Optional[str] = None


class GradeRecordUpdate(BaseModel):
    obtained_marks: Optional[float] = Field(None, ge=0)
    max_marks: Optional[float] = Field(None, gt=0)
    grade_letter: Optional[str] = None


class GradeRecordResponse(BaseModel):
    id: int
    academic_profile_id: int
    subject_id: int
    component_type: str
    obtained_marks: Optional[float]
    max_marks: float
    grade_letter: Optional[str]
    recorded_at: datetime

    class Config:
        from_attributes = True


# ── DeadlineItem ──────────────────────────────────────────────────────────────

class DeadlineItemCreate(BaseModel):
    subject_id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    item_type: str = Field("OTHER", pattern="^(EXAM|ASSIGNMENT|PROJECT|LAB_SUBMISSION|QUIZ|PRESENTATION|OTHER)$")
    due_date: datetime
    priority: str = Field("MEDIUM", pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")


class DeadlineItemUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    item_type: Optional[str] = Field(None, pattern="^(EXAM|ASSIGNMENT|PROJECT|LAB_SUBMISSION|QUIZ|PRESENTATION|OTHER)$")
    due_date: Optional[datetime] = None
    priority: Optional[str] = Field(None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    is_completed: Optional[bool] = None


class DeadlineItemResponse(BaseModel):
    id: int
    academic_profile_id: int
    subject_id: Optional[int]
    title: str
    description: Optional[str]
    item_type: str
    due_date: datetime
    priority: str
    is_completed: bool
    completed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ── StudyActivityLog ──────────────────────────────────────────────────────────

class StudyActivityLogCreate(BaseModel):
    subject_id: Optional[int] = None
    activity_type: str = Field(..., pattern="^(READING|FLASHCARD|QUIZ|PROBLEM_SOLVING|VIDEO|REVISION|GROUP_STUDY|OTHER)$")
    duration_minutes: float = Field(0, ge=0)
    topics_covered: Optional[List[str]] = None
    productivity_score: Optional[float] = Field(None, ge=0, le=100)
    notes: Optional[str] = None
    logged_at: Optional[datetime] = None


class StudyActivityLogResponse(BaseModel):
    id: int
    academic_profile_id: int
    subject_id: Optional[int]
    activity_type: str
    duration_minutes: float
    topics_covered: Optional[List[str]]
    productivity_score: Optional[float]
    notes: Optional[str]
    logged_at: datetime

    class Config:
        from_attributes = True


# ── DigitalTwinSnapshot ───────────────────────────────────────────────────────

class DigitalTwinSnapshotResponse(BaseModel):
    id: int
    academic_profile_id: int
    overall_readiness: Optional[float]
    risk_level: str
    mastery_summary: Optional[Dict[str, Any]]
    attendance_summary: Optional[Dict[str, Any]]
    grade_summary: Optional[Dict[str, Any]]
    upcoming_deadlines: Optional[List[Dict[str, Any]]]
    ai_recommendations: Optional[List[Dict[str, Any]]]
    study_streak_days: int
    total_study_minutes_week: float
    captured_at: datetime

    class Config:
        from_attributes = True


# ── Full Digital Twin (composite) ─────────────────────────────────────────────

class DigitalTwinFull(BaseModel):
    academic_profile: StudentAcademicProfileResponse
    attendance: List[AttendanceRecordResponse]
    grades: List[GradeRecordResponse]
    upcoming_deadlines: List[DeadlineItemResponse]
    recent_activity: List[StudyActivityLogResponse]
    latest_snapshot: Optional[DigitalTwinSnapshotResponse]
    insights: Dict[str, Any]

    class Config:
        from_attributes = True
