from app.db.models import Habit, StudentGoal
from app.services.goals_service import create_goal, delete_goal, list_goals, update_goal
from app.services.habit_service import create_habit, delete_habit, habit_summary, list_habits, log_habit, update_habit
from app.services.productivity_service import analyze_productivity
from app.tools.base import BaseTool
from app.tools.common import require_student
from app.tools.exceptions import ToolValidationError
from app.tools.registry import register_tool
from app.tools.schemas import GoalToolRequest, HabitToolRequest, StudentToolRequest


@register_tool
class GoalTool(BaseTool):
	name = "goals"
	description = "List, create, or update goals belonging to the current student."
	input_model = GoalToolRequest

	async def execute(self, payload):
		db, student_id = require_student(payload, self.name)
		action = payload.value("action", "list")
		if action == "list":
			return list_goals(db, student_id, include_completed=payload.value("include_completed", True))
		fields = payload.value("fields", {})
		if action == "create":
			return create_goal(db, student_id, fields)
		if action == "update":
			goal_id = payload.value("goal_id")
			goal = db.query(StudentGoal).filter_by(id=goal_id, student_id=student_id).first()
			if goal is None:
				return None
			return update_goal(db, goal_id, fields)
		if action == "delete":
			goal = db.query(StudentGoal.id).filter_by(id=payload.value("goal_id"), student_id=student_id).first()
			return delete_goal(db, goal[0]) if goal else False
		raise ToolValidationError(self.name, f"Unsupported goal action: {action}")


@register_tool
class HabitTool(BaseTool):
	name = "habits"
	description = "List, create, or log habits belonging to the current student."
	input_model = HabitToolRequest

	async def execute(self, payload):
		db, student_id = require_student(payload, self.name)
		action = payload.value("action", "list")
		if action == "list":
			return habit_summary(db, student_id) if payload.value("include_summary", False) else list_habits(db, student_id, active_only=payload.value("active_only", True))
		fields = payload.value("fields", {})
		if action == "create":
			return create_habit(db, student_id, fields["habit_name"], fields["category"], fields.get("target_per_week", 7))
		if action == "log":
			habit = db.query(Habit).filter_by(id=payload.value("habit_id"), student_id=student_id).first()
			if habit is None:
				return None
			return log_habit(db, student_id, habit.id, fields["log_date"], fields.get("completed", True), fields.get("duration_minutes"), fields.get("notes"))
		if action == "update":
			habit = db.query(Habit.id).filter_by(id=payload.value("habit_id"), student_id=student_id).first()
			return update_habit(db, habit[0], fields) if habit else None
		if action == "delete":
			habit = db.query(Habit.id).filter_by(id=payload.value("habit_id"), student_id=student_id).first()
			return delete_habit(db, habit[0]) if habit else False
		raise ToolValidationError(self.name, f"Unsupported habit action: {action}")


@register_tool
class ProductivityAnalyticsTool(BaseTool):
	name = "productivity_analytics"
	description = "Calculate productivity, study consistency, and procrastination risks."
	input_model = StudentToolRequest

	async def execute(self, payload):
		db, student_id = require_student(payload, self.name)
		return analyze_productivity(db, student_id)