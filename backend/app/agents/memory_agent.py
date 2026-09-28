from app.agents.base import BaseAgent
from app.services.memory_service import (
    build_student_profile,
    generate_profile_summary,
    get_memories,
    get_readiness_trend,
)


class MemoryAgent(BaseAgent):
    name = "memory"

    def execute(self, context: dict) -> dict:
        db = context["db"]
        student_id = context["student_id"]
        profile = build_student_profile(student_id, db=db)
        memories = get_memories(student_id, db=db)
        trend = get_readiness_trend(student_id, db=db)
        summary = generate_profile_summary(student_id, db=db)["summary"]
        recommendations = [
            f"Give extra attention to {topic}."
            for topic in profile["weaknesses"][:3]
        ]
        return self.response(
            summary,
            recommendations,
            data={"profile": profile, "memories": memories, "readiness_trend": trend},
        )