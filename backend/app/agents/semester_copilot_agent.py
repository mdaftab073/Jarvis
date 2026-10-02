from app.agents.base import BaseAgent


class SemesterCopilotAgent(BaseAgent):
    name = "semester_copilot"

    def execute(self, context: dict) -> dict:
        result = self.invoke_tool("semester_copilot", context)
        return self.response(result["summary"], result["recommendations"], result["data"], result["risks"])
