import json
import logging
import re
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import Course, StudyPlan, Student, Subject
from app.services import llm_service
from app.services.performance_service import (
    calculate_exam_readiness,
    generate_personalized_recommendations,
    get_strong_topics,
    get_weak_topics,
)
from app.services.pyq_service import (
    analyze_exam_trends,
    generate_important_topics,
    generate_practice_questions,
)
from app.services.study_plan_service import generate_study_plan, get_study_plan
from app.services.memory_service import (
    build_student_profile,
    get_memories,
    get_readiness_trend,
    store_memory,
    update_student_profile,
)
from app.services.copilot_service import get_active_semester_guidance

logger = logging.getLogger(__name__)

_ACTION_SETS = {
    "exam_preparation": [
        "readiness",
        "weak_topics",
        "study_plan",
        "pyq_topics",
        "recommendations",
    ],
    "revision_planning": [
        "study_plan",
        "weak_topics",
        "pyq_topics",
        "recommendations",
    ],
    "weak_topic_recovery": [
        "readiness",
        "weak_topics",
        "strong_topics",
        "pyq_topics",
        "recommendations",
    ],
    "practice_preparation": [
        "practice_generation",
        "weak_topics",
        "pyq_topics",
        "recommendations",
    ],
    "general_guidance": [
        "readiness",
        "weak_topics",
        "strong_topics",
        "study_plan",
        "pyq_topics",
        "recommendations",
    ],
}


def classify_goal(goal: str) -> str:
    text = goal.casefold()
    if re.search(r"\b(practice|quiz|mock test|practice questions)\b", text):
        return "practice_preparation"
    if re.search(r"\b(weak|improve|struggling|low score|work on)\b", text):
        return "weak_topic_recovery"
    if re.search(r"\b(revis(e|ion)|review|this week|next week)\b", text):
        return "revision_planning"
    if re.search(r"\b(exam|examination|test)\b", text):
        return "exam_preparation"
    return "general_guidance"


def plan_goal_execution(goal: str) -> dict:
    goal_type = classify_goal(goal)
    return {"goal_type": goal_type, "actions": list(_ACTION_SETS[goal_type])}


