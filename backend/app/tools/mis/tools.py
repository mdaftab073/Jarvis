from app.services.mis_sync_service import (
    MISSyncError,
    get_profile,
    sync_profile,
)
from app.services.mis.client import MISClientError
from app.tools.base import BaseTool
from app.tools.common import require_student
from app.tools.exceptions import ToolExecutionError, ToolValidationError
from app.tools.registry import register_tool
from app.tools.schemas import StudentToolRequest


class _MISSnapshotTool(BaseTool):
	input_model = StudentToolRequest
	snapshot_field = ""

	async def execute(self, payload):
		db, student_id = require_student(payload, self.name)
		profile = get_profile(db, student_id)
		if profile is None:
			raise ToolValidationError(self.name, "No SVNIT MIS data is available for this student")
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


@register_tool
class MISGetAttendanceTool(MISAttendanceTool):
	name = "mis_get_attendance"
	description = "Retrieve the current student's saved SVNIT MIS attendance snapshot."


@register_tool
class MISGetResultsTool(MISResultTool):
	name = "mis_get_results"
	description = "Retrieve the current student's saved SVNIT MIS results snapshot."


@register_tool
class MISGetTimetableTool(_MISSnapshotTool):
	name = "mis_get_timetable"
	description = "Retrieve the current student's saved SVNIT MIS timetable snapshot."
	snapshot_field = "timetable_json"


@register_tool
class MISSyncProfileTool(BaseTool):
	name = "mis_sync_profile"
	description = "Refresh the current student's profile through the dedicated SVNIT MIS sync service."
	input_model = StudentToolRequest

	async def execute(self, payload):
		db, student_id = require_student(payload, self.name)
		try:
			profile, count = sync_profile(db, student_id)
		except (MISClientError, MISSyncError) as error:
			raise ToolExecutionError(self.name, "SVNIT MIS profile synchronization failed") from error
		return {"student_id": student_id, "records_processed": count, "synced_at": profile.synced_at}