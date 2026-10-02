from app.db.models import StudyBlock
from app.services.calendar_service import get_events
from app.services.deadline_service import overdue_deadlines, upcoming_deadlines
from app.services.notification_service import generate_alerts, list_notifications
from app.services.reminder_service import generate_reminders, list_reminders
from app.services.scheduler_service import generate_study_schedule
from app.tools.base import BaseTool
from app.tools.common import require_student, require_subject_owner
from app.tools.registry import register_tool
from app.tools.schemas import StudentToolRequest


@register_tool
class CalendarTool(BaseTool):
	name = "calendar_events"
	description = "Retrieve calendar events for the current student within an optional time range."
	input_model = StudentToolRequest

	async def execute(self, payload):
		db, student_id = require_student(payload, self.name)
		return get_events(db, student_id, payload.value("start"), payload.value("end"))


@register_tool
class ScheduleTool(BaseTool):
	name = "study_schedule"
	description = "Retrieve scheduled study blocks or generate a schedule for owned subjects."
	input_model = StudentToolRequest

	async def execute(self, payload):
		db, student_id = require_student(payload, self.name)
		subject_ids = payload.value("subject_ids", [])
		start_time = payload.value("start_time")
		if subject_ids and start_time:
			for subject_id in subject_ids:
				require_subject_owner(db, student_id, subject_id, self.name)
			return generate_study_schedule(
				db, student_id, subject_ids, start_time,
				payload.value("session_length", 50), payload.value("break_minutes", 10),
			)
		return db.query(StudyBlock).filter_by(student_id=student_id).order_by(StudyBlock.start_time).all()


@register_tool
class DeadlineTool(BaseTool):
	name = "deadlines"
	description = "Retrieve upcoming or overdue deadlines for the current student."
	input_model = StudentToolRequest

	async def execute(self, payload):
		db, student_id = require_student(payload, self.name)
		return overdue_deadlines(db, student_id) if payload.value("action") == "overdue" else upcoming_deadlines(db, student_id)


@register_tool
class ReminderTool(BaseTool):
	name = "reminders"
	description = "List student reminders or generate reminders from upcoming deadlines."
	input_model = StudentToolRequest

	async def execute(self, payload):
		db, student_id = require_student(payload, self.name)
		if payload.value("generate_reminders", False):
			return generate_reminders(db, student_id)
		return list_reminders(db, student_id, pending_only=payload.value("pending_only", True))


@register_tool
class NotificationTool(BaseTool):
	name = "notifications"
	description = "Retrieve notifications or generate academic alerts for the current student."
	input_model = StudentToolRequest

	async def execute(self, payload):
		db, student_id = require_student(payload, self.name)
		if payload.value("generate_alerts", False):
			return generate_alerts(db, student_id)
		return list_notifications(db, student_id, unread_only=payload.value("unread_only", True))