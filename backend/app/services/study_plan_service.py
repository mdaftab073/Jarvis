import logging
import math
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session, joinedload

from app.core.study_plan_types import StudyTaskStatus
from app.db.models import (
    Course,
    StudyPlan,
    StudyTask,
    Student,
    Subject,
)
from app.services.pyq_service import (
    create_revision_plan,
    generate_important_topics,
    get_topic_frequency,
)

logger = logging.getLogger(__name__)


def _today_utc():
    return datetime.now(timezone.utc).date()


def rank_topics_for_study(
    db: Session,
    subject_id: int,
    subject_difficulty: int = 3,
):
    frequencies = get_topic_frequency(db, subject_id)
    important_topics = generate_important_topics(db, subject_id)
    revision_plan = create_revision_plan(db, subject_id)
    importance_by_topic = {
        item["topic"]: item["score"] for item in important_topics
    }
    revision_priority = {}
    for bucket, topics in revision_plan.items():
        bucket_score = {
            "high_priority": 100,
            "medium_priority": 60,
            "low_priority": 20,
        }[bucket]
        for item in topics:
            revision_priority[item["topic"]] = bucket_score

    topic_names = set(frequencies) | set(importance_by_topic)
    if not topic_names:
        return [
            {
                "topic": "Core concepts and definitions",
                "priority": 1,
                "score": 50,
                "frequency": 0,
            },
            {
                "topic": "Practice problems and applications",
                "priority": 2,
                "score": 40,
                "frequency": 0,
            },
        ]

    maximum_frequency = max(frequencies.values(), default=1)
    difficulty_factor = 0.9 + (subject_difficulty * 0.05)
    ranked = []
    for topic in topic_names:
        frequency = frequencies.get(topic, 0)
        normalized_frequency = 100 * frequency / maximum_frequency
        importance = importance_by_topic.get(topic, 0)
        revision_score = revision_priority.get(topic, 20)
        score = round(
            difficulty_factor
            * (
                0.50 * importance
                + 0.30 * normalized_frequency
                + 0.20 * revision_score
            )
        )
        ranked.append(
            {
                "topic": topic,
                "score": score,
                "frequency": frequency,
            }
        )

    ranked.sort(key=lambda item: (-item["score"], -item["frequency"], item["topic"]))
    for priority, topic in enumerate(ranked, start=1):
        topic["priority"] = priority
    return ranked


def _allocate_topic_hours(topics: list[dict], total_hours: float):
    total_half_hour_units = int(math.floor(total_hours * 2 + 1e-8))
    if total_half_hour_units <= 0 or not topics:
        return []

    weights = [max(topic["score"], 1) for topic in topics]
    total_weight = sum(weights)
    exact_units = [total_half_hour_units * weight / total_weight for weight in weights]
    allocated_units = [math.floor(value) for value in exact_units]
    remaining_units = total_half_hour_units - sum(allocated_units)
    remainder_order = sorted(
        range(len(topics)),
        key=lambda index: (-(exact_units[index] - allocated_units[index]), index),
    )
    for index in remainder_order[:remaining_units]:
        allocated_units[index] += 1

    return [
        (topic, units / 2)
        for topic, units in zip(topics, allocated_units)
        if units > 0
    ]


def _build_task_schedule(
    topics: list[dict],
    days_until_exam: int,
    hours_per_day: float,
    subject_difficulty: int,
):
    tasks = []
    if days_until_exam >= 4:
        topic_days = days_until_exam - 3
        day_capacities = [hours_per_day] * topic_days
        topic_budget = min(
            topic_days * hours_per_day,
            topic_days * hours_per_day * (0.70 + subject_difficulty * 0.06),
        )
    else:
        topic_days = days_until_exam
        day_capacities = [hours_per_day] * topic_days
        day_capacities[-1] *= 0.5
        topic_budget = min(
            days_until_exam * hours_per_day * 0.5,
            sum(day_capacities),
        )

    daily_load = [0.0] * topic_days
    session_limit = max(0.5, 2.5 - (subject_difficulty * 0.2))
    for topic, allocated_hours in _allocate_topic_hours(topics, topic_budget):
        remaining = allocated_hours
        while remaining > 1e-8:
            eligible_days = [
                index
                for index, capacity in enumerate(day_capacities)
                if capacity - daily_load[index] > 1e-8
            ]
            if not eligible_days:
                break
            day_index = min(eligible_days, key=lambda index: (daily_load[index], index))
            hours = min(
                remaining,
                session_limit,
                day_capacities[day_index] - daily_load[day_index],
            )
            tasks.append(
                {
                    "day_number": day_index + 1,
                    "topic": topic["topic"],
                    "priority": topic["priority"],
                    "estimated_hours": round(hours, 4),
                }
            )
            daily_load[day_index] += hours
            remaining -= hours

    if days_until_exam >= 4:
        revision_start = days_until_exam - 2
        review_topics = ", ".join(
            topic["topic"] for topic in topics[: min(5, len(topics))]
        ) or "Core concepts"
        final_tasks = [
            (revision_start, f"Revision: {review_topics}", 1),
            (revision_start + 1, "Full-length mock test", 2),
            (revision_start + 2, "Weak-topic review and error correction", 1),
        ]
        for day_number, topic, priority in final_tasks:
            tasks.append(
                {
                    "day_number": day_number,
                    "topic": topic,
                    "priority": priority,
                    "estimated_hours": round(hours_per_day, 4),
                }
            )
    else:
        reserve_hours = hours_per_day * 0.5
        revision_items = [
            ("Revision: highest-priority topics", 1),
            ("Short mock test", 2),
            ("Weak-topic review", 1),
        ]
        for topic, priority in revision_items:
            tasks.append(
                {
                    "day_number": days_until_exam,
                    "topic": topic,
                    "priority": priority,
                    "estimated_hours": round(reserve_hours / 3, 4),
                }
            )

    return sorted(tasks, key=lambda task: (task["day_number"], task["priority"], task["topic"]))


