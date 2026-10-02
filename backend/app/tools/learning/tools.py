from app.db.models import ExamQuestion
from app.models import Flashcard, FlashcardDeck, Topic, TopicMastery
from app.services.flashcard_service import FlashcardService
from app.services.learning_session_service import LearningSessionService
from app.services.mastery_service import MasteryService
from app.services.quiz_service import QuizService
from app.tools.base import BaseTool
from app.tools.common import require_student, require_subject_owner
from app.tools.exceptions import ToolValidationError
from app.tools.registry import register_tool
from app.tools.schemas import StudentToolRequest


@register_tool
class TopicMasteryTool(BaseTool):
	name = "topic_mastery"
	description = "Retrieve mastery records for the current student, optionally for one topic."
	input_model = StudentToolRequest

	async def execute(self, payload):
		db, student_id = require_student(payload, self.name)
		service = MasteryService(db)
		topic_id = payload.value("topic_id")
		if topic_id is not None:
			topic = db.query(Topic).filter_by(id=topic_id).first()
			if topic is None:
				return None
			require_subject_owner(db, student_id, topic.subject_id, self.name)
			return service.get_mastery(student_id, topic_id)
		subject_id = getattr(payload, "subject_id", None)
		records = service.list_mastery_for_student(student_id, limit=payload.value("limit", 100))
		if subject_id is not None:
			require_subject_owner(db, student_id, subject_id, self.name)
			topic_ids = {row.id for row in db.query(Topic.id).filter_by(subject_id=subject_id).all()}
			records = [record for record in records if record.topic_id in topic_ids]
		return records


@register_tool
class FlashcardTool(BaseTool):
	name = "flashcards"
	description = "Retrieve flashcards from a deck, topic, or subject owned by the current student."
	input_model = StudentToolRequest

	async def execute(self, payload):
		db, student_id = require_student(payload, self.name)
		service = FlashcardService(db)
		deck_id = payload.value("deck_id")
		topic_id = payload.value("topic_id")
		if deck_id is not None:
			deck = service.get_deck(deck_id)
			if deck is None:
				return []
			require_subject_owner(db, student_id, deck.subject_id, self.name)
			return service.get_flashcards_by_deck(deck_id, limit=payload.value("limit", 100))
		if topic_id is not None:
			topic = db.query(Topic).filter_by(id=topic_id).first()
			if topic is None:
				return []
			require_subject_owner(db, student_id, topic.subject_id, self.name)
			return service.get_flashcards_by_topic(topic_id, limit=payload.value("limit", 100))
		subject_id = getattr(payload, "subject_id", None)
		if subject_id is None:
			raise ToolValidationError(self.name, "deck_id, topic_id, or subject_id is required")
		require_subject_owner(db, student_id, subject_id, self.name)
		deck_ids = [row.id for row in db.query(FlashcardDeck.id).filter_by(subject_id=subject_id).all()]
		return db.query(Flashcard).filter(Flashcard.deck_id.in_(deck_ids)).limit(payload.value("limit", 100)).all() if deck_ids else []


@register_tool
class QuizTool(BaseTool):
	name = "quizzes"
	description = "Retrieve the student's quiz history or build a quiz from owned subject questions."
	input_model = StudentToolRequest

	async def execute(self, payload):
		db, student_id = require_student(payload, self.name)
		action = payload.value("action", "list")
		if action == "list":
			return QuizService(db).list_sessions(student_id, limit=payload.value("limit", 100))
		subject_id = getattr(payload, "subject_id", None)
		if subject_id is None:
			raise ToolValidationError(self.name, "subject_id is required to generate a quiz")
		require_subject_owner(db, student_id, subject_id, self.name)
		return db.query(ExamQuestion).filter_by(subject_id=subject_id).order_by(ExamQuestion.id.desc()).limit(payload.value("count", 10)).all()


@register_tool
class LearningSummaryTool(BaseTool):
	name = "learning_summary"
	description = "Summarize mastery, quiz history, study sessions, topic strengths, and learning risks."
	input_model = StudentToolRequest

	async def execute(self, payload):
		db, student_id = require_student(payload, self.name)
		mastery_records = MasteryService(db).list_mastery_for_student(student_id, limit=1000)
		quiz_sessions = QuizService(db).list_sessions(student_id, limit=1000)
		learning_sessions = LearningSessionService(db).list_for_student(student_id, limit=1000)
		topic_rows = db.query(Topic).join(TopicMastery, TopicMastery.topic_id == Topic.id).filter(TopicMastery.student_id == student_id).all()
		topic_names = {topic.id: topic.name for topic in topic_rows}
		weak = sorted((row for row in mastery_records if row.mastery_score < 50), key=lambda row: row.mastery_score)
		strong = sorted((row for row in mastery_records if row.mastery_score >= 75), key=lambda row: row.mastery_score, reverse=True)
		weak_topics = [{"topic_id": row.topic_id, "topic_name": topic_names.get(row.topic_id, f"Topic {row.topic_id}"), "mastery_score": row.mastery_score, "attempt_count": row.attempt_count} for row in weak[:10]]
		strong_topics = [{"topic_id": row.topic_id, "topic_name": topic_names.get(row.topic_id, f"Topic {row.topic_id}"), "mastery_score": row.mastery_score, "attempt_count": row.attempt_count} for row in strong[:10]]
		total_time = sum((session.duration_minutes or 0) for session in learning_sessions)
		activity_breakdown = {}
		for session in learning_sessions:
			activity_breakdown[session.activity_type] = activity_breakdown.get(session.activity_type, 0) + 1
		average_mastery = round(sum(row.mastery_score for row in mastery_records) / len(mastery_records), 2) if mastery_records else 0.0
		completed_quizzes = [session for session in quiz_sessions if session.score is not None]
		average_quiz_score = round(sum(session.score for session in completed_quizzes) / len(completed_quizzes), 2) if completed_quizzes else None
		recommendations = [f"Focus on '{row['topic_name']}' – mastery is only {row['mastery_score']:.0f}%." for row in weak_topics[:3]]
		if not completed_quizzes:
			recommendations.append("Take a quiz to test your knowledge and track progress.")
		if activity_breakdown.get("flashcard_review", 0) == 0:
			recommendations.append("Use flashcard review sessions to reinforce key concepts.")
		if total_time < 60:
			recommendations.append("Increase active study time – aim for at least 1 hour per day.")
		if average_mastery < 40:
			recommendations.append("Overall mastery is low. Consider a structured revision plan.")
		readiness = "HIGH" if average_mastery >= 75 else "MEDIUM" if average_mastery >= 50 else "LOW"
		risks = []
		if average_mastery < 30:
			risks.append({"message": "Mastery critically low – risk of exam failure."})
		if len(weak_topics) > 5:
			risks.append({"message": "Many weak topics – revision load may be unmanageable."})
		data = {"weak_topics": weak_topics, "strong_topics": strong_topics, "average_mastery": average_mastery, "average_quiz_score": average_quiz_score, "total_sessions": len(learning_sessions), "total_time_minutes": round(total_time, 2), "activity_breakdown": activity_breakdown, "overall_readiness": readiness}
		summary = f"Student {student_id}: avg mastery {average_mastery:.0f}%, {len(weak_topics)} weak topic(s), {len(strong_topics)} strong topic(s), readiness {readiness}."
		return {"summary": summary, "recommendations": recommendations, "data": data, "risks": risks}