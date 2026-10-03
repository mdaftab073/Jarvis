"""Service layer for Phase 15: Student Digital Twin & Academic OS"""

from datetime import timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models import (
    AttendanceRecord,
    DeadlineItem,
    DigitalTwinSnapshot,
    GradeRecord,
    StudentAcademicProfile,
    StudyActivityLog,
    TopicMastery,
)
from app.schemas.digital_twin import (
    AttendanceRecordCreate,
    AttendanceRecordUpdate,
    DeadlineItemCreate,
    DeadlineItemUpdate,
    GradeRecordCreate,
    GradeRecordUpdate,
    StudentAcademicProfileCreate,
    StudentAcademicProfileUpdate,
    StudyActivityLogCreate,
)
from app.services.ownership_service import student_id_for_profile, student_owned_query
from app.services.attendance_service import (
    list_attendance as list_student_attendance,
    update_attendance_record,
    upsert_attendance as upsert_student_attendance,
)
from app.services.grade_service import (
    add_grade as add_student_grade,
    delete_grade as delete_student_grade,
    list_grades as list_student_grades,
    update_grade as update_student_grade,
)
from app.services.deadline_service import (
    create_deadline as create_student_deadline,
    delete_deadline as delete_student_deadline,
    list_deadlines as list_student_deadlines,
    update_deadline as update_student_deadline,
)
from app.services.time_service import utc_now_naive


# ── Helpers ───────────────────────────────────────────────────────────────────

def _calc_attendance_pct(attended: int, total: int) -> Optional[float]:
    if total == 0:
        return None
    return round((attended / total) * 100, 2)


def _compute_risk(profile: StudentAcademicProfile, attendance: List[AttendanceRecord]) -> str:
    """Simple rule-based risk scoring."""
    risk_score = 0

    if profile.academic_status in ("PROBATION", "SUSPENDED"):
        risk_score += 40

    if profile.current_spi is not None and profile.current_spi < 5.0:
        risk_score += 30
    elif profile.current_spi is not None and profile.current_spi < 6.0:
        risk_score += 15

    low_attendance = [
        a for a in attendance
        if a.attendance_percentage is not None and a.attendance_percentage < 75
    ]
    risk_score += min(len(low_attendance) * 10, 30)

    if risk_score >= 50:
        return "CRITICAL"
    elif risk_score >= 30:
        return "HIGH"
    elif risk_score >= 15:
        return "MEDIUM"
    return "LOW"


def _compute_study_streak(logs: List[StudyActivityLog]) -> int:
    if not logs:
        return 0
    sorted_dates = sorted({log.logged_at.date() for log in logs}, reverse=True)
    streak = 0
    expected = utc_now_naive().date()
    for d in sorted_dates:
        if d == expected or d == expected - timedelta(days=1):
            streak += 1
            expected = d - timedelta(days=1)
        else:
            break
    return streak


# ── Academic Profile CRUD ─────────────────────────────────────────────────────

