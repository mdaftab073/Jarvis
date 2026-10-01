from app.agents.base import BaseAgent
from app.db.models import DigitalTwinSnapshot, ExamQuestion, Semester, SemesterSubject, Subject
from app.models import Topic, TopicMastery
from app.services.copilot_service import get_active_semester_guidance
from app.services.deadline_service import upcoming_deadlines
from app.services.grade_service import grade_analytics
from app.services.time_service import utc_now_naive


class SemesterCopilotAgent(BaseAgent):
    name = "semester_copilot"

    def execute(self, context: dict) -> dict:
        db = context["db"]
        student_id = context["student_id"]
        guidance = get_active_semester_guidance(db, student_id)
        grade_summary = grade_analytics(db, student_id)
        deadlines = upcoming_deadlines(db, student_id)
        exams = [item for item in deadlines if item.type == "EXAM"]
        now = utc_now_naive()
        countdowns = [
            {"deadline_id": exam.id, "title": exam.title, "due_date": exam.due_date,
             "days_remaining": max(0, (exam.due_date - now).days)}
            for exam in exams
        ]
        weak_rows = (
            db.query(TopicMastery, Topic, Subject)
            .join(Topic, Topic.id == TopicMastery.topic_id)
            .join(Subject, Subject.id == Topic.subject_id)
            .filter(TopicMastery.student_id == student_id, TopicMastery.mastery_score < 50)
            .order_by(TopicMastery.mastery_score)
            .all()
        )
        weak_topics = [
            {"topic_id": topic.id, "topic": topic.name, "subject_id": subject.id,
             "subject": subject.name, "mastery_score": mastery.mastery_score}
            for mastery, topic, subject in weak_rows
        ]
        subject_ids = {
            subject["subject_id"]
            for semester in guidance
            for subject in semester.get("priority_subjects", [])
        }
        if not subject_ids:
            subject_ids = {
                row.subject_id
                for row in db.query(SemesterSubject.subject_id)
                .join(Semester, Semester.id == SemesterSubject.semester_id)
                .filter(Semester.student_id == student_id, Semester.status == "ACTIVE")
                .all()
            }
        pyq_coverage = {
            subject_id: db.query(ExamQuestion.id).filter_by(subject_id=subject_id).count()
            for subject_id in sorted(subject_ids)
        }
        revision_roadmap = [
            {"subject_id": topic["subject_id"], "subject": topic["subject"],
             "topic": topic["topic"], "priority": index + 1,
             "reason": "mastery below 50%"}
            for index, topic in enumerate(weak_topics[:10])
        ]
        snapshot = (
            db.query(DigitalTwinSnapshot)
            .filter_by(student_id=student_id)
            .order_by(DigitalTwinSnapshot.captured_at.desc())
            .first()
        )
        current_readiness = snapshot.overall_readiness if snapshot else None
        forecast = {
            "current_readiness": current_readiness,
            "status": "AT_RISK" if current_readiness is not None and current_readiness < 60 else "ON_TRACK" if current_readiness is not None else "UNKNOWN",
            "basis": "latest digital-twin snapshot; not a statistical prediction",
        }
        summary = (
            f"Semester copilot found {len(countdowns)} exam deadlines and "
            f"{len(weak_topics)} weak topics."
        )
        recommendations = [
            "Prioritize weak topics with scheduled revision blocks." if weak_topics else "Continue regular revision and practice.",
            "Increase PYQ coverage for subjects with few indexed exam questions." if any(value < 5 for value in pyq_coverage.values()) else "PYQ question coverage is available for active subjects.",
        ]
        risks = []
        if forecast["status"] == "AT_RISK":
            risks.append({"type": "READINESS", "severity": "HIGH", "score": current_readiness})
        risks.extend({"type": "EXAM_COUNTDOWN", "severity": "HIGH" if item["days_remaining"] <= 7 else "MEDIUM", **item} for item in countdowns)
        return self.response(
            summary,
            recommendations,
            data={
                "semesters": guidance,
                "exam_countdowns": countdowns,
                "revision_roadmap": revision_roadmap,
                "weak_topics": weak_topics,
                "pyq_coverage": pyq_coverage,
                "readiness_forecast": forecast,
                "grade_analytics": grade_summary,
            },
            risks=risks,
        )
