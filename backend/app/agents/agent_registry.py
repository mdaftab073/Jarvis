from app.agents.analytics_agent import AnalyticsAgent
from app.agents.memory_agent import MemoryAgent
from app.agents.pyq_agent import PYQAgent
from app.agents.retrieval_agent import RetrievalAgent
from app.agents.semester_agent import SemesterAgent
from app.agents.study_agent import StudyAgent


class AgentRegistry:
    def __init__(self, agents=None):
        self._agents = {}
        for agent in agents or []:
            self.register(agent)

    def register(self, agent) -> None:
        name = getattr(agent, "name", None)
        if not name:
            raise ValueError("Registered agents must define a name")
        self._agents[name] = agent

    def get(self, name: str):
        try:
            return self._agents[name]
        except KeyError as error:
            raise KeyError(f"Agent not registered: {name}") from error

    def names(self) -> list[str]:
        return list(self._agents)


def create_default_registry() -> AgentRegistry:
    return AgentRegistry(
        [
            AnalyticsAgent(),
            StudyAgent(),
            PYQAgent(),
            RetrievalAgent(),
            MemoryAgent(),
            SemesterAgent(),
        ]
    )