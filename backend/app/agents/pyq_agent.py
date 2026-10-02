from app.agents.base import BaseAgent, execute_agent_tool


def analyze_exam_trends(db, student_id, subject_id):
    return execute_agent_tool("pyq_analysis", {"db": db, "student_id": student_id, "subject_id": subject_id, "action": "trends"})


def generate_important_topics(db, student_id, subject_id):
    return execute_agent_tool("pyq_analysis", {"db": db, "student_id": student_id, "subject_id": subject_id, "action": "important_topics"})


def get_topic_frequency(db, student_id, subject_id):
    return execute_agent_tool("pyq_analysis", {"db": db, "student_id": student_id, "subject_id": subject_id, "action": "topic_frequency"})


def generate_practice_questions(db, student_id, subject_id, count=5):
    return execute_agent_tool("pyq_analysis", {"db": db, "student_id": student_id, "subject_id": subject_id, "action": "practice_questions", "count": count})


class PYQAgent(BaseAgent):
    name = "pyq"

    def execute(self, context: dict) -> dict:
        db = context["db"]
        student_id = context["student_id"]
        subjects = self.invoke_tool("student_subjects", context)
        goal = context.get("goal", "").casefold()

        include_practice = any(word in goal for word in ("practice", "quiz", "mock"))
        results = []
        for subject in subjects:
            trends = analyze_exam_trends(db, student_id, subject.id)
            important = generate_important_topics(db, student_id, subject.id)
            results.append(
                {
                    "subject_id": subject.id,
                    "subject_name": subject.name,
                    "topic_frequency": get_topic_frequency(db, student_id, subject.id),
                    "trends": trends,
                    "important_topics": important,
                    "practice": (
                        generate_practice_questions(db, student_id, subject.id, count=5)
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