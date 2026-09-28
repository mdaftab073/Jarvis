from sqlalchemy.orm import Session

from app.db.models import Semester
from app.services.memory_service import build_student_profile
from app.services.semester_service import (
    calculate_semester_health,
    detect_academic_risks,
    get_semester,
)


def generate_copilot_guidance(db: Session, semester_id: int) -> dict:
    semester = get_semester(db, semester_id)
    health = calculate_semester_health(db, semester_id)
    risks = detect_academic_risks(db, semester_id)
    profile = build_student_profile(semester["student_id"], db=db)
    enrollments = {
        item["subject_id"]: item for item in semester["subjects"]
    }
    priority_subjects = [
        {
            **metric,
            "target_score": enrollments[metric["subject_id"]]["target_score"],
        }
        for metric in sorted(
            health["subjects"],
            key=lambda item: (item["readiness"], item["subject_name"]),
        )
    ]
    next_actions = []
    next_actions.extend(item["risk"] for item in risks[:3])
    for milestone in semester["milestones"]:
        if not milestone["completed"]:
            next_actions.append(
                f"Complete {milestone['title']} by {milestone['due_date'].isoformat()}."
            )
            if len(next_actions) >= 5:
                break
    for subject in priority_subjects:
        target = subject["target_score"]
        if target is not None and subject["readiness"] < target:
            next_actions.append(
                f"Raise {subject['subject_name']} readiness toward its {target:g}% target."
            )
        if len(next_actions) >= 5:
            break
    if not next_actions:
        next_actions.append("Review your semester goals and keep your weekly study plan current.")
    return {
        "semester_id": semester_id,
        "semester_health": health["health_score"],
        "health_category": health["category"],
        "priority_subjects": priority_subjects,
        "risks": risks,
        "milestones": semester["milestones"],
        "next_actions": next_actions[:5],
        "profile_memory": {
            "strengths": profile["strengths"],
            "weaknesses": profile["weaknesses"],
            "study_habits": profile["study_habits"],
            "current_goal": profile["current_goal"],
        },
    }


def get_active_semester_guidance(db: Session, student_id: int) -> list[dict]:
    active_semesters = (
        db.query(Semester)
        .filter(Semester.student_id == student_id, Semester.status == "ACTIVE")
        .order_by(Semester.semester_number.asc())
        .all()
    )
    return [
        generate_copilot_guidance(db, semester.id)
        for semester in active_semesters
    ]