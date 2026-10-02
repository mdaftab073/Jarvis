from datetime import date

from app.db.models import StudyPlan
from app.services.rag_service import ask_question
from app.services.study_material_service import get_subject_materials
from app.services.study_plan_service import (
    generate_study_plan,
    get_study_plan,
    rank_topics_for_study,
)
from app.tools.base import BaseTool
from app.tools.common import require_student, require_subject_owner
from app.tools.exceptions import ToolValidationError
from app.tools.registry import register_tool
from app.tools.schemas import RAGSearchRequest, StudyPlanToolRequest, SubjectToolRequest


@register_tool
class RAGSearchTool(BaseTool):
    name = "rag_search"
    description = "Search the student's study materials and answer a question with cited sources."
    input_model = RAGSearchRequest

    async def execute(self, payload):
        db = getattr(payload, "db", None)
        if db is None:
            raise ToolValidationError(self.name, "A database session is required")
        question = payload.value("question", payload.value("retrieval_question", payload.value("goal", "")))
        if not question.strip():
            raise ToolValidationError(self.name, "A search question is required")
        student_id = getattr(payload, "student_id", None)
        subject_id = getattr(payload, "subject_id", None)
        if student_id is not None:
            require_student(payload, self.name)
            if subject_id is not None:
                require_subject_owner(db, student_id, subject_id, self.name)
        return ask_question(question=question, db=db, subject_id=subject_id)


@register_tool
class StudyMaterialTool(BaseTool):
    name = "study_materials"
    description = "Retrieve study materials for a student-owned subject."
    input_model = SubjectToolRequest

    async def execute(self, payload):
        db, student_id = require_student(payload, self.name)
        require_subject_owner(db, student_id, payload.subject_id, self.name)
        return get_subject_materials(db, payload.subject_id)


@register_tool
class StudyPlanTool(BaseTool):
    name = "study_plan"
    description = "Rank study topics, retrieve an owned study plan, or create a plan before an exam."
    input_model = StudyPlanToolRequest

    async def execute(self, payload):
        db, student_id = require_student(payload, self.name)
        action = payload.value("action", "rank_topics")
        subject_id = getattr(payload, "subject_id", None)
        if action in {"rank_topics", "generate"}:
            if subject_id is None:
                raise ToolValidationError(self.name, "subject_id is required")
            require_subject_owner(db, student_id, subject_id, self.name)
        if action == "rank_topics":
            return rank_topics_for_study(db, subject_id)
        if action == "generate":
            exam_date = payload.value("exam_date")
            hours_per_day = payload.value("hours_per_day", 2.0) or 2.0
            if isinstance(exam_date, str):
                exam_date = date.fromisoformat(exam_date)
            if exam_date is None:
                raise ToolValidationError(self.name, "exam_date is required to generate a study plan")
            return generate_study_plan(db, student_id, subject_id, exam_date, hours_per_day)
        if action in {"get", "get_latest"}:
            query = db.query(StudyPlan).filter_by(student_id=student_id)
            if action == "get":
                plan_id = payload.value("plan_id")
                if plan_id is None:
                    raise ToolValidationError(self.name, "plan_id is required")
                plan = query.filter_by(id=plan_id).first()
            else:
                if subject_id is not None:
                    require_subject_owner(db, student_id, subject_id, self.name)
                    query = query.filter_by(subject_id=subject_id)
                exam_date = payload.value("exam_date")
                if exam_date is not None:
                    if isinstance(exam_date, str):
                        exam_date = date.fromisoformat(exam_date)
                    query = query.filter_by(exam_date=exam_date)
                plan = query.order_by(StudyPlan.created_at.desc(), StudyPlan.id.desc()).first()
            return get_study_plan(db, plan.id) if plan else None
        raise ToolValidationError(self.name, f"Unsupported study-plan action: {action}")


@register_tool
class PYQAnalysisTool(BaseTool):
    name = "pyq_analysis"
    description = "Analyze past-question trends, topic frequency, and priority for a student-owned subject."
    input_model = SubjectToolRequest

    async def execute(self, payload):
        from app.services.pyq_service import (
            analyze_exam_trends,
            generate_important_topics,
            generate_practice_questions,
            get_topic_frequency,
        )

        db, student_id = require_student(payload, self.name)
        require_subject_owner(db, student_id, payload.subject_id, self.name)
        action = payload.value("action", "all")
        if action == "trends":
            return analyze_exam_trends(db, payload.subject_id)
        if action == "important_topics":
            return generate_important_topics(db, payload.subject_id)
        if action == "topic_frequency":
            return get_topic_frequency(db, payload.subject_id)
        if action == "practice_questions":
            return generate_practice_questions(db, payload.subject_id, count=payload.value("count", 5))
        return {
            "trends": analyze_exam_trends(db, payload.subject_id),
            "important_topics": generate_important_topics(db, payload.subject_id),
            "topic_frequency": get_topic_frequency(db, payload.subject_id),
            "practice": (
                generate_practice_questions(db, payload.subject_id, count=5)
                if payload.value("include_practice", False)
                else None
            ),
        }