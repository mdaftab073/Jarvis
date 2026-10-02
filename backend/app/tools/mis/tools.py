from app.services.mis_sync_service import get_profile
from app.tools.base import BaseTool
from app.tools.common import require_student
from app.tools.registry import register_tool
from app.tools.schemas import StudentToolRequest


class _MISSnapshotTool(BaseTool):
	input_model = StudentToolRequest
	snapshot_field = ""

	async def execute(self, payload):
		db, student_id = require_student(payload, self.name)
		profile = get_profile(db, student_id)
		if profile is None:
			return None
		return getattr(profile, self.snapshot_field) if self.snapshot_field else profile


@register_tool
class MISProfileTool(_MISSnapshotTool):
	name = "mis_profile"
	description = "Retrieve the current student's persisted SVNIT MIS profile snapshot."


@register_tool
class MISAttendanceTool(_MISSnapshotTool):
	name = "mis_attendance"
	description = "Retrieve the current student's persisted SVNIT MIS attendance snapshot."
	snapshot_field = "attendance_json"


@register_tool
class MISResultTool(_MISSnapshotTool):
	name = "mis_results"
	description = "Retrieve the current student's persisted SVNIT MIS result snapshot."
	snapshot_field = "results_json"