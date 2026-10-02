from app.db.models import DigitalTwinSnapshot, ExamQuestion, Semester, SemesterSubject, Subject
from app.models import Topic, TopicMastery
from app.services.academic_agent_service import generate_agent_response
from app.services.copilot_service import generate_copilot_guidance, get_active_semester_guidance
from app.services.deadline_service import upcoming_deadlines
from app.services.grade_service import grade_analytics
from app.services.memory_service import (
	build_student_profile,
	generate_profile_summary,
	get_memories,
	get_readiness_trend,
)
from app.services.semester_service import detect_academic_risks
from app.services.dashboard_service import get_dashboard
from app.services.time_service import utc_now_naive
from app.tools.base import BaseTool
from app.tools.common import require_student
from app.tools.exceptions import ToolValidationError
from app.tools.registry import register_tool
from app.tools.schemas import StudentToolRequest, ToolRequest


@register_tool
class MemoryTool(BaseTool):
	name = "student_memory"
	description = "Retrieve the student's profile, memories, summary, or readiness trend."
	input_model = StudentToolRequest

	async def execute(self, payload):
		_, student_id = require_student(payload, self.name)
		db = payload.db
		action = payload.value("action", "context")
		if action == "profile":
			return build_student_profile(student_id, db=db)
		if action == "memories":
			return get_memories(student_id, db=db)
		if action == "trend":
			return get_readiness_trend(student_id, db=db)
		if action == "summary":
			return generate_profile_summary(student_id, db=db)
		return {
			"profile": build_student_profile(student_id, db=db),
			"memories": get_memories(student_id, db=db),
			"readiness_trend": get_readiness_trend(student_id, db=db),
			"summary": generate_profile_summary(student_id, db=db),
		}


@register_tool
class SemesterGuidanceTool(BaseTool):
	name = "semester_guidance"
	description = "Retrieve active semester health guidance and risks for the current student."
	input_model = StudentToolRequest

	async def execute(self, payload):
		db, student_id = require_student(payload, self.name)
		semester_id = payload.value("semester_id")
		if semester_id is not None:
			semester = db.query(Semester).filter_by(id=semester_id, student_id=student_id).first()
			if semester is None:
				return None
			action = payload.value("action")
			if action == "guidance":
				return {"guidance": generate_copilot_guidance(db, semester_id)}
			if action == "risks":
				return {"risks": detect_academic_risks(db, semester_id)}
			return {"guidance": generate_copilot_guidance(db, semester_id), "risks": detect_academic_risks(db, semester_id)}
		return get_active_semester_guidance(db, student_id)


@register_tool
class SemesterCopilotTool(BaseTool):
	name = "semester_copilot"
	description = "Build the student's semester exam countdown, readiness, revision roadmap, and grade view."
	input_model = StudentToolRequest

	async def execute(self, payload):
		db, student_id = require_student(payload, self.name)
		guidance = get_active_semester_guidance(db, student_id)
		grade_summary = grade_analytics(db, student_id)
		deadlines = upcoming_deadlines(db, student_id)
		exams = [item for item in deadlines if item.type == "EXAM"]
		now = utc_now_naive()
		countdowns = [{"deadline_id": exam.id, "title": exam.title, "due_date": exam.due_date, "days_remaining": max(0, (exam.due_date - now).days)} for exam in exams]
		weak_rows = (
			db.query(TopicMastery, Topic, Subject)
			.join(Topic, Topic.id == TopicMastery.topic_id)
			.join(Subject, Subject.id == Topic.subject_id)
			.filter(TopicMastery.student_id == student_id, TopicMastery.mastery_score < 50)
			.order_by(TopicMastery.mastery_score)
			.all()
		)
		weak_topics = [{"topic_id": topic.id, "topic": topic.name, "subject_id": subject.id, "subject": subject.name, "mastery_score": mastery.mastery_score} for mastery, topic, subject in weak_rows]
		subject_ids = {item["subject_id"] for semester in guidance for item in semester.get("priority_subjects", [])}
		if not subject_ids:
			subject_ids = {row.subject_id for row in db.query(SemesterSubject.subject_id).join(Semester, Semester.id == SemesterSubject.semester_id).filter(Semester.student_id == student_id, Semester.status == "ACTIVE").all()}
		pyq_coverage = {subject_id: db.query(ExamQuestion.id).filter_by(subject_id=subject_id).count() for subject_id in sorted(subject_ids)}
		roadmap = [{"subject_id": item["subject_id"], "subject": item["subject"], "topic": item["topic"], "priority": index + 1, "reason": "mastery below 50%"} for index, item in enumerate(weak_topics[:10])]
		snapshot = db.query(DigitalTwinSnapshot).filter_by(student_id=student_id).order_by(DigitalTwinSnapshot.captured_at.desc()).first()
		current_readiness = snapshot.overall_readiness if snapshot else None
		forecast = {"current_readiness": current_readiness, "status": "AT_RISK" if current_readiness is not None and current_readiness < 60 else "ON_TRACK" if current_readiness is not None else "UNKNOWN", "basis": "latest digital-twin snapshot; not a statistical prediction"}
		summary = f"Semester copilot found {len(countdowns)} exam deadlines and {len(weak_topics)} weak topics."
		recommendations = ["Prioritize weak topics with scheduled revision blocks." if weak_topics else "Continue regular revision and practice.", "Increase PYQ coverage for subjects with few indexed exam questions." if any(value < 5 for value in pyq_coverage.values()) else "PYQ question coverage is available for active subjects."]
		risks = ([{"type": "READINESS", "severity": "HIGH", "score": current_readiness}] if forecast["status"] == "AT_RISK" else [])
		risks.extend({"type": "EXAM_COUNTDOWN", "severity": "HIGH" if item["days_remaining"] <= 7 else "MEDIUM", **item} for item in countdowns)
		return {"summary": summary, "recommendations": recommendations, "data": {"semesters": guidance, "exam_countdowns": countdowns, "revision_roadmap": roadmap, "weak_topics": weak_topics, "pyq_coverage": pyq_coverage, "readiness_forecast": forecast, "grade_analytics": grade_summary}, "risks": risks}


@register_tool
class AcademicStrategyTool(BaseTool):
	name = "academic_strategy"
	description = "Generate a concise academic strategy from collected academic context."
	input_model = ToolRequest

	async def execute(self, payload):
		goal = payload.value("goal", "")
		context = payload.value("strategy_context", {})
		if not isinstance(context, dict):
			raise ToolValidationError(self.name, "strategy_context must be an object")
		return generate_agent_response(goal, context)


@register_tool
class AcademicDashboardTool(BaseTool):
	name = "academic_dashboard"
	description = "Retrieve the current student's academic dashboard summary."
	input_model = StudentToolRequest

	async def execute(self, payload):
		_, student_id = require_student(payload, self.name)
		return get_dashboard(payload.db, student_id)