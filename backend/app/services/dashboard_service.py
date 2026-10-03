from app.db.models import DigitalTwinSnapshot, GradeRecord, StudentAcademicProfile, StudentNotification, TopicMastery
from app.services.attendance_service import attendance_summary
from app.services.calendar_service import get_events, get_agenda, get_week_agenda
from app.services.deadline_service import serialize_deadline, upcoming_deadlines
from app.services.ownership_service import student_owned_query
from app.services.grade_service import grade_analytics
from app.services.goals_service import list_goals
from app.services.productivity_service import analyze_productivity
from app.services.time_service import utc_now_naive


def get_dashboard(db, student_id: int) -> dict:
    profile = db.query(StudentAcademicProfile).filter_by(student_id=student_id).first()
    snapshot = (
        db.query(DigitalTwinSnapshot)
        .filter_by(academic_profile_id=profile.id)
        .order_by(DigitalTwinSnapshot.captured_at.desc())
        .first()
        if profile
        else None
    )
    mastery = db.query(TopicMastery).filter_by(student_id=student_id).all()
    attendance = attendance_summary(db, student_id) if profile else []
    grades = student_owned_query(db, GradeRecord, student_id).order_by(
        GradeRecord.semester, GradeRecord.subject_id, GradeRecord.recorded_at
    ).all() if profile else []
    grade_summary = grade_analytics(db, student_id)
    profile_data = None
    if profile:
        profile_data = {
            column.name: getattr(profile, column.name)
            for column in profile.__table__.columns
        }
        profile_data["current_cpi"] = grade_summary["cpi"]
        profile_data["current_spi"] = grade_summary["current_spi"]
    attendance_scores = [item["record"].attendance_percentage for item in attendance if item["record"].attendance_percentage is not None]
    mastery_scores = [item.mastery_score for item in mastery]
    readiness_scores = []
    if attendance_scores:
        readiness_scores.append(sum(attendance_scores) / len(attendance_scores))
    if mastery_scores:
        readiness_scores.append(sum(mastery_scores) / len(mastery_scores))
    deadlines = upcoming_deadlines(db, student_id)
    goals = list_goals(db, student_id)
    productivity = analyze_productivity(db, student_id)
    return {
        "student_id": student_id,
        "profile": profile_data,
        "attendance": attendance,
        "mastery": [{"topic_id": item.topic_id, "mastery_score": item.mastery_score} for item in mastery],
        "readiness": round(sum(readiness_scores) / len(readiness_scores), 1) if readiness_scores else None,
        "grades": grades,
        "grade_analytics": grade_summary,
        "deadlines": [serialize_deadline(item) for item in deadlines],
        "notifications": db.query(StudentNotification).filter_by(student_id=student_id, read=False).order_by(StudentNotification.created_at.desc()).all(),
        "calendar": get_events(db, student_id),
        "agenda_today": get_agenda(db, student_id, utc_now_naive().date()),
        "agenda_week": get_week_agenda(db, student_id),
        "goals": goals,
        "goal_progress": [
            {"goal_id": goal["id"], "title": goal["title"], "progress_percent": goal["progress_percent"], "completed": goal["completed"]}
            for goal in goals
        ],
        "productivity": productivity,
        "productivity_score": productivity["productivity_score"],
        "consistency_score": productivity["consistency_score"],
        "study_hours_7d": productivity["study_hours_7d"],
        "completion_rate": productivity["completion_rate"],
        "habit_streaks": productivity["habit_streaks"],
        "readiness_snapshot": {
            "score": snapshot.overall_readiness,
            "captured_at": snapshot.captured_at,
        } if snapshot else None,
    }
