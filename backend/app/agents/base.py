from abc import ABC, abstractmethod

from app.tools.registry import get_tool_registry


def execute_agent_tool(tool_name: str, context: dict, **parameters):
    payload = {**context, **parameters}
    response = get_tool_registry().execute_tool(tool_name, payload)
    return response._raw_data


class BaseAgent(ABC):
    name = "base"

    @abstractmethod
    def execute(self, context: dict) -> dict:
        raise NotImplementedError

    def response(
        self,
        summary: str,
        recommendations: list[str] | None = None,
        data=None,
        risks: list[dict] | None = None,
    ) -> dict:
        return {
            "agent_name": self.name,
            "summary": summary,
            "recommendations": recommendations or [],
            "data": data or {},
            "risks": risks or [],
        }

    def invoke_tool(self, tool_name: str, context: dict, **parameters):
        return execute_agent_tool(tool_name, context, **parameters)