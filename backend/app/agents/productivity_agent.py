from app.agents.base import BaseAgent
from app.agents.base import execute_agent_tool


def analyze_productivity(db, student_id):
    return execute_agent_tool("productivity_analytics", {"db": db, "student_id": student_id})


class ProductivityAgent(BaseAgent):
    name = "productivity"

    def execute(self, context: dict) -> dict:
        data = self.invoke_tool("productivity_analytics", context)
        risks = data["procrastination_risks"]
        summary = (
            f"Productivity score is {data['productivity_score']}/100 with "
            f"{data['study_hours_7d']} study hours in the last week."
        )
        return self.response(summary, data["suggestions"], data=data, risks=risks)
