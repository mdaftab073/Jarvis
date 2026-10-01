import logging
import re
import time

from app.agents.agent_registry import AgentRegistry, create_default_registry
from app.agents.base import BaseAgent
from app.services.academic_agent_service import generate_agent_response

logger = logging.getLogger(__name__)


def create_execution_plan(goal: str) -> dict:
    text = goal.casefold()
    retrieval_requested = bool(
        re.search(r"\b(explain|what does|according to|uploaded|notes|document|search)\b", text)
    )
    practice_requested = bool(re.search(r"\b(practice|quiz|mock test)\b", text))
    exam_requested = bool(re.search(r"\b(exam|examination|test)\b", text))
    revision_requested = bool(re.search(r"\b(revis(e|ion)|review|study plan)\b", text))
    semester_requested = bool(re.search(r"\b(semester|milestone|cgpa|risk)\b", text))
    memory_requested = bool(re.search(r"\b(profile|remember|history|past performance)\b", text))
    learning_requested = bool(re.search(r"\b(mastery|flashcard|insight|progress|learning)\b", text))
    operating_system_routes = [
        ("attendance", r"\battendance\b"),
        ("deadline", r"\b(deadlines?|due dates?|overdue)\b"),
        ("calendar", r"\bcalendar\b"),
        ("scheduler", r"\b(schedule|scheduling|study blocks?)\b"),
        ("academic_profile", r"\b(profile|enrollment|cpi|spi|credits)\b"),
        ("notification", r"\bnotifications?\b"),
        ("reminder", r"\breminders?\b"),
    ]

    agents = []
    if retrieval_requested:
        agents.append("retrieval")
    if exam_requested or practice_requested or revision_requested or semester_requested:
        agents.append("analytics")
    if exam_requested or semester_requested:
        agents.append("semester")
    if exam_requested or revision_requested or practice_requested:
        agents.append("study")
    if exam_requested or practice_requested or revision_requested:
        agents.append("pyq")
    if memory_requested:
        agents.append("memory")
    if learning_requested:
        agents.append("learning")
    agents.extend(name for name, pattern in operating_system_routes if re.search(pattern, text))
    if not agents:
        agents = ["analytics", "memory"]
    return {
        "goal_type": (
            "exam_preparation" if exam_requested else
            "personalized_learning" if learning_requested else
            "practice_preparation" if practice_requested else
            "revision_planning" if revision_requested else
            "semester_guidance" if semester_requested else
            "retrieval" if retrieval_requested else
            "student_operating_system" if any(re.search(pattern, text) for _, pattern in operating_system_routes) else
            "general_guidance"
        ),
        "agents": list(dict.fromkeys(agents)),
    }


def aggregate_agent_outputs(agent_outputs: list[dict]) -> dict:
    aggregate = {
        "readiness": [],
        "weak_topics": [],
        "strong_topics": [],
        "plans": [],
        "revision_priorities": [],
        "risks": [],
        "recommendations": [],
        "agent_summaries": [],
        "failures": [],
    }
    for output in agent_outputs:
        if output.get("error"):
            aggregate["failures"].append(
                {"agent_name": output.get("agent_name"), "error": output["error"]}
            )
            continue
        aggregate["agent_summaries"].append(
            {"agent_name": output["agent_name"], "summary": output["summary"]}
        )
        aggregate["recommendations"].extend(output.get("recommendations", []))
        aggregate["risks"].extend(output.get("risks", []))
        data = output.get("data", {})
        for subject in data.get("subjects", []):
            readiness = subject.get("readiness")
            if readiness:
                aggregate["readiness"].append(
                    {
                        "subject_id": subject.get("subject_id"),
                        "subject_name": subject.get("subject_name"),
                        **readiness,
                    }
                )
            aggregate["weak_topics"].extend(
                {
                    "subject_id": subject.get("subject_id"),
                    "subject_name": subject.get("subject_name"),
                    **topic,
                }
                for topic in subject.get("weak_topics", [])
            )
            aggregate["strong_topics"].extend(
                {
                    "subject_id": subject.get("subject_id"),
                    "subject_name": subject.get("subject_name"),
                    **topic,
                }
                for topic in subject.get("strong_topics", [])
            )
            aggregate["revision_priorities"].extend(
                topic.get("topic")
                for topic in subject.get("important_topics", [])[:5]
                if topic.get("topic")
            )
        aggregate["plans"].extend(data.get("plans", []))
        for semester in data.get("semesters", []):
            aggregate["risks"].extend(semester.get("risks", []))
            aggregate["recommendations"].extend(semester.get("next_actions", []))
        if output.get("agent_name") == "learning" or "average_mastery" in data:
            aggregate["weak_topics"].extend(
                {
                    "subject_id": None,
                    "subject_name": "Personalized Learning",
                    "topic": topic.get("topic_name", topic.get("topic")),
                    **topic,
                }
                for topic in data.get("weak_topics", [])
            )
            aggregate["strong_topics"].extend(
                {
                    "subject_id": None,
                    "subject_name": "Personalized Learning",
                    "topic": topic.get("topic_name", topic.get("topic")),
                    **topic,
                }
                for topic in data.get("strong_topics", [])
            )
            if data.get("overall_readiness"):
                aggregate["readiness"].append(
                    {
                        "subject_id": None,
                        "subject_name": "Learning Mastery",
                        "readiness_score": int(data.get("average_mastery", 0)),
                        "status": data.get("overall_readiness"),
                    }
                )
    aggregate["recommendations"] = list(dict.fromkeys(aggregate["recommendations"]))
    aggregate["revision_priorities"] = list(dict.fromkeys(aggregate["revision_priorities"]))
    return aggregate


