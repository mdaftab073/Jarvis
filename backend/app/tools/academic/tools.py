from app.db.models import Course, Subject
from app.services.academic_profile_service import academic_summary
from app.services.attendance_service import attendance_summary
from app.services.grade_service import grade_analytics
from app.services.performance_service import (
    calculate_exam_readiness,
    generate_personalized_recommendations,
    get_strong_topics,
    get_weak_topics,
)
from app.tools.base import BaseTool
from app.tools.common import require_student, require_subject_owner
from app.tools.registry import register_tool
from app.tools.schemas import StudentToolRequest, SubjectToolRequest


@register_tool
class StudentSubjectsTool(BaseTool):
    name = "student_subjects"
    description = "List subjects belonging to the current student, optionally filtered by name or ID."
    input_model = StudentToolRequest

    async def execute(self, payload):
        db, student_id = require_student(payload, self.name)
        subjects = (
            db.query(Subject)
            .join(Course, Course.id == Subject.course_id)
            .filter(Course.student_id == student_id)
            .order_by(Subject.name.asc())
            .all()
        )
        goal = getattr(payload, "goal", "").casefold()
        matched = [subject for subject in subjects if subject.name.casefold() in goal]
        if matched:
            return matched
        subject_id = getattr(payload, "subject_id", None)
        if subject_id is not None:
            return [subject for subject in subjects if subject.id == subject_id]
        return subjects


@register_tool
class AcademicProfileTool(BaseTool):
    name = "academic_profile"
    description = "Fetch the student's academic profile summary and associated counts."
    input_model = StudentToolRequest

    async def execute(self, payload):
        db, student_id = require_student(payload, self.name)
        return academic_summary(db, student_id)


@register_tool
class GradesTool(BaseTool):
    name = "grades"
    description = "Fetch grade analytics for the current student."
    input_model = StudentToolRequest

    async def execute(self, payload):
        db, student_id = require_student(payload, self.name)
        return grade_analytics(db, student_id)


@register_tool
class AttendanceSummaryTool(BaseTool):
    name = "attendance_summary"
    description = "Fetch student attendance records, risks, and recovery counts."
    input_model = StudentToolRequest

    async def execute(self, payload):
        db, student_id = require_student(payload, self.name)
        return attendance_summary(db, student_id)


class _SubjectMetricTool(BaseTool):
    input_model = SubjectToolRequest

    def context(self, payload):
        db, student_id = require_student(payload, self.name)
        require_subject_owner(db, student_id, payload.subject_id, self.name)
        return db, student_id


@register_tool
class ExamReadinessTool(_SubjectMetricTool):
    name = "exam_readiness"
    description = "Calculate exam readiness for a student-owned subject."

    async def execute(self, payload):
        db, student_id = self.context(payload)
        return calculate_exam_readiness(db, student_id, payload.subject_id)


@register_tool
class WeakTopicsTool(_SubjectMetricTool):
    name = "weak_topics"
    description = "List weak topics for a student-owned subject."

    async def execute(self, payload):
        db, student_id = self.context(payload)
        return get_weak_topics(db, student_id, payload.subject_id)


@register_tool
class StrongTopicsTool(_SubjectMetricTool):
    name = "strong_topics"
    description = "List strong topics for a student-owned subject."

    async def execute(self, payload):
        db, student_id = self.context(payload)
        return get_strong_topics(db, student_id, payload.subject_id)


@register_tool
class PersonalizedRecommendationsTool(_SubjectMetricTool):
    name = "personalized_recommendations"
    description = "Generate personalized study recommendations for a student-owned subject."

    async def execute(self, payload):
        db, student_id = self.context(payload)
        return generate_personalized_recommendations(db, student_id, payload.subject_id)