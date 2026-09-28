import logging
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session, joinedload

from app.db.models import (
    Course,
    Semester,
    SemesterMilestone,
    SemesterSubject,
    StudyPlan,
    StudyTask,
    Subject,
    Student,
)
from app.core.study_plan_types import StudyTaskStatus
from app.services.performance_service import (
    calculate_exam_readiness,
    get_weak_topics,
)
from app.services.study_plan_service import calculate_plan_progress

logger = logging.getLogger(__name__)

SEMESTER_STATUSES = {"ACTIVE", "COMPLETED", "ARCHIVED"}


def _require_student(db: Session, student_id: int):
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is None:
        raise ValueError("Student not found")
    return student


def _get_semester(db: Session, semester_id: int) -> Semester:
    semester = (
        db.query(Semester)
        .options(
            joinedload(Semester.subjects).joinedload(SemesterSubject.subject),
            joinedload(Semester.milestones),
        )
        .filter(Semester.id == semester_id)
        .first()
    )
    if semester is None:
        raise ValueError("Semester not found")
    return semester


def _serialize_semester(semester: Semester) -> dict:
    return {
        "id": semester.id,
        "student_id": semester.student_id,
        "semester_number": semester.semester_number,
        "start_date": semester.start_date,
        "end_date": semester.end_date,
        "target_cgpa": semester.target_cgpa,
        "status": semester.status,
        "created_at": semester.created_at,
        "subjects": [
            {
                "id": item.id,
                "subject_id": item.subject_id,
                "subject_name": item.subject.name,
                "target_score": item.target_score,
                "current_readiness": item.current_readiness,
            }
            for item in semester.subjects
        ],
        "milestones": [_serialize_milestone(item) for item in semester.milestones],
    }


def _serialize_milestone(milestone: SemesterMilestone) -> dict:
    return {
        "id": milestone.id,
        "semester_id": milestone.semester_id,
        "title": milestone.title,
        "description": milestone.description,
        "due_date": milestone.due_date,
        "completed": milestone.completed,
        "completed_at": milestone.completed_at,
        "created_at": milestone.created_at,
    }


def create_semester(
    db: Session,
    student_id: int,
    semester_number: int,
    start_date: date,
    end_date: date,
    target_cgpa: float | None = None,
    subjects: list[dict] | None = None,
):
    _require_student(db, student_id)
    if semester_number <= 0:
        raise ValueError("semester_number must be positive")
    if end_date < start_date:
        raise ValueError("end_date must not be before start_date")
    if target_cgpa is not None and target_cgpa <= 0:
        raise ValueError("target_cgpa must be positive")
    subject_ids = [item["subject_id"] for item in subjects or []]
    if len(subject_ids) != len(set(subject_ids)):
        raise ValueError("A subject can only be enrolled once per semester")

    semester = Semester(
        student_id=student_id,
        semester_number=semester_number,
        start_date=start_date,
        end_date=end_date,
        target_cgpa=target_cgpa,
        status="ACTIVE",
    )
    db.add(semester)
    db.flush()
    for item in subjects or []:
        subject = (
            db.query(Subject)
            .join(Course, Subject.course_id == Course.id)
            .filter(
                Subject.id == item["subject_id"],
                Course.student_id == student_id,
            )
            .first()
        )
        if subject is None:
            db.rollback()
            raise ValueError(f"Subject {item['subject_id']} not found for this student")
        target_score = item.get("target_score")
        if target_score is not None and not 0 <= target_score <= 100:
            db.rollback()
            raise ValueError("target_score must be between 0 and 100")
        semester.subjects.append(
            SemesterSubject(
                subject_id=subject.id,
                target_score=target_score,
                current_readiness=0,
            )
        )
    db.commit()
    semester = _get_semester(db, semester.id)
    logger.info(
        "Semester created: student_id=%d semester_id=%d number=%d subjects=%d",
        student_id,
        semester.id,
        semester_number,
        len(semester.subjects),
    )
    return _serialize_semester(semester)


def get_semester(db: Session, semester_id: int) -> dict:
    return _serialize_semester(_get_semester(db, semester_id))


def add_semester_milestone(
    db: Session,
    semester_id: int,
    title: str,
    due_date: date,
    description: str | None = None,
    completed: bool = False,
):
    semester = _get_semester(db, semester_id)
    if not title.strip():
        raise ValueError("Milestone title cannot be empty")
    if not semester.start_date <= due_date <= semester.end_date:
        raise ValueError("Milestone due_date must fall within the semester")
    milestone = SemesterMilestone(
        semester_id=semester_id,
        title=title.strip(),
        description=description,
        due_date=due_date,
        completed=completed,
        completed_at=datetime.utcnow() if completed else None,
    )
    db.add(milestone)
    db.commit()
    db.refresh(milestone)
    return _serialize_milestone(milestone)