def _goal_deadline_days(goal: str) -> int | None:
    match = re.search(r"\b(?:in|within)\s+(\d+)\s+days?\b", goal, re.IGNORECASE)
    if match is None:
        match = re.search(r"\b(\d+)\s+days?\s+(?:left|away)\b", goal, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _goal_hours_per_day(goal: str) -> float:
    match = re.search(r"\b(\d+(?:\.\d+)?)\s+hours?\s+(?:a\s+)?day\b", goal, re.IGNORECASE)
    return float(match.group(1)) if match else 2.0


def _get_student_subjects(db: Session, student_id: int) -> list[Subject]:
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is None:
        raise ValueError("Student not found")
    return (
        db.query(Subject)
        .join(Course, Subject.course_id == Course.id)
        .filter(Course.student_id == student_id)
        .order_by(Subject.name.asc())
        .all()
    )


def _resolve_subjects(db: Session, student_id: int, goal: str) -> list[Subject]:
    subjects = _get_student_subjects(db, student_id)
    normalized_goal = goal.casefold()
    matching = [subject for subject in subjects if subject.name.casefold() in normalized_goal]
    if matching:
        return matching
    if len(subjects) == 1:
        return subjects
    return subjects


def execute_action(
    db: Session,
    student_id: int,
    action: str,
    subject_id: int | None = None,
    goal: str = "",
):
    supported_actions = {
        "readiness",
        "weak_topics",
        "strong_topics",
        "study_plan",
        "pyq_topics",
        "recommendations",
        "practice_generation",
    }
    if action not in supported_actions:
        raise ValueError(f"Unsupported academic agent action: {action}")

    subjects = _get_student_subjects(db, student_id)
    if subject_id is not None:
        subjects = [subject for subject in subjects if subject.id == subject_id]
        if not subjects:
            raise ValueError("Subject not found for this student")

    output = []
    for subject in subjects:
        if action == "readiness":
            result = calculate_exam_readiness(db, student_id, subject.id)
        elif action == "weak_topics":
            result = get_weak_topics(db, student_id, subject.id)
        elif action == "strong_topics":
            result = get_strong_topics(db, student_id, subject.id)
        elif action == "recommendations":
            result = generate_personalized_recommendations(db, student_id, subject.id)
        elif action == "pyq_topics":
            result = {
                "trends": analyze_exam_trends(db, subject.id),
                "important_topics": generate_important_topics(db, subject.id),
            }
        elif action == "practice_generation":
            result = generate_practice_questions(db, subject.id, count=5)
        else:
            deadline_days = _goal_deadline_days(goal)
            if deadline_days and deadline_days > 0:
                exam_date = datetime.now(timezone.utc).date() + timedelta(days=deadline_days)
                existing = (
                    db.query(StudyPlan)
                    .filter(
                        StudyPlan.student_id == student_id,
                        StudyPlan.subject_id == subject.id,
                        StudyPlan.exam_date == exam_date,
                    )
                    .order_by(StudyPlan.created_at.desc(), StudyPlan.id.desc())
                    .first()
                )
                if existing is None:
                    existing = generate_study_plan(
                        db,
                        student_id=student_id,
                        subject_id=subject.id,
                        exam_date=exam_date,
                        hours_per_day=_goal_hours_per_day(goal),
                    )
                result = get_study_plan(db, existing.id)
            else:
                existing = (
                    db.query(StudyPlan)
                    .filter(
                        StudyPlan.student_id == student_id,
                        StudyPlan.subject_id == subject.id,
                    )
                    .order_by(StudyPlan.created_at.desc(), StudyPlan.id.desc())
                    .first()
                )
                result = get_study_plan(db, existing.id) if existing else None
        output.append(
            {
                "subject_id": subject.id,
                "subject_name": subject.name,
                "result": result,
            }
        )
    return output


def build_agent_context(action_results: dict) -> dict:
    context = {
        "readiness": [],
        "weak_topics": [],
        "strong_topics": [],
        "pyq_trends": [],
        "study_plans": [],
        "recommendations": [],
        "practice_questions": [],
    }
    for action, subject_results in action_results.items():
        for subject_result in subject_results:
            subject_name = subject_result["subject_name"]
            result = subject_result["result"]
            if action == "readiness" and result is not None:
                context["readiness"].append(
                    {
                        "subject": subject_name,
                        "score": result["readiness_score"],
                        "status": result["status"],
                        "plan_completion": result["plan_completion"],
                        "pyq_coverage": result["pyq_coverage"],
                    }
                )
            elif action in {"weak_topics", "strong_topics"} and result:
                context[action].extend(
                    {"subject": subject_name, **topic} for topic in result
                )
            elif action == "pyq_topics" and result is not None:
                context["pyq_trends"].append({"subject": subject_name, **result})
            elif action == "study_plan" and result is not None:
                context["study_plans"].append(result)
            elif action == "recommendations" and result:
                context["recommendations"].extend(
                    {"subject": subject_name, "text": item} for item in result
                )
            elif action == "practice_generation" and result is not None:
                context["practice_questions"].append(
                    {"subject": subject_name, **result}
                )
    return context


def _fallback_agent_response(goal: str, context: dict) -> dict:
    readiness = context["readiness"]
    weak_topics = context["weak_topics"]
    pyq_topics = [
        topic
        for subject_data in context["pyq_trends"]
        for topic in subject_data.get("important_topics", [])
    ]
    recommended_topics = []
    for item in [*weak_topics, *pyq_topics]:
        topic = item.get("topic")
        if topic and topic not in recommended_topics:
            recommended_topics.append(topic)
    priority_actions = [
        f"Review {item['topic']}" for item in weak_topics[:3]
    ]
    for plan in context["study_plans"]:
        for day in plan.get("daily_agenda", []):
            pending = [task for task in day.get("tasks", []) if task["status"] != "COMPLETED"]
            if pending:
                priority_actions.append(
                    f"Complete Day {day['day_number']} study tasks"
                )
                break
    readiness_summary = (
        ", ".join(f"{item['subject']}: {item['score']}%" for item in readiness)
        if readiness
        else "Readiness data is not available yet"
    )
    next_steps = ["Attempt a practice test and review the questions you miss."]
    if context["practice_questions"]:
        next_steps = ["Complete the generated practice questions and review your answers."]
    return {
        "summary": f"{readiness_summary}. Your goal: {goal}",
        "priority_actions": priority_actions or ["Review the highest-priority topics."],
        "recommended_topics": recommended_topics[:5],
        "next_steps": next_steps,
    }


def generate_agent_response(goal: str, context: dict) -> dict:
    prompt = f"""
You are Jarvis, an academic workflow assistant. Build a practical strategy from the supplied student data.
Do not invent readiness scores, topics, or study-plan tasks. Return only valid JSON with these keys:
{{"summary": "...", "priority_actions": ["..."], "recommended_topics": ["..."], "next_steps": ["..."]}}

Student goal: {goal}
Academic context:
{json.dumps(context, default=str)}
"""
    try:
        response = llm_service.client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)
        fallback = _fallback_agent_response(goal, context)
        return {
            "summary": str(parsed.get("summary") or fallback["summary"]),
            "priority_actions": _string_list(
                parsed.get("priority_actions"), fallback["priority_actions"]
            ),
            "recommended_topics": _string_list(
                parsed.get("recommended_topics"), fallback["recommended_topics"]
            ),
            "next_steps": _string_list(parsed.get("next_steps"), fallback["next_steps"]),
        }
    except Exception:
        logger.exception("Unable to generate structured academic agent response")
        return _fallback_agent_response(goal, context)