class AcademicDirectorAgent(BaseAgent):
    name = "director"

    def __init__(self, registry: AgentRegistry | None = None):
        self.registry = registry or create_default_registry()

    def execute(self, context: dict) -> dict:
        started_at = time.perf_counter()
        goal = context.get("goal", "")
        plan = create_execution_plan(goal)
        selected_agents = plan["agents"]
        agent_outputs = []
        execution_order = []
        for agent_name in selected_agents:
            agent_started_at = time.perf_counter()
            execution_order.append(agent_name)
            try:
                output = self.registry.get(agent_name).execute(context)
                agent_outputs.append(output)
            except Exception as error:
                logger.exception("Director delegated agent failed: agent=%s", agent_name)
                agent_outputs.append(
                    {
                        "agent_name": agent_name,
                        "summary": "Agent execution failed.",
                        "recommendations": [],
                        "data": {},
                        "risks": [],
                        "error": str(error),
                    }
                )
            logger.info(
                "Director agent execution: agent=%s duration_seconds=%.3f",
                agent_name,
                time.perf_counter() - agent_started_at,
            )

        aggregation_started_at = time.perf_counter()
        aggregate = aggregate_agent_outputs(agent_outputs)
        response_context = {
            **aggregate,
            "readiness": [
                {
                    "subject": item.get("subject_name", "Subject"),
                    "score": item.get("readiness_score", 0),
                }
                for item in aggregate["readiness"]
            ],
            "weak_topics": aggregate["weak_topics"],
            "study_plans": aggregate["plans"],
            "pyq_trends": [],
            "practice_questions": [],
            "semester_guidance": [
                semester
                for output in agent_outputs
                for semester in output.get("data", {}).get("semesters", [])
            ],
            "student_profile": next(
                (
                    output["data"]["profile"]
                    for output in agent_outputs
                    if "profile" in output.get("data", {})
                ),
                context.get("student_profile", {}),
            ),
        }
        strategy = generate_agent_response(goal, response_context)
        aggregation_duration = time.perf_counter() - aggregation_started_at
        duration = time.perf_counter() - started_at
        logger.info(
            "Director execution complete: selected=%s order=%s execution_seconds=%.3f aggregation_seconds=%.3f failures=%d",
            selected_agents,
            execution_order,
            duration,
            aggregation_duration,
            len(aggregate["failures"]),
        )
        result = {
            "goal_type": plan["goal_type"],
            "selected_agents": selected_agents,
            "execution_order": execution_order,
            "summary": strategy["summary"],
            "readiness": aggregate["readiness"],
            "weak_topics": aggregate["weak_topics"],
            "study_strategy": aggregate["plans"],
            "revision_priorities": aggregate["revision_priorities"],
            "risks": aggregate["risks"],
            "recommended_actions": list(
                dict.fromkeys(
                    [*strategy["priority_actions"], *aggregate["recommendations"]]
                )
            ),
            "next_steps": strategy["next_steps"],
            "agent_outputs": agent_outputs,
            "failures": aggregate["failures"],
            "execution_duration_seconds": round(duration, 4),
            "aggregation_duration_seconds": round(aggregation_duration, 4),
        }
        return self.response(
            result["summary"],
            result["recommended_actions"],
            data=result,
            risks=result["risks"],
        )

    def run(self, context: dict) -> dict:
        return self.execute(context)["data"]