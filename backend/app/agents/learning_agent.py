"""Phase 14 – LearningAgent.

Aggregates mastery data, quiz history, learning sessions, and flashcard
usage to produce a personalised learning report.  All heavy lifting is
delegated to the existing service layer – no business logic is duplicated.
"""

import logging
from typing import List

from app.agents.base import BaseAgent
from app.services.mastery_service import MasteryService
from app.services.quiz_service import QuizService
from app.services.learning_session_service import LearningSessionService
from app.services.flashcard_service import FlashcardService
from app.models import Topic

logger = logging.getLogger(__name__)

WEAK_THRESHOLD = 50.0
STRONG_THRESHOLD = 75.0


class LearningAgent(BaseAgent):
    """Analyse a student's learning state and generate recommendations."""

    name = "learning"

    def execute(self, context: dict) -> dict:
        db = context.get("db")
        student_id = context.get("student_id")
        if db is None or student_id is None:
            return self.response(
                "Missing db or student_id in context.",
                recommendations=[],
                data={},
                risks=[{"message": "LearningAgent requires db and student_id"}],
            )

        mastery_svc = MasteryService(db)
        quiz_svc = QuizService(db)
        session_svc = LearningSessionService(db)

        # ── Gather data ───────────────────────────────────────────────
        mastery_records = mastery_svc.list_mastery_for_student(
            student_id=student_id, limit=1000,
        )
        quiz_sessions = quiz_svc.list_sessions(
            student_id=student_id, limit=1000,
        )
        learning_sessions = session_svc.list_for_student(
            student_id=student_id, limit=1000,
        )

        # ── Compute weak / strong topics ──────────────────────────────
        topic_cache: dict = {}

        def _topic_name(topic_id: int) -> str:
            if topic_id not in topic_cache:
                t = db.query(Topic).filter(Topic.id == topic_id).first()
                topic_cache[topic_id] = t.name if t else f"Topic {topic_id}"
            return topic_cache[topic_id]

        weak = sorted(
            [m for m in mastery_records if m.mastery_score < WEAK_THRESHOLD],
            key=lambda m: m.mastery_score,
        )
        strong = sorted(
            [m for m in mastery_records if m.mastery_score >= STRONG_THRESHOLD],
            key=lambda m: m.mastery_score,
            reverse=True,
        )

        weak_topics = [
            {
                "topic_id": m.topic_id,
                "topic_name": _topic_name(m.topic_id),
                "mastery_score": m.mastery_score,
                "attempt_count": m.attempt_count,
            }
            for m in weak[:10]
        ]
        strong_topics = [
            {
                "topic_id": m.topic_id,
                "topic_name": _topic_name(m.topic_id),
                "mastery_score": m.mastery_score,
                "attempt_count": m.attempt_count,
            }
            for m in strong[:10]
        ]

        # ── Aggregate session data ────────────────────────────────────
        total_time = sum((s.duration_minutes or 0) for s in learning_sessions)
        activity_breakdown: dict = {}
        for s in learning_sessions:
            activity_breakdown[s.activity_type] = (
                activity_breakdown.get(s.activity_type, 0) + 1
            )

        avg_mastery = (
            round(
                sum(m.mastery_score for m in mastery_records) / len(mastery_records), 2,
            )
            if mastery_records
            else 0.0
        )

        # ── Quiz analysis ─────────────────────────────────────────────
        completed_quizzes = [q for q in quiz_sessions if q.score is not None]
        avg_quiz_score = (
            round(
                sum(q.score for q in completed_quizzes) / len(completed_quizzes), 2,
            )
            if completed_quizzes
            else None
        )

        # ── Recommendations ───────────────────────────────────────────
        recommendations: List[str] = []
        for w in weak_topics[:3]:
            recommendations.append(
                f"Focus on '{w['topic_name']}' – mastery is only {w['mastery_score']:.0f}%."
            )
        if not completed_quizzes:
            recommendations.append(
                "Take a quiz to test your knowledge and track progress."
            )
        if activity_breakdown.get("flashcard_review", 0) == 0:
            recommendations.append(
                "Use flashcard review sessions to reinforce key concepts."
            )
        if total_time < 60:
            recommendations.append(
                "Increase active study time – aim for at least 1 hour per day."
            )
        if avg_mastery < 40:
            recommendations.append(
                "Overall mastery is low. Consider a structured revision plan."
            )

        # ── Overall readiness ─────────────────────────────────────────
        if avg_mastery >= 75:
            readiness = "HIGH"
        elif avg_mastery >= 50:
            readiness = "MEDIUM"
        else:
            readiness = "LOW"

        # ── Summary ───────────────────────────────────────────────────
        summary = (
            f"Student {student_id}: avg mastery {avg_mastery:.0f}%, "
            f"{len(weak_topics)} weak topic(s), "
            f"{len(strong_topics)} strong topic(s), "
            f"readiness {readiness}."
        )

        data = {
            "weak_topics": weak_topics,
            "strong_topics": strong_topics,
            "average_mastery": avg_mastery,
            "average_quiz_score": avg_quiz_score,
            "total_sessions": len(learning_sessions),
            "total_time_minutes": round(total_time, 2),
            "activity_breakdown": activity_breakdown,
            "overall_readiness": readiness,
        }

        risks = []
        if avg_mastery < 30:
            risks.append({"message": "Mastery critically low – risk of exam failure."})
        if len(weak_topics) > 5:
            risks.append({"message": "Many weak topics – revision load may be unmanageable."})

        return self.response(
            summary=summary,
            recommendations=recommendations,
            data=data,
            risks=risks,
        )
