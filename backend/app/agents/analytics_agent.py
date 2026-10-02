from sqlalchemy.orm import Session

from app.agents.base import BaseAgent, execute_agent_tool


def calculate_exam_readiness(db, student_id, subject_id):
    return execute_agent_tool("exam_readiness", {"db": db, "student_id": student_id, "subject_id": subject_id})


def get_weak_topics(db, student_id, subject_id):
    return execute_agent_tool("weak_topics", {"db": db, "student_id": student_id, "subject_id": subject_id})


def get_strong_topics(db, student_id, subject_id):
    return execute_agent_tool("strong_topics", {"db": db, "student_id": student_id, "subject_id": subject_id})


def generate_personalized_recommendations(db, student_id, subject_id):
    return execute_agent_tool("personalized_recommendations", {"db": db, "student_id": student_id, "subject_id": subject_id})


class AnalyticsAgent(BaseAgent):
    name = "analytics"

    def execute(self, context: dict) -> dict:
        db: Session = context["db"]
        student_id = context["student_id"]
        subjects = self.invoke_tool("student_subjects", context)

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