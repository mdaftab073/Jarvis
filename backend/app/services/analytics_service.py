import logging
from datetime import timezone

from sqlalchemy.orm import Session

from app.db.models import Course, PracticeSession, Student, Subject
from app.services.performance_service import (
    calculate_exam_readiness,
    generate_personalized_recommendations,
    get_strong_topics,
    get_weak_topics,
)

logger = logging.getLogger(__name__)


def _practice_score_trend(db: Session, student_id: int):
    sessions = (
        db.query(PracticeSession)
        .filter(
            PracticeSession.student_id == student_id,
            PracticeSession.completed_at.isnot(None),
        )
        .order_by(PracticeSession.completed_at.asc(), PracticeSession.id.asc())
        .all()
    )
    return [
        {
            "date": session.completed_at.replace(tzinfo=timezone.utc).date(),
            "subject_id": session.subject_id,
            "score": round(session.score or 0),
        }
        for session in sessions
    ]


def get_student_dashboard(db: Session, student_id: int):
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is None:
        raise ValueError("Student not found")

    subjects = (
        db.query(Subject)
        .join(Course, Subject.course_id == Course.id)
        .filter(Course.student_id == student_id)
        .order_by(Subject.name.asc())
        .all()
    )
    subject_analytics = []
    for subject in subjects:
        readiness = calculate_exam_readiness(db, student_id, subject.id)
        subject_analytics.append(
            {
                "subject_id": subject.id,
                "subject_name": subject.name,
                "readiness_score": readiness["readiness_score"],
                "status": readiness["status"],
                "plan_completion": readiness["plan_completion"],
                "pyq_coverage": readiness["pyq_coverage"],
                "weak_topics": get_weak_topics(db, student_id, subject.id),
                "strong_topics": get_strong_topics(db, student_id, subject.id),
                "recommendations": generate_personalized_recommendations(
                    db,
                    student_id,
                    subject.id,
                ),
                "topic_mastery": readiness["topic_mastery"],
            }
        )

    readiness_score = (
        round(
            sum(item["readiness_score"] for item in subject_analytics)
            / len(subject_analytics)
        )
        if subject_analytics
        else 0
    )
    plan_completion = (
        round(
            sum(item["plan_completion"] for item in subject_analytics)
            / len(subject_analytics)
        )
        if subject_analytics
        else 0
    )
    if readiness_score < 40:
        status = "At Risk"
    elif readiness_score < 60:
        status = "Needs Work"
    elif readiness_score < 80:
        status = "Good"
    else:
        status = "Ready"

    dashboard = {
        "student_id": student_id,
        "readiness_score": readiness_score,
        "status": status,
        "plan_completion": plan_completion,
        "weak_topics": [
            {"subject_id": item["subject_id"], **topic}
            for item in subject_analytics
            for topic in item["weak_topics"]
        ],
        "strong_topics": [
            {"subject_id": item["subject_id"], **topic}
            for item in subject_analytics
            for topic in item["strong_topics"]
        ],
        "recommendations": [
            recommendation
            for item in subject_analytics
            for recommendation in item["recommendations"]
        ][:10],
        "subjects": subject_analytics,
        "practice_score_trend": _practice_score_trend(db, student_id),
    }
    logger.info(
        "Built student analytics dashboard: student_id=%d subjects=%d readiness=%d",
        student_id,
        len(subjects),
        readiness_score,
    )
    return dashboard