def update_semester_status(db: Session, semester_id: int, status: str) -> dict:
    normalized_status = status.upper()
    if normalized_status not in SEMESTER_STATUSES:
        raise ValueError(f"Unsupported semester status: {status}")
    semester = _get_semester(db, semester_id)
    semester.status = normalized_status
    db.commit()
    return _serialize_semester(_get_semester(db, semester_id))


def create_semester_goal(
    db: Session,
    semester_id: int,
    title: str,
    due_date: date | None = None,
    description: str | None = None,
):
    semester = _get_semester(db, semester_id)
    return add_semester_milestone(
        db,
        semester_id,
        title,
        due_date or semester.end_date,
        description=description or "Semester goal",
    )


def update_milestone_completion(
    db: Session,
    semester_id: int,
    milestone_id: int,
    completed: bool,
):
    milestone = (
        db.query(SemesterMilestone)
        .filter(
            SemesterMilestone.id == milestone_id,
            SemesterMilestone.semester_id == semester_id,
        )
        .first()
    )
    if milestone is None:
        return None
    milestone.completed = completed
    milestone.completed_at = datetime.utcnow() if completed else None
    db.commit()
    db.refresh(milestone)
    return _serialize_milestone(milestone)


def _latest_study_plan(db: Session, student_id: int, subject_id: int):
    return (
        db.query(StudyPlan)
        .options(joinedload(StudyPlan.tasks))
        .filter(
            StudyPlan.student_id == student_id,
            StudyPlan.subject_id == subject_id,
        )
        .order_by(StudyPlan.created_at.desc(), StudyPlan.id.desc())
        .first()
    )


def _refresh_subject_metrics(db: Session, semester: Semester):
    metrics = []
    for enrollment in semester.subjects:
        readiness = calculate_exam_readiness(
            db,
            semester.student_id,
            enrollment.subject_id,
        )
        weak_topics = get_weak_topics(
            db,
            semester.student_id,
            enrollment.subject_id,
        )
        enrollment.current_readiness = readiness["readiness_score"]
        study_plan = _latest_study_plan(
            db,
            semester.student_id,
            enrollment.subject_id,
        )
        plan_completion = (
            calculate_plan_progress(study_plan)["completion"]
            if study_plan is not None
            else 0
        )
        metrics.append(
            {
                "subject_id": enrollment.subject_id,
                "subject_name": enrollment.subject.name,
                "readiness": readiness["readiness_score"],
                "plan_completion": plan_completion,
                "weak_topic_count": len(weak_topics),
            }
        )
    db.commit()
    return metrics


def calculate_semester_progress(db: Session, semester_id: int) -> dict:
    semester = _get_semester(db, semester_id)
    milestones = list(semester.milestones)
    milestone_completion = (
        round(100 * sum(item.completed for item in milestones) / len(milestones))
        if milestones
        else 0
    )
    plans = [
        _latest_study_plan(db, semester.student_id, item.subject_id)
        for item in semester.subjects
    ]
    plans = [plan for plan in plans if plan is not None]
    plan_completion = (
        round(
            sum(calculate_plan_progress(plan)["completion"] for plan in plans)
            / len(plans)
        )
        if plans
        else 0
    )
    overall = round((milestone_completion + plan_completion) / 2)
    return {
        "semester_id": semester_id,
        "progress": overall,
        "milestone_completion": milestone_completion,
        "plan_completion": plan_completion,
        "milestones_completed": sum(item.completed for item in milestones),
        "milestones_total": len(milestones),
    }


