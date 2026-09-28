from abc import ABC, abstractmethod


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