def _get_subject_for_student(db: Session, student_id: int, subject_id: int):
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


def generate_study_plan(
    db: Session,
    student_id: int,
    subject_id: int,
    exam_date: date,
    hours_per_day: float,
    subject_difficulty: int = 3,
    today: date | None = None,
):
    current_date = today or _today_utc()
    days_until_exam = (exam_date - current_date).days
    if days_until_exam <= 0:
        raise ValueError("Exam date must be at least one day in the future")
    if hours_per_day <= 0 or hours_per_day > 24:
        raise ValueError("hours_per_day must be greater than 0 and at most 24")
    if not 1 <= subject_difficulty <= 5:
        raise ValueError("subject_difficulty must be between 1 and 5")

    subject = _get_subject_for_student(db, student_id, subject_id)
    plan = StudyPlan(
        student_id=student_id,
        subject_id=subject_id,
        exam_date=exam_date,
        hours_per_day=hours_per_day,
        created_at=datetime.combine(current_date, datetime.min.time()),
    )
    db.add(plan)
    db.flush()

    topics = rank_topics_for_study(
        db,
        subject_id,
        subject_difficulty=subject_difficulty,
    )
    scheduled_tasks = _build_task_schedule(
        topics=topics,
        days_until_exam=days_until_exam,
        hours_per_day=hours_per_day,
        subject_difficulty=subject_difficulty,
    )
    plan.tasks.extend(
        StudyTask(
            day_number=task["day_number"],
            topic=task["topic"],
            priority=task["priority"],
            estimated_hours=task["estimated_hours"],
            status=StudyTaskStatus.PENDING.value,
        )
        for task in scheduled_tasks
    )
    db.commit()
    db.refresh(plan)
    logger.info(
        "Generated study plan id=%d student_id=%d subject_id=%d days=%d tasks=%d",
        plan.id,
        student_id,
        subject_id,
        days_until_exam,
        len(plan.tasks),
    )
    return plan


def calculate_plan_progress(plan: StudyPlan):
    tasks = list(plan.tasks)
    total_tasks = len(tasks)
    tasks_done = sum(
        task.status == StudyTaskStatus.COMPLETED.value
        for task in tasks
    )
    tasks_remaining = total_tasks - tasks_done
    completion = round(100 * tasks_done / total_tasks) if total_tasks else 0
    return {
        "completion": completion,
        "tasks_done": tasks_done,
        "tasks_remaining": tasks_remaining,
    }


def get_study_plan(db: Session, plan_id: int):
    plan = (
        db.query(StudyPlan)
        .options(joinedload(StudyPlan.tasks), joinedload(StudyPlan.subject))
        .filter(StudyPlan.id == plan_id)
        .first()
    )
    if plan is None:
        return None

    start_date = plan.created_at.date()
    tasks_by_day = {}
    for task in sorted(plan.tasks, key=lambda item: (item.day_number, item.priority, item.id)):
        task_date = start_date + timedelta(days=task.day_number - 1)
        task_payload = {
            "id": task.id,
            "day_number": task.day_number,
            "scheduled_date": task_date,
            "topic": task.topic,
            "priority": task.priority,
            "estimated_hours": task.estimated_hours,
            "status": task.status,
        }
        tasks_by_day.setdefault(task.day_number, []).append(task_payload)

    agenda = [
        {
            "day_number": day_number,
            "date": start_date + timedelta(days=day_number - 1),
            "tasks": tasks,
        }
        for day_number, tasks in sorted(tasks_by_day.items())
    ]
    return {
        "id": plan.id,
        "student_id": plan.student_id,
        "subject_id": plan.subject_id,
        "subject_name": plan.subject.name,
        "exam_date": plan.exam_date,
        "start_date": start_date,
        "hours_per_day": plan.hours_per_day,
        "created_at": plan.created_at,
        "progress": calculate_plan_progress(plan),
        "daily_agenda": agenda,
    }


