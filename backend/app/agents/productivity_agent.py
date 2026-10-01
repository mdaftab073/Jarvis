from app.agents.base import BaseAgent
from app.services.productivity_service import analyze_productivity


class ProductivityAgent(BaseAgent):
    name = "productivity"

    def execute(self, context: dict) -> dict:
        data = analyze_productivity(context["db"], context["student_id"])
        risks = data["procrastination_risks"]
        summary = (
            f"Productivity score is {data['productivity_score']}/100 with "
            f"{data['study_hours_7d']} study hours in the last week."
        )
        return self.response(summary, data["suggestions"], data=data, risks=risks)
