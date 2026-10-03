import logging
import re
import time

from app.agents.agent_registry import AgentRegistry, create_default_registry
from app.agents.base import BaseAgent, execute_agent_tool
from app.tools.registry import get_tool_registry


def generate_agent_response(goal, response_context):
    return execute_agent_tool("academic_strategy", {"goal": goal, "strategy_context": response_context})

logger = logging.getLogger(__name__)


def select_chat_tool(message: str) -> str | None:
    text = message.casefold()
    if re.search(r"\b(hello|hi|hey|good morning|good afternoon)\b", text):
        return None
    routes = (
        (r"\b(attendance|present|absent)\b", "attendance_summary"),
        (r"\b(grades?|marks|cpi|spi|gpa|cgpa)\b", "grades"),
        (r"\b(academic profile|profile|enrollment|department|program)\b", "academic_profile"),
        (r"\b(deadlines?|due dates?|overdue)\b", "deadlines"),
        (r"\b(calendar|events?)\b", "calendar_events"),
        (r"\b(reminders?)\b", "reminders"),
        (r"\b(goals?)\b", "goals"),
        (r"\b(habits?)\b", "habits"),
        (r"\b(productivity|consistency|focus routine)\b", "productivity_analytics"),
        (r"\b(semester copilot|semester health|semester risks?|readiness forecast|exam countdown)\b", "semester_copilot"),
        (r"\b(study plan|study schedule|schedule)\b", "study_plan"),
        (r"\b(mastery|topic mastery|learning progress)\b", "topic_mastery"),
        (r"\b(flashcards?)\b", "flashcards"),
        (r"\b(quizzes|quiz|practice test)\b", "quizzes"),
    )
    return next((tool for pattern, tool in routes if re.search(pattern, text)), "rag_search")


def _chat_tool_answer(tool_name: str, data) -> str:
    if tool_name == "rag_search":
        answer = data.get("answer") if isinstance(data, dict) else None
        return answer or "I couldn't find an answer in the available study materials."
    if tool_name == "attendance_summary":
        records = data or []
        if not records:
            return "I couldn't find any attendance records yet."
        summaries = []
        for item in records:
            record = item.get("record", {})
            percentage = record.get("attendance_percentage")
            if percentage is None:
                percentage = "not recorded"
            else:
                percentage = f"{percentage:g}%"
            summaries.append(f"Subject {record.get('subject_id')}: {percentage} ({item.get('risk', 'UNKNOWN')})")
        return "Attendance summary: " + "; ".join(summaries)
    if tool_name == "grades":
        cpi = data.get("cpi") if isinstance(data, dict) else None
        if cpi is None:
            return "I couldn't find final grade records to calculate your CPI yet."
        return f"Your current CPI is {cpi:g}. Semester SPI: {data.get('spi_by_semester', {})}."
    if tool_name == "academic_profile":
        profile = data.get("profile") if isinstance(data, dict) else None
        if not profile:
            return "Your academic profile hasn't been set up yet."
        semester = profile.get("semester")
        department = profile.get("department") or profile.get("branch")
        return f"Your academic profile is available{f' for semester {semester}' if semester else ''}{f' in {department}' if department else ''}."
    if isinstance(data, list):
        if not data:
            return f"I couldn't find any {tool_name.replace('_', ' ')} records yet."
        first = data[0]
        label = first.get("title") if isinstance(first, dict) else None
        return f"I found {len(data)} {tool_name.replace('_', ' ')} record(s)" + (f", including {label}." if label else ".")
    if isinstance(data, dict) and data.get("summary"):
        return data["summary"]
    if isinstance(data, dict) and "productivity_score" in data:
        return f"Your productivity score is {data['productivity_score']}/100, with {data.get('study_hours_7d', 0)} study hours this week."
    return f"I retrieved your {tool_name.replace('_', ' ')} information."


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
        ("academic_profile", r"\b(profile|enrollment|cpi|spi|credits|grades?)\b"),
        ("notification", r"\bnotifications?\b"),
        ("reminder", r"\breminders?\b"),
        ("productivity", r"\b(goals?|habits?|productivity|consistency|focus|routine)\b"),
        ("semester_copilot", r"\b(semester copilot|exam command center|readiness forecast|exam countdown)\b"),
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

    def __init__(self, registry: AgentRegistry | None = None, tools=None):
        self.registry = registry or create_default_registry()
        self.tool_registry = tools or get_tool_registry()

    def list_tools(self) -> list[dict]:
        return self.tool_registry.list_tools()

    def process_message(self, context: dict) -> dict:
        student_id = context.get("student_id")
        message = (context.get("message") or "").strip()
        if not student_id or not message:
            raise ValueError("student_id and message are required")

        tool_name = select_chat_tool(message)
        history = context.get("history", [])[-20:]
        if tool_name is None:
            return {
                "answer": "Hi. What would you like help with today?",
                "agent_used": self.name,
                "tool_used": None,
                "metadata": {"tools_executed": [], "history_messages": len(history)},
            }

        payload = {
            "db": context.get("db"),
            "student_id": student_id,
            "principal_id": context.get("principal_id"),
        }
        tools_executed = [tool_name]
        if tool_name == "rag_search":
            follow_up = re.search(r"\b(it|that|those|them|same)\b", message.casefold())
            question = message
            if follow_up and history:
                prior = " ".join(
                    str(item.get("content", ""))
                    for item in history[-4:]
                    if isinstance(item, dict) and item.get("content")
                )
                if prior:
                    question = f"Conversation context: {prior}\nCurrent question: {message}"
            payload["question"] = question
        elif tool_name in {"study_plan", "flashcards"}:
            subjects = self.tool_registry.execute_tool(
                "student_subjects", {**payload, "goal": message}
            ).data
            tools_executed.insert(0, "student_subjects")
            requested_subject_id = context.get("subject_id")
            subject = next((item for item in subjects if item.get("id") == requested_subject_id), None) if requested_subject_id else (subjects[0] if subjects else None)
            if subject is None:
                return {
                    "answer": "Which subject should I use for that?",
                    "agent_used": self.name,
                    "tool_used": "student_subjects",
                    "metadata": {"tools_executed": tools_executed, "history_messages": len(history)},
                }
            payload["subject_id"] = subject["id"]
            if tool_name == "study_plan":
                payload["action"] = "rank_topics"

        result = self.tool_registry.execute_tool(tool_name, payload)
        return {
            "answer": _chat_tool_answer(tool_name, result.data),
            "agent_used": self.name,
            "tool_used": tool_name,
            "metadata": {
                "tools_executed": tools_executed,
                "execution_status": "succeeded",
                "history_messages": len(history),
            },
        }

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
            "available_tools": self.list_tools(),
        }
        return self.response(
            result["summary"],
            result["recommended_actions"],
            data=result,
            risks=result["risks"],
        )

    def run(self, context: dict) -> dict:
        return self.execute(context)["data"]