def complete_study_task(db: Session, task_id: int):
    task = (
        db.query(StudyTask)
        .options(joinedload(StudyTask.study_plan).joinedload(StudyPlan.tasks))
        .filter(StudyTask.id == task_id)
        .first()
    )
    if task is None:
        return None

    task.status = StudyTaskStatus.COMPLETED.value
    db.commit()
    plan_id = task.study_plan_id
    today = _today_utc()
    plan = db.query(StudyPlan).filter(StudyPlan.id == plan_id).first()
    if plan is not None and any(
        item.status != StudyTaskStatus.COMPLETED.value
        and plan.created_at.date() + timedelta(days=item.day_number - 1) < today
        for item in plan.tasks
    ) and today < plan.exam_date:
        recalculate_plan(db, plan_id, today=today)

    return get_study_plan(db, plan_id)


def recalculate_plan(
    db: Session,
    plan_id: int,
    today: date | None = None,
):
    plan = (
        db.query(StudyPlan)
        .options(joinedload(StudyPlan.tasks))
        .filter(StudyPlan.id == plan_id)
        .first()
    )
    if plan is None:
        return None

    current_date = today or _today_utc()
    start_date = plan.created_at.date()
    total_days = (plan.exam_date - start_date).days
    first_day = max(1, (current_date - start_date).days + 1)
    available_days = list(range(first_day, total_days + 1))
    incomplete = sorted(
        (
            task for task in plan.tasks
            if task.status != StudyTaskStatus.COMPLETED.value
        ),
        key=lambda task: (task.priority, task.day_number, task.id),
    )
    completed_load = {day: 0.0 for day in available_days}
    for task in plan.tasks:
        if task.status == StudyTaskStatus.COMPLETED.value and task.day_number in completed_load:
            completed_load[task.day_number] += task.estimated_hours
    remaining_capacity = {
        day: max(0.0, plan.hours_per_day - completed_load[day])
        for day in available_days
    }

    total_required = sum(task.estimated_hours for task in incomplete)
    total_capacity = sum(remaining_capacity.values())
    if total_required and total_capacity <= 1e-8:
        raise ValueError("No study time remains before the exam")
    compression_ratio = (
        min(1.0, total_capacity / total_required)
        if total_required
        else 1.0
    )
    if compression_ratio < 1:
        logger.warning(
            "Compressing study plan id=%d to %.1f%% of remaining task hours",
            plan_id,
            compression_ratio * 100,
        )

    placements = []
    for task in incomplete:
        hours_left = task.estimated_hours * compression_ratio
        task_placements = []
        for day in available_days:
            capacity = remaining_capacity[day]
            if capacity <= 1e-8:
                continue
            allocated_hours = min(hours_left, capacity)
            task_placements.append((day, allocated_hours))
            remaining_capacity[day] -= allocated_hours
            hours_left -= allocated_hours
            if hours_left <= 1e-8:
                break
        if hours_left > 1e-8:
            raise ValueError("Not enough remaining study time before the exam")
        placements.append((task, task_placements))

    rescheduled_tasks = 0
    for task, task_placements in placements:
        if not task_placements:
            continue
        first_day, first_hours = task_placements[0]
        if task.day_number != first_day or abs(task.estimated_hours - first_hours) > 1e-8:
            rescheduled_tasks += 1
        task.day_number = first_day
        task.estimated_hours = round(first_hours, 4)
        for day, hours in task_placements[1:]:
            db.add(
                StudyTask(
                    study_plan_id=plan.id,
                    day_number=day,
                    topic=task.topic,
                    priority=task.priority,
                    estimated_hours=round(hours, 4),
                    status=StudyTaskStatus.PENDING.value,
                )
            )
            rescheduled_tasks += 1

    db.commit()
    logger.info(
        "Recalculated study plan id=%d rescheduled_tasks=%d remaining_days=%d",
        plan_id,
        rescheduled_tasks,
        len(available_days),
    )
    return get_study_plan(db, plan_id), rescheduled_tasks