def calculate_semester_health(
    db: Session,
    semester_id: int,
    today: date | None = None,
) -> dict:
    semester = _get_semester(db, semester_id)
    subject_metrics = _refresh_subject_metrics(db, semester)
    average_readiness = (
        sum(item["readiness"] for item in subject_metrics) / len(subject_metrics)
        if subject_metrics
        else 0
    )
    average_plan_completion = (
        sum(item["plan_completion"] for item in subject_metrics) / len(subject_metrics)
        if subject_metrics
        else 0
    )
    milestones = list(semester.milestones)
    milestone_completion = (
        100 * sum(item.completed for item in milestones) / len(milestones)
        if milestones
        else 100
    )
    weak_topic_count = sum(item["weak_topic_count"] for item in subject_metrics)
    weak_topic_score = max(0, 100 - 10 * weak_topic_count)
    health_score = round(
        0.40 * average_readiness
        + 0.25 * average_plan_completion
        + 0.20 * milestone_completion
        + 0.15 * weak_topic_score
    )
    category = (
        "Critical" if health_score < 40 else
        "At Risk" if health_score < 60 else
        "Stable" if health_score < 80 else
        "Excellent"
    )
    return {
        "semester_id": semester_id,
        "health_score": health_score,
        "category": category,
        "factors": {
            "average_readiness": round(average_readiness),
            "plan_completion": round(average_plan_completion),
            "milestone_completion": round(milestone_completion),
            "weak_topic_count": weak_topic_count,
            "weak_topic_score": weak_topic_score,
        },
        "subjects": subject_metrics,
        "calculated_at": datetime.combine(today or date.today(), datetime.min.time()),
    }


def detect_academic_risks(
    db: Session,
    semester_id: int,
    today: date | None = None,
) -> list[dict]:
    current_date = today or date.today()
    semester = _get_semester(db, semester_id)
    subject_metrics = _refresh_subject_metrics(db, semester)
    risks = []
    for item in subject_metrics:
        if item["readiness"] < 40:
            risks.append(
                {
                    "risk": f"{item['subject_name']} readiness is critically low ({item['readiness']}%).",
                    "severity": "HIGH",
                }
            )
        elif item["readiness"] < 60:
            risks.append(
                {
                    "risk": f"{item['subject_name']} readiness needs attention ({item['readiness']}%).",
                    "severity": "MEDIUM",
                }
            )
        if item["weak_topic_count"] >= 3:
            risks.append(
                {
                    "risk": f"{item['subject_name']} has {item['weak_topic_count']} weak topics.",
                    "severity": "HIGH" if item["weak_topic_count"] >= 5 else "MEDIUM",
                }
            )
        study_plan = _latest_study_plan(db, semester.student_id, item["subject_id"])
        if study_plan is not None:
            overdue_tasks = [
                task
                for task in study_plan.tasks
                if task.status != StudyTaskStatus.COMPLETED.value
                and study_plan.created_at.date() + timedelta(days=task.day_number - 1)
                < current_date
            ]
            if overdue_tasks:
                risks.append(
                    {
                        "risk": f"{item['subject_name']} has {len(overdue_tasks)} overdue study-plan task(s).",
                        "severity": "HIGH" if len(overdue_tasks) >= 3 else "MEDIUM",
                    }
                )

    for milestone in semester.milestones:
        if not milestone.completed and milestone.due_date < current_date:
            days_overdue = (current_date - milestone.due_date).days
            risks.append(
                {
                    "risk": f"Milestone '{milestone.title}' is {days_overdue} day(s) overdue.",
                    "severity": "HIGH" if days_overdue >= 7 else "MEDIUM",
                }
            )
    return risks


def generate_weekly_review(
    db: Session,
    semester_id: int,
    today: date | None = None,
) -> dict:
    current_date = today or date.today()
    week_start = current_date - timedelta(days=6)
    semester = _get_semester(db, semester_id)
    completed_goals = [
        {
            "title": item.title,
            "completed_at": item.completed_at,
        }
        for item in semester.milestones
        if item.completed
        and item.completed_at is not None
        and week_start <= item.completed_at.date() <= current_date
    ]
    pending_goals = [
        {
            "title": item.title,
            "due_date": item.due_date,
            "overdue": item.due_date < current_date,
        }
        for item in semester.milestones
        if not item.completed and item.due_date <= current_date + timedelta(days=7)
    ]
    risks = detect_academic_risks(db, semester_id, today=current_date)
    recommended_actions = [item["risk"] for item in risks[:3]]
    recommended_actions.extend(
        f"Complete '{item['title']}' by {item['due_date'].isoformat()}."
        for item in pending_goals[:3]
        if not item["overdue"]
    )
    if not recommended_actions:
        recommended_actions.append("Keep your study plans current and review progress next week.")
    return {
        "summary": (
            f"Completed {len(completed_goals)} milestone(s); "
            f"{len(pending_goals)} milestone(s) are due or overdue."
        ),
        "completed_goals": completed_goals,
        "pending_goals": pending_goals,
        "recommended_actions": recommended_actions,
    }