def get_or_create_academic_profile(
    db: Session, student_id: int, data: Optional[StudentAcademicProfileCreate] = None
) -> StudentAcademicProfile:
    profile = (
        db.query(StudentAcademicProfile)
        .filter(StudentAcademicProfile.student_id == student_id)
        .first()
    )
    if profile:
        return profile
    profile = StudentAcademicProfile(
        student_id=student_id,
        **(data.model_dump(exclude_none=True) if data else {}),
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def get_academic_profile(db: Session, student_id: int) -> Optional[StudentAcademicProfile]:
    return (
        db.query(StudentAcademicProfile)
        .filter(StudentAcademicProfile.student_id == student_id)
        .first()
    )


def update_academic_profile(
    db: Session, student_id: int, data: StudentAcademicProfileUpdate
) -> Optional[StudentAcademicProfile]:
    profile = get_academic_profile(db, student_id)
    if not profile:
        return None
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(profile, k, v)
    profile.updated_at = utc_now_naive()
    db.commit()
    db.refresh(profile)
    return profile


# ── Attendance ────────────────────────────────────────────────────────────────

def upsert_attendance(
    db: Session, profile_id: int, data: AttendanceRecordCreate
) -> AttendanceRecord:
    return upsert_student_attendance(
        db,
        student_id_for_profile(db, profile_id),
        data.subject_id,
        data.attended_classes,
        data.total_classes,
    )


def get_attendance(db: Session, profile_id: int) -> List[AttendanceRecord]:
    return list_student_attendance(db, student_id_for_profile(db, profile_id))


def update_attendance(
    db: Session, record_id: int, data: AttendanceRecordUpdate
) -> Optional[AttendanceRecord]:
    return update_attendance_record(db, record_id, data.model_dump(exclude_none=True))


# ── Grades ────────────────────────────────────────────────────────────────────

def add_grade_record(db: Session, profile_id: int, data: GradeRecordCreate) -> GradeRecord:
    return add_student_grade(
        db,
        student_id_for_profile(db, profile_id),
        data.model_dump(),
    )


def get_grades(db: Session, profile_id: int) -> List[GradeRecord]:
    return list_student_grades(db, student_id_for_profile(db, profile_id))


def update_grade_record(
    db: Session, record_id: int, data: GradeRecordUpdate
) -> Optional[GradeRecord]:
    return update_student_grade(db, record_id, data.model_dump(exclude_none=True))


def delete_grade_record(db: Session, record_id: int) -> bool:
    return delete_student_grade(db, record_id)


# ── Deadlines ─────────────────────────────────────────────────────────────────

def create_deadline(db: Session, profile_id: int, data: DeadlineItemCreate) -> DeadlineItem:
    fields = data.model_dump()
    fields["type"] = fields.pop("item_type")
    return create_student_deadline(db, student_id_for_profile(db, profile_id), fields)


def get_deadlines(
    db: Session, profile_id: int, include_completed: bool = False
) -> List[DeadlineItem]:
    return list_student_deadlines(
        db, student_id_for_profile(db, profile_id), include_completed
    )


def update_deadline(
    db: Session, item_id: int, data: DeadlineItemUpdate
) -> Optional[DeadlineItem]:
    fields = data.model_dump(exclude_none=True, by_alias=True)
    fields = {"completed" if key == "is_completed" else "type" if key == "item_type" else key: value for key, value in fields.items()}
    return update_student_deadline(db, item_id, fields)


def delete_deadline(db: Session, item_id: int) -> bool:
    return delete_student_deadline(db, item_id)


# ── Study Activity ────────────────────────────────────────────────────────────

def log_study_activity(
    db: Session, profile_id: int, data: StudyActivityLogCreate
) -> StudyActivityLog:
    log_data = data.model_dump()
    if not log_data.get("logged_at"):
        log_data["logged_at"] = utc_now_naive()
        log = StudyActivityLog(
            student_id=student_id_for_profile(db, profile_id),
            academic_profile_id=profile_id,
            **log_data,
        )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_study_activity(
    db: Session, profile_id: int, days: int = 7
) -> List[StudyActivityLog]:
    since = utc_now_naive() - timedelta(days=days)
    student_id = student_id_for_profile(db, profile_id)
    return (
        student_owned_query(db, StudyActivityLog, student_id)
        .filter(
            StudyActivityLog.academic_profile_id == profile_id,
            StudyActivityLog.logged_at >= since,
        )
        .order_by(StudyActivityLog.logged_at.desc())
        .all()
    )


# ── Digital Twin Snapshot ─────────────────────────────────────────────────────

def build_and_save_snapshot(db: Session, profile_id: int) -> DigitalTwinSnapshot:
    profile = (
        db.query(StudentAcademicProfile)
        .filter(StudentAcademicProfile.id == profile_id)
        .first()
    )
    if not profile:
        raise ValueError(f"Academic profile {profile_id} not found")

    attendance_records = get_attendance(db, profile_id)
    grade_records = get_grades(db, profile_id)
    deadlines = get_deadlines(db, profile_id, include_completed=False)
    activity_logs = get_study_activity(db, profile_id, days=7)

    # Mastery summary from topic_mastery table
    masteries = (
        db.query(TopicMastery)
        .filter(TopicMastery.student_id == profile.student_id)
        .all()
    )
    mastery_summary: Dict[str, Any] = {}
    for m in masteries:
        key = str(m.topic_id)
        mastery_summary[key] = m.mastery_score

    attendance_summary: Dict[str, Any] = {
        str(a.subject_id): a.attendance_percentage for a in attendance_records
    }

    grade_summary: Dict[str, Any] = {}
    for g in grade_records:
        subj = str(g.subject_id)
        if subj not in grade_summary:
            grade_summary[subj] = {}
        if g.grade_type == "FINAL":
            grade_summary[subj].setdefault("final_grades", []).append(
                {
                    "semester": g.semester,
                    "grade": g.grade,
                    "credits": g.credits,
                    "grade_points": g.grade_points,
                }
            )
        else:
            grade_summary[subj].setdefault("components", {})[g.component_type] = {
                "obtained": g.obtained_marks,
                "max": g.max_marks,
            }

    upcoming = [
        {
            "id": d.id,
            "title": d.title,
            "item_type": d.item_type,
            "due_date": d.due_date.isoformat(),
            "priority": d.priority,
            "subject_id": d.subject_id,
        }
        for d in deadlines[:10]
    ]

    week_minutes = sum(a.duration_minutes for a in activity_logs)
    streak = _compute_study_streak(activity_logs)
    risk = _compute_risk(profile, attendance_records)

    # Overall readiness: weighted average of mastery + attendance
    readiness_scores = []
    if mastery_summary:
        avg_mastery = sum(mastery_summary.values()) / len(mastery_summary)
        readiness_scores.append(avg_mastery)
    if attendance_summary:
        valid_pcts = [v for v in attendance_summary.values() if v is not None]
        if valid_pcts:
            avg_attendance = sum(valid_pcts) / len(valid_pcts)
            readiness_scores.append(avg_attendance)

    overall_readiness = (
        round(sum(readiness_scores) / len(readiness_scores), 1) if readiness_scores else None
    )

    recommendations = _generate_recommendations(
        profile, attendance_records, masteries, deadlines, streak
    )

    snapshot = DigitalTwinSnapshot(
        student_id=profile.student_id,
        academic_profile_id=profile_id,
        overall_readiness=overall_readiness,
        risk_level=risk,
        mastery_summary=mastery_summary,
        attendance_summary=attendance_summary,
        grade_summary=grade_summary,
        upcoming_deadlines=upcoming,
        ai_recommendations=recommendations,
        study_streak_days=streak,
        total_study_minutes_week=week_minutes,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def get_latest_snapshot(db: Session, profile_id: int) -> Optional[DigitalTwinSnapshot]:
    student_id = student_id_for_profile(db, profile_id)
    return (
        student_owned_query(db, DigitalTwinSnapshot, student_id)
        .filter(DigitalTwinSnapshot.academic_profile_id == profile_id)
        .order_by(DigitalTwinSnapshot.captured_at.desc())
        .first()
    )


def get_snapshot_history(
    db: Session, profile_id: int, limit: int = 30
) -> List[DigitalTwinSnapshot]:
    student_id = student_id_for_profile(db, profile_id)
    return (
        student_owned_query(db, DigitalTwinSnapshot, student_id)
        .filter(DigitalTwinSnapshot.academic_profile_id == profile_id)
        .order_by(DigitalTwinSnapshot.captured_at.desc())
        .limit(limit)
        .all()
    )


def _generate_recommendations(
    profile: StudentAcademicProfile,
    attendance: List[AttendanceRecord],
    masteries: List[TopicMastery],
    deadlines: List[DeadlineItem],
    streak: int,
) -> List[Dict[str, Any]]:
    recs = []

    # Attendance warnings
    low_att = [
        a for a in attendance
        if a.attendance_percentage is not None and a.attendance_percentage < 75
    ]
    for a in low_att[:3]:
        recs.append({
            "type": "ATTENDANCE_WARNING",
            "priority": "HIGH",
            "message": f"Attendance for subject {a.subject_id} is {a.attendance_percentage:.1f}% — below 75% threshold. Attend upcoming classes.",
            "subject_id": a.subject_id,
        })

    # Low mastery
    weak_topics = sorted(
        [m for m in masteries if m.mastery_score < 50],
        key=lambda x: x.mastery_score,
    )[:3]
    for m in weak_topics:
        recs.append({
            "type": "MASTERY_IMPROVEMENT",
            "priority": "MEDIUM",
            "message": f"Topic {m.topic_id} has low mastery ({m.mastery_score:.1f}%). Review flashcards and attempt practice quizzes.",
            "topic_id": m.topic_id,
        })

    # Upcoming deadlines within 3 days
    now = utc_now_naive()
    soon = [d for d in deadlines if (d.due_date - now).days <= 3]
    for d in soon[:3]:
        days_remaining = (d.due_date - now).days
        recs.append({
            "type": "DEADLINE_ALERT",
            "priority": "CRITICAL" if days_remaining <= 1 else "HIGH",
            "message": f"'{d.title}' is due in {max(0, days_remaining)} day(s). Prioritize completion.",
            "deadline_id": d.id,
        })

    # Study streak encouragement
    if streak == 0:
        recs.append({
            "type": "STUDY_HABIT",
            "priority": "MEDIUM",
            "message": "Start a study session today to build your streak and maintain momentum.",
        })
    elif streak >= 7:
        recs.append({
            "type": "STUDY_HABIT",
            "priority": "LOW",
            "message": f"Excellent! {streak}-day study streak. Keep it up!",
        })

    return recs


def get_full_digital_twin(db: Session, student_id: int) -> Dict[str, Any]:
    profile = get_academic_profile(db, student_id)
    if not profile:
        return {}

    attendance = get_attendance(db, profile.id)
    grades = get_grades(db, profile.id)
    deadlines = get_deadlines(db, profile.id)
    activity = get_study_activity(db, profile.id, days=7)
    snapshot = get_latest_snapshot(db, profile.id)

    # Calculate insights
    avg_attendance = None
    if attendance:
        pcts = [a.attendance_percentage for a in attendance if a.attendance_percentage is not None]
        avg_attendance = round(sum(pcts) / len(pcts), 1) if pcts else None

    total_study_hours_week = sum(a.duration_minutes for a in activity) / 60

    insights = {
        "average_attendance_pct": avg_attendance,
        "total_study_hours_this_week": round(total_study_hours_week, 1),
        "study_streak_days": _compute_study_streak(activity),
        "upcoming_deadline_count": len(deadlines),
        "risk_level": snapshot.risk_level if snapshot else "UNKNOWN",
        "overall_readiness": snapshot.overall_readiness if snapshot else None,
    }

    return {
        "academic_profile": profile,
        "attendance": attendance,
        "grades": grades,
        "upcoming_deadlines": deadlines,
        "recent_activity": activity,
        "latest_snapshot": snapshot,
        "insights": insights,
    }
