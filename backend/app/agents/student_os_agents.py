from app.agents.base import BaseAgent


class AcademicProfileAgent(BaseAgent):
    name = "academic_profile"

    def execute(self, context: dict) -> dict:
        data = self.invoke_tool("academic_profile", context)
        return self.response("Academic profile summary loaded.", data=data)


class AttendanceAgent(BaseAgent):
    name = "attendance"

    def execute(self, context: dict) -> dict:
        items = self.invoke_tool("attendance_summary", context)
        risks = [{"subject_id": item["record"].subject_id, "severity": item["risk"], "attendance_percentage": item["record"].attendance_percentage} for item in items if item["risk"] != "SAFE"]
        return self.response(f"Attendance reviewed across {len(items)} subjects.", ["Prioritize classes in warning or critical subjects." ] if risks else [], data={"attendance": items}, risks=risks)


class DeadlineAgent(BaseAgent):
    name = "deadline"

    def execute(self, context: dict) -> dict:
        items = self.invoke_tool("deadlines", context)
        return self.response(f"Found {len(items)} upcoming deadlines.", [f"Prioritize {items[0].title}." ] if items else [], data={"deadlines": items})


class NotificationAgent(BaseAgent):
    name = "notification"

    def execute(self, context: dict) -> dict:
        items = self.invoke_tool("notifications", context)
        return self.response(f"{len(items)} student notifications are available.", data={"notifications": items})


class CalendarAgent(BaseAgent):
    name = "calendar"

    def execute(self, context: dict) -> dict:
        items = self.invoke_tool("calendar_events", context)
        return self.response(f"Found {len(items)} calendar events.", data={"calendar": items})


class SchedulerAgent(BaseAgent):
    name = "scheduler"

    def execute(self, context: dict) -> dict:
        items = self.invoke_tool("study_schedule", context)
        return self.response(f"Study schedule contains {len(items)} blocks.", data={"study_blocks": items})


class ReminderAgent(BaseAgent):
    name = "reminder"

    def execute(self, context: dict) -> dict:
        items = self.invoke_tool("reminders", context)
        return self.response(f"Found {len(items)} pending reminders.", data={"reminders": items})
