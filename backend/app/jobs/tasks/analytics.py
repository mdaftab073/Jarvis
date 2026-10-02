from app.db.database import SessionLocal
from app.db.models import Course, Student, Subject
from app.services.performance_service import calculate_exam_readiness
from app.jobs.registry import register_job
from app.services.dashboard_service import get_dashboard
from app.services.productivity_service import analyze_productivity


@register_job("refresh_analytics", "Refresh dashboard and productivity analytics for selected students.")
def refresh_analytics(payload: dict) -> dict:
    with SessionLocal() as db:
        if payload.get("all_students"):
            student_ids = [student_id for (student_id,) in db.query(Student.id).all()]
        else:
            student_ids = [int(payload["student_id"])]
        refreshed = 0
        for student_id in student_ids:
            get_dashboard(db, student_id)
            analyze_productivity(db, student_id)
            subject_ids = [
                subject_id
                for (subject_id,) in db.query(Subject.id)
                .join(Course, Course.id == Subject.course_id)
                .filter(Course.student_id == student_id)
                .all()
            ]
            for subject_id in subject_ids:
                calculate_exam_readiness(db, student_id, subject_id)
            refreshed += 1
        return {"students_refreshed": refreshed, "study_subjects_refreshed": sum(len(db.query(Subject.id).join(Course, Course.id == Subject.course_id).filter(Course.student_id == student_id).all()) for student_id in student_ids)}