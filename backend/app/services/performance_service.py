import json
import logging
import math
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.study_plan_types import StudyTaskStatus
from app.db.models import (
    Course,
    ExamQuestion,
    PracticeQuestionAttempt,
    PracticeSession,
    Student,
    StudentTopicPerformance,
    StudyPlan,
    StudyTask,
    Subject,
)
from app.services.pyq_service import generate_practice_questions, get_topic_frequency

logger = logging.getLogger(__name__)


def _now_utc_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _validate_student_subject(db: Session, student_id: int, subject_id: int):
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is None:
        raise ValueError("Student not found")
    subject = (
        db.query(Subject)
        .join(Course, Subject.course_id == Course.id)
        .filter(Subject.id == subject_id, Course.student_id == student_id)
        .first()
    )
    if subject is None:
        raise ValueError("Subject not found for this student")
    return subject


def _calculate_mastery(
    attempts: int,
    correct_answers: int,
    confidence_score: float,
    last_practiced_at: datetime | None,
    now: datetime | None = None,
):
    if attempts <= 0:
        return 0.0
    accuracy = correct_answers / attempts
    evidence = min(1.0, attempts / 5)
    confidence = max(0.0, min(100.0, confidence_score)) / 100
    current_time = now or _now_utc_naive()
    if last_practiced_at is None:
        recency = 0.0
    else:
        practiced_at = last_practiced_at.replace(tzinfo=None)
        age_days = max(0.0, (current_time - practiced_at).total_seconds() / 86400)
        recency = math.exp(-age_days / 60)
    base_score = 100 * (
        0.65 * accuracy
        + 0.20 * confidence
        + 0.15 * evidence
    )
    reliability = 0.60 + 0.40 * evidence
    return round(base_score * reliability * (0.85 + 0.15 * recency), 2)


def update_topic_mastery(
    db: Session,
    student_id: int,
    subject_id: int,
    topic: str,
    is_correct: bool,
    confidence_score: float = 50,
    practiced_at: datetime | None = None,
):
    _validate_student_subject(db, student_id, subject_id)
    normalized_topic = " ".join(topic.strip().split())
    if not normalized_topic:
        raise ValueError("topic cannot be empty")
    if not 0 <= confidence_score <= 100:
        raise ValueError("confidence_score must be between 0 and 100")

    performance = (
        db.query(StudentTopicPerformance)
        .filter_by(
            student_id=student_id,
            subject_id=subject_id,
            topic=normalized_topic,
        )
        .with_for_update()
        .first()
    )
    if performance is None:
        performance = StudentTopicPerformance(
            student_id=student_id,
            subject_id=subject_id,
            topic=normalized_topic,
            attempts=0,
            correct_answers=0,
            incorrect_answers=0,
            confidence_score=confidence_score,
            mastery_score=0,
        )
        db.add(performance)
        db.flush()

    prior_attempts = performance.attempts
    performance.attempts += 1
    if is_correct:
        performance.correct_answers += 1
    else:
        performance.incorrect_answers += 1
    performance.confidence_score = (
        performance.confidence_score * prior_attempts + confidence_score
    ) / performance.attempts
    performance.last_practiced_at = practiced_at or _now_utc_naive()
    performance.mastery_score = _calculate_mastery(
        attempts=performance.attempts,
        correct_answers=performance.correct_answers,
        confidence_score=performance.confidence_score,
        last_practiced_at=performance.last_practiced_at,
    )
    logger.info(
        "Updated topic mastery: student_id=%d subject_id=%d topic=%s attempts=%d mastery=%.2f",
        student_id,
        subject_id,
        normalized_topic,
        performance.attempts,
        performance.mastery_score,
    )
    return performance


def _parse_json(content: str):
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.I)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start >= 0 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise ValueError("Grading service returned invalid JSON")


def create_practice_session(
    db: Session,
    student_id: int,
    subject_id: int,
    count: int = 10,
):
    subject = _validate_student_subject(db, student_id, subject_id)
    generated = generate_practice_questions(db, subject_id, count=count)
    questions = generated.get("questions", [])
    if not questions:
        raise ValueError("No practice questions could be generated")

    session = PracticeSession(
        student_id=student_id,
        subject_id=subject_id,
        started_at=_now_utc_naive(),
        total_questions=len(questions),
    )
    db.add(session)
    db.flush()

    attempts = []
    for question in questions:
        expected_answer = question.get("expected_answer")
        if not expected_answer:
            raise ValueError("Practice question is missing its answer key")
        attempt = PracticeQuestionAttempt(
            practice_session_id=session.id,
            question_text=question["question"],
            topic=question.get("topic") or "General review",
            difficulty=question.get("difficulty") or "Medium",
            expected_answer=expected_answer,
            confidence_score=50,
        )
        db.add(attempt)
        attempts.append(attempt)

    db.commit()
    for attempt in attempts:
        db.refresh(attempt)
    db.refresh(session)
    logger.info(
        "Created practice session id=%d student_id=%d subject_id=%d questions=%d",
        session.id,
        student_id,
        subject_id,
        len(attempts),
    )
    return {
        "session": session,
        "subject_name": subject.name,
        "attempts": attempts,
    }


def _grade_attempts(attempts: list[PracticeQuestionAttempt], answers: dict):
    from app.services.llm_service import client

    grading_input = [
        {
            "attempt_id": attempt.id,
            "question": attempt.question_text,
            "expected_answer": attempt.expected_answer,
            "student_answer": answers[attempt.id]["student_answer"],
        }
        for attempt in attempts
    ]
    prompt = (
        "Grade each student answer against its expected answer. Be lenient to "
        "equivalent wording but do not award unsupported claims. Return only a "
        "JSON array with attempt_id, is_correct (boolean), score (0 to 100), "
        "and concise feedback. A response is correct when it demonstrates the "
        "core expected concepts.\n"
        f"Answers: {json.dumps(grading_input, ensure_ascii=True)}"
    )
    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    parsed = _parse_json(response.choices[0].message.content or "[]")
    if isinstance(parsed, dict):
        parsed = parsed.get("results", [])
    grades = {}
    for grade in parsed:
        if not isinstance(grade, dict):
            continue
        try:
            attempt_id = int(grade["attempt_id"])
            score = max(0.0, min(100.0, float(grade.get("score", 0))))
        except (KeyError, TypeError, ValueError):
            continue
        grades[attempt_id] = {
            "is_correct": (
                grade.get("is_correct")
                if isinstance(grade.get("is_correct"), bool)
                else score >= 70
            ),
            "score": score,
            "feedback": str(grade.get("feedback") or "Reviewed against the expected answer."),
        }
    if set(grades) != {attempt.id for attempt in attempts}:
        raise ValueError("Grading service did not return a result for each answer")
    return grades


def complete_practice_session(
    db: Session,
    session_id: int,
    answers: list[dict],
):
    session = (
        db.query(PracticeSession)
        .filter(PracticeSession.id == session_id)
        .with_for_update()
        .first()
    )
    if session is None:
        raise ValueError("Practice session not found")
    if session.completed_at is not None:
        raise ValueError("Practice session is already completed")

    attempts = (
        db.query(PracticeQuestionAttempt)
        .filter(PracticeQuestionAttempt.practice_session_id == session_id)
        .order_by(PracticeQuestionAttempt.id)
        .all()
    )
    answer_by_id = {}
    for answer in answers:
        attempt_id = int(answer["attempt_id"])
        if attempt_id in answer_by_id:
            raise ValueError("Duplicate answer attempt_id")
        answer_by_id[attempt_id] = answer
    if set(answer_by_id) != {attempt.id for attempt in attempts}:
        raise ValueError("Submit exactly one answer for every practice question")

    grades = _grade_attempts(attempts, answer_by_id)
    completed_at = _now_utc_naive()
    results = []
    topic_coverage = set()
    correct_answers = 0

    for attempt in attempts:
        answer = answer_by_id[attempt.id]
        grade = grades[attempt.id]
        attempt.student_answer = answer["student_answer"]
        attempt.is_correct = grade["is_correct"]
        attempt.score = grade["score"]
        attempt.confidence_score = float(answer.get("confidence_score", 50))
        topic = attempt.topic or "General review"
        topic_coverage.add(topic)
        correct_answers += int(attempt.is_correct)
        update_topic_mastery(
            db=db,
            student_id=session.student_id,
            subject_id=session.subject_id,
            topic=topic,
            is_correct=attempt.is_correct,
            confidence_score=attempt.confidence_score,
            practiced_at=completed_at,
        )
        results.append(
            {
                "attempt_id": attempt.id,
                "topic": topic,
                "is_correct": attempt.is_correct,
                "score": attempt.score,
                "feedback": grade["feedback"],
            }
        )

    session.completed_at = completed_at
    session.correct_answers = correct_answers
    session.score = round(100 * correct_answers / len(attempts), 2) if attempts else 0
    db.commit()
    duration_seconds = max(
        0,
        int((completed_at - session.started_at.replace(tzinfo=None)).total_seconds()),
    )
    logger.info(
        "Completed practice session id=%d score=%.2f accuracy=%.2f topics=%d",
        session.id,
        session.score,
        session.score,
        len(topic_coverage),
    )
    return {
        "session_id": session.id,
        "score": session.score,
        "total_questions": session.total_questions,
        "correct_answers": session.correct_answers,
        "accuracy": session.score,
        "duration_seconds": duration_seconds,
        "topic_coverage": sorted(topic_coverage),
        "results": results,
    }


def _topic_performances(db: Session, student_id: int, subject_id: int):
    return (
        db.query(StudentTopicPerformance)
        .filter(
            StudentTopicPerformance.student_id == student_id,
            StudentTopicPerformance.subject_id == subject_id,
        )
        .order_by(StudentTopicPerformance.mastery_score.desc(), StudentTopicPerformance.topic.asc())
        .all()
    )


def get_weak_topics(db: Session, student_id: int, subject_id: int):
    _validate_student_subject(db, student_id, subject_id)
    performances = _topic_performances(db, student_id, subject_id)
    frequencies = get_topic_frequency(db, subject_id)
    result = [
        {
            "topic": item.topic,
            "mastery": round(item.mastery_score),
            "attempts": item.attempts,
            "pyq_frequency": frequencies.get(item.topic, 0),
        }
        for item in sorted(
            (entry for entry in performances if entry.mastery_score < 50),
            key=lambda entry: (entry.mastery_score, entry.topic),
        )
    ]
    from app.services.memory_service import sync_topic_memories

    sync_topic_memories(student_id, subject_id, result, [], db=db)
    return result


def get_strong_topics(db: Session, student_id: int, subject_id: int):
    _validate_student_subject(db, student_id, subject_id)
    performances = _topic_performances(db, student_id, subject_id)
    result = [
        {
            "topic": item.topic,
            "mastery": round(item.mastery_score),
            "attempts": item.attempts,
            "confidence_score": round(item.confidence_score),
        }
        for item in sorted(
            (entry for entry in performances if entry.mastery_score >= 80),
            key=lambda entry: (-entry.mastery_score, entry.topic),
        )
    ]
    from app.services.memory_service import sync_topic_memories

    sync_topic_memories(student_id, subject_id, [], result, db=db)
    return result


def _latest_plan_completion(db: Session, student_id: int, subject_id: int):
    plan = (
        db.query(StudyPlan)
        .filter(
            StudyPlan.student_id == student_id,
            StudyPlan.subject_id == subject_id,
        )
        .order_by(StudyPlan.created_at.desc(), StudyPlan.id.desc())
        .first()
    )
    if plan is None:
        return 0
    tasks = list(plan.tasks)
    if not tasks:
        return 0
    return round(
        100
        * sum(task.status == StudyTaskStatus.COMPLETED.value for task in tasks)
        / len(tasks)
    )


def _readiness_status(score: int):
    if score < 40:
        return "At Risk"
    if score < 60:
        return "Needs Work"
    if score < 80:
        return "Good"
    return "Ready"


def calculate_exam_readiness(db: Session, student_id: int, subject_id: int):
    _validate_student_subject(db, student_id, subject_id)
    performances = _topic_performances(db, student_id, subject_id)
    topic_mastery = [
        {
            "topic": item.topic,
            "attempts": item.attempts,
            "correct_answers": item.correct_answers,
            "incorrect_answers": item.incorrect_answers,
            "confidence_score": round(item.confidence_score, 2),
            "mastery_score": round(item.mastery_score, 2),
            "last_practiced_at": item.last_practiced_at,
        }
        for item in performances
    ]
    mastery_component = (
        sum(item.mastery_score for item in performances) / len(performances)
        if performances
        else 0.0
    )
    plan_completion = _latest_plan_completion(db, student_id, subject_id)
    pyq_topics = {
        topic
        for (topic,) in db.query(ExamQuestion.topic)
        .filter(
            ExamQuestion.subject_id == subject_id,
            ExamQuestion.topic.isnot(None),
        )
        .distinct()
        .all()
    }
    practiced_topics = {item.topic for item in performances if item.attempts > 0}
    pyq_coverage = (
        round(100 * len(pyq_topics & practiced_topics) / len(pyq_topics))
        if pyq_topics
        else 0
    )
    readiness = round(
        0.50 * mastery_component
        + 0.25 * plan_completion
        + 0.25 * pyq_coverage
    )
    result = {
        "student_id": student_id,
        "subject_id": subject_id,
        "readiness_score": readiness,
        "status": _readiness_status(readiness),
        "topic_mastery": topic_mastery,
        "plan_completion": plan_completion,
        "pyq_coverage": pyq_coverage,
    }
    logger.info(
        "Calculated exam readiness: student_id=%d subject_id=%d score=%d mastery=%.1f plan=%d pyq=%d",
        student_id,
        subject_id,
        readiness,
        mastery_component,
        plan_completion,
        pyq_coverage,
    )
    from app.services.memory_service import record_readiness_snapshot

    record_readiness_snapshot(
        student_id,
        subject_id,
        readiness,
        db=db,
    )
    return result


def generate_personalized_recommendations(
    db: Session,
    student_id: int,
    subject_id: int,
    today=None,
):
    from app.services.pyq_service import get_topic_frequency

    _validate_student_subject(db, student_id, subject_id)
    weak_topics = get_weak_topics(db, student_id, subject_id)
    topic_frequency = get_topic_frequency(db, subject_id)
    current_date = today or datetime.now(timezone.utc).date()
    upcoming_plan = (
        db.query(StudyPlan)
        .filter(
            StudyPlan.student_id == student_id,
            StudyPlan.subject_id == subject_id,
            StudyPlan.exam_date >= current_date,
        )
        .order_by(StudyPlan.exam_date.asc())
        .first()
    )
    recommendations = []
    next_exam_date = upcoming_plan.exam_date if upcoming_plan else None

    for topic in weak_topics[:3]:
        frequency = topic_frequency.get(topic["topic"], 0)
        if next_exam_date:
            recommendation = (
                f"Revise {topic['topic']} before your {next_exam_date.isoformat()} exam."
            )
        else:
            recommendation = f"Schedule a focused review of {topic['topic']}."
        if frequency:
            recommendation += f" It appears in {frequency} recorded PYQ(s)."
        recommendations.append(recommendation)

    mastered_topics = {item.topic for item in _topic_performances(db, student_id, subject_id)}
    unpracticed_high_frequency = [
        (topic, count)
        for topic, count in sorted(
            topic_frequency.items(),
            key=lambda item: (-item[1], item[0]),
        )
        if topic not in mastered_topics
    ]
    if unpracticed_high_frequency:
        topic, count = unpracticed_high_frequency[0]
        recommendations.append(
            f"Practice {topic}; it appears in {count} recorded PYQ(s) and has no mastery history."
        )

    if upcoming_plan:
        incomplete_count = (
            db.query(func.count(StudyTask.id))
            .filter(
                StudyTask.study_plan_id == upcoming_plan.id,
                StudyTask.status != StudyTaskStatus.COMPLETED.value,
            )
            .scalar()
        ) or 0
        if incomplete_count:
            recommendations.append(
                f"Complete or recalculate your study plan: {incomplete_count} task(s) remain."
            )

    if not recommendations:
        recommendations.append("Keep your practice streak active and review recent mistakes weekly.")

    result = recommendations[:5]
    logger.info(
        "Generated personalized recommendations: student_id=%d subject_id=%d count=%d",
        student_id,
        subject_id,
        len(result),
    )
    return result


def get_practice_session(db: Session, session_id: int):
    session = db.query(PracticeSession).filter(PracticeSession.id == session_id).first()
    if session is None:
        return None
    return session
