from app.agents.base import BaseAgent
from app.services.academic_profile_service import academic_summary
from app.services.attendance_service import attendance_summary
from app.services.calendar_service import get_events
from app.services.deadline_service import upcoming_deadlines
from app.services.notification_service import generate_alerts, list_notifications
from app.services.reminder_service import generate_reminders, list_reminders
from app.services.scheduler_service import generate_study_schedule
from app.db.models import StudyBlock


class AcademicProfileAgent(BaseAgent):
    name = "academic_profile"

    def execute(self, context: dict) -> dict:
        data = academic_summary(context["db"], context["student_id"])
        return self.response("Academic profile summary loaded.", data=data)


class AttendanceAgent(BaseAgent):
    name = "attendance"

    def execute(self, context: dict) -> dict:
        items = attendance_summary(context["db"], context["student_id"])
        risks = [{"subject_id": item["record"].subject_id, "severity": item["risk"], "attendance_percentage": item["record"].attendance_percentage} for item in items if item["risk"] != "SAFE"]
        return self.response(f"Attendance reviewed across {len(items)} subjects.", ["Prioritize classes in warning or critical subjects." ] if risks else [], data={"attendance": items}, risks=risks)


class DeadlineAgent(BaseAgent):
    name = "deadline"

    def execute(self, context: dict) -> dict:
        items = upcoming_deadlines(context["db"], context["student_id"])
        return self.response(f"Found {len(items)} upcoming deadlines.", [f"Prioritize {items[0].title}." ] if items else [], data={"deadlines": items})


class NotificationAgent(BaseAgent):
    name = "notification"

    def execute(self, context: dict) -> dict:
        db, student_id = context["db"], context["student_id"]
        items = generate_alerts(db, student_id) if context.get("generate_alerts") else list_notifications(db, student_id, unread_only=True)
        return self.response(f"{len(items)} student notifications are available.", data={"notifications": items})


class CalendarAgent(BaseAgent):
    name = "calendar"

    def execute(self, context: dict) -> dict:
        items = get_events(context["db"], context["student_id"], context.get("start"), context.get("end"))
        return self.response(f"Found {len(items)} calendar events.", data={"calendar": items})


class SchedulerAgent(BaseAgent):
    name = "scheduler"

    def execute(self, context: dict) -> dict:
        db, student_id = context["db"], context["student_id"]
        if context.get("subject_ids") and context.get("start_time"):
            items = generate_study_schedule(db, student_id, context["subject_ids"], context["start_time"], context.get("session_length", 50), context.get("break_minutes", 10))
        else:
            items = db.query(StudyBlock).filter_by(student_id=student_id).order_by(StudyBlock.start_time).all()
        return self.response(f"Study schedule contains {len(items)} blocks.", data={"study_blocks": items})


class ReminderAgent(BaseAgent):
    name = "reminder"

    def execute(self, context: dict) -> dict:
        db, student_id = context["db"], context["student_id"]
        items = generate_reminders(db, student_id) if context.get("generate_reminders") else list_reminders(db, student_id)
        return self.response(f"Found {len(items)} pending reminders.", data={"reminders": items})