def _string_list(value, fallback: list[str]) -> list[str]:
    if not isinstance(value, list):
        return fallback
    return [str(item) for item in value if isinstance(item, str)]


def run_academic_agent(
    student_id: int,
    goal: str,
    db: Session | None = None,
    include_debug: bool = False,
) -> dict:
    owns_session = db is None
    if owns_session:
        db = SessionLocal()
    started_at = time.perf_counter()
    try:
        student_profile = build_student_profile(student_id, db=db)
        student_memories = get_memories(student_id, db=db)
        readiness_trend = get_readiness_trend(student_id, db=db)
        plan = plan_goal_execution(goal)
        subjects = _resolve_subjects(db, student_id, goal)
        matching = [subject for subject in subjects if subject.name.casefold() in goal.casefold()]
        target_subject_id = matching[0].id if matching else None
        update_student_profile(
            student_id,
            db=db,
            current_goal=goal,
            preferred_subjects=(
                [subject.name for subject in matching]
                if matching
                else student_profile["preferred_subjects"]
            ),
        )
        store_memory(
            student_id,
            "GOAL",
            goal,
            {"status": "ACTIVE"},
            db=db,
        )
        action_results = {}
        executed_actions = []
        for action in plan["actions"]:
            try:
                action_results[action] = execute_action(
                    db,
                    student_id,
                    action,
                    subject_id=target_subject_id,
                    goal=goal,
                )
                executed_actions.append(action)
            except Exception:
                logger.exception(
                    "Academic agent action failed: student_id=%d action=%s",
                    student_id,
                    action,
                )
                action_results[action] = []

        context = build_agent_context(action_results)
        context["student_profile"] = student_profile
        context["student_memories"] = student_memories
        context["readiness_trend"] = readiness_trend
        context["semester_guidance"] = get_active_semester_guidance(db, student_id)
        result = generate_agent_response(goal, context)
        for recommendation in result["priority_actions"]:
            store_memory(
                student_id,
                "RECOMMENDATION",
                recommendation,
                {"goal": goal, "status": "OPEN"},
                db=db,
            )
        if include_debug:
            result.update(
                {
                    "goal_type": plan["goal_type"],
                    "planned_actions": plan["actions"],
                    "executed_actions": executed_actions,
                }
            )
        logger.info(
            "Academic agent completed: student_id=%d goal_type=%s planned=%s executed=%s duration_seconds=%.3f",
            student_id,
            plan["goal_type"],
            plan["actions"],
            executed_actions,
            time.perf_counter() - started_at,
        )
        return result
    finally:
        if owns_session:
            db.close()