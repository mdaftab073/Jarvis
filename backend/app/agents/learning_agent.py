from app.agents.base import BaseAgent


class LearningAgent(BaseAgent):
    """Analyse a student's learning state and generate recommendations."""

    name = "learning"

    def execute(self, context: dict) -> dict:
        if context.get("db") is None or context.get("student_id") is None:
            return self.response("Missing db or student_id in context.", risks=[{"message": "LearningAgent requires db and student_id"}])
        result = self.invoke_tool("learning_summary", context)
        return self.response(result["summary"], result["recommendations"], result["data"], result["risks"])
