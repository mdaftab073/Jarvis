from sqlalchemy.orm import Session

from app.agents.base import BaseAgent
from app.db.models import Course, Student, Subject
from app.services.performance_service import (
    calculate_exam_readiness,
    generate_personalized_recommendations,
    get_strong_topics,
    get_weak_topics,
)


class AnalyticsAgent(BaseAgent):
    name = "analytics"

    def execute(self, context: dict) -> dict:
        db: Session = context["db"]
        student_id = context["student_id"]
        student = db.query(Student.id).filter(Student.id == student_id).first()
        if student is None:
            raise ValueError("Student not found")
        goal = context.get("goal", "").casefold()
        subjects = (
            db.query(Subject)
            .join(Course, Subject.course_id == Course.id)
            .filter(Course.student_id == student_id)
            .order_by(Subject.name.asc())
            .all()
        )
        matching = [item for item in subjects if item.name.casefold() in goal]
        if matching:
            subjects = matching
        elif context.get("subject_id") is not None:
            subjects = [item for item in subjects if item.id == context["subject_id"]]

        results = []
        for subject in subjects:
            readiness = calculate_exam_readiness(db, student_id, subject.id)
            weak = get_weak_topics(db, student_id, subject.id)
            strong = get_strong_topics(db, student_id, subject.id)
            recommendations = generate_personalized_recommendations(
                db,
                student_id,
                subject.id,
            )
            results.append(
                {
                    "subject_id": subject.id,
                    "subject_name": subject.name,
                    "readiness": readiness,
                    "weak_topics": weak,
                    "strong_topics": strong,
                    "recommendations": recommendations,
                }
            )
        summary = (
            "; ".join(
                f"{item['subject_name']} readiness {item['readiness']['readiness_score']}%"
                for item in results
            )
            if results
            else "No subjects are available for analytics."
        )
        return self.response(summary, data={"subjects": results})