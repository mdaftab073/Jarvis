from app.agents.base import BaseAgent
from app.agents.base import execute_agent_tool


def get_active_semester_guidance(db, student_id):
    return execute_agent_tool("semester_guidance", {"db": db, "student_id": student_id})


def generate_copilot_guidance(db, semester_id, student_id):
    result = execute_agent_tool("semester_guidance", {"db": db, "student_id": student_id, "semester_id": semester_id, "action": "guidance"})
    return result["guidance"]


def detect_academic_risks(db, semester_id, student_id):
    result = execute_agent_tool("semester_guidance", {"db": db, "student_id": student_id, "semester_id": semester_id, "action": "risks"})
    return result["risks"]


class SemesterAgent(BaseAgent):
    name = "semester"

    def execute(self, context: dict) -> dict:
        db = context["db"]
        semester_id = context.get("semester_id")
        if semester_id is not None:
            guidance = [generate_copilot_guidance(db, semester_id, context["student_id"])]
            risks = detect_academic_risks(db, semester_id, context["student_id"])
        else:
            guidance = get_active_semester_guidance(db, context["student_id"])
            risks = [risk for item in guidance for risk in item["risks"]]
        recommendations = [
            action
            for item in guidance
            for action in item["next_actions"]
        ]
        scores = [item["semester_health"] for item in guidance]
        summary = (
            f"Active semester health averages {round(sum(scores) / len(scores))}%."
            if scores
            else "No active semester is configured."
        )
        return self.response(
            summary,
            recommendations,
            data={"semesters": guidance},
            risks=risks,
        )