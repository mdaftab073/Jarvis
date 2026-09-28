from sqlalchemy.orm import Session

from app.agents.base import BaseAgent
from app.db.models import Course, Student, Subject
from app.services.pyq_service import (
    analyze_exam_trends,
    generate_important_topics,
    generate_practice_questions,
    get_topic_frequency,
)


class PYQAgent(BaseAgent):
    name = "pyq"

    def execute(self, context: dict) -> dict:
        db: Session = context["db"]
        student_id = context["student_id"]
        if db.query(Student.id).filter(Student.id == student_id).first() is None:
            raise ValueError("Student not found")
        subjects = (
            db.query(Subject)
            .join(Course, Subject.course_id == Course.id)
            .filter(Course.student_id == student_id)
            .order_by(Subject.name.asc())
            .all()
        )
        goal = context.get("goal", "").casefold()
        matched = [subject for subject in subjects if subject.name.casefold() in goal]
        if matched:
            subjects = matched
        elif context.get("subject_id") is not None:
            subjects = [subject for subject in subjects if subject.id == context["subject_id"]]

        include_practice = any(word in goal for word in ("practice", "quiz", "mock"))
        results = []
        for subject in subjects:
            trends = analyze_exam_trends(db, subject.id)
            important = generate_important_topics(db, subject.id)
            results.append(
                {
                    "subject_id": subject.id,
                    "subject_name": subject.name,
                    "topic_frequency": get_topic_frequency(db, subject.id),
                    "trends": trends,
                    "important_topics": important,
                    "practice": (
                        generate_practice_questions(db, subject.id, count=5)
                        if include_practice
                        else None
                    ),
                }
            )
        recommendations = [
            f"Revise {topic['topic']} based on its recorded PYQ frequency."
            for result in results
            for topic in result["important_topics"][:3]
        ]
        return self.response(
            f"Analyzed PYQ trends for {len(results)} subject(s).",
            recommendations,
            data={"subjects": results},
        )