import json
import logging
from contextlib import contextmanager
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import (
    ReadinessSnapshot,
    Student,
    StudentMemory,
    StudentProfile,
    Subject,
)

logger = logging.getLogger(__name__)

MEMORY_TYPES = {
    "STRENGTH",
    "WEAKNESS",
    "GOAL",
    "HABIT",
    "RECOMMENDATION",
    "READINESS",
}


@contextmanager
def _session_scope(db: Session | None):
    owns_session = db is None
    session = SessionLocal() if owns_session else db
    try:
        yield session
    finally:
        if owns_session:
            session.close()


def _require_student(db: Session, student_id: int):
    if db.query(Student.id).filter(Student.id == student_id).first() is None:
        raise ValueError("Student not found")


def _decode_value(memory_value: str):
    try:
        return json.loads(memory_value)
    except (TypeError, json.JSONDecodeError):
        return memory_value


def _memory_payload(memory: StudentMemory) -> dict:
    return {
        "id": memory.id,
        "student_id": memory.student_id,
        "memory_type": memory.memory_type,
        "memory_key": memory.memory_key,
        "memory_value": _decode_value(memory.memory_value),
        "created_at": memory.created_at,
        "updated_at": memory.updated_at,
    }


def store_memory(
    student_id: int,
    memory_type: str,
    memory_key: str,
    memory_value=None,
    db: Session | None = None,
) -> dict:
    normalized_type = memory_type.upper()
    normalized_key = " ".join(memory_key.split())
    if normalized_type not in MEMORY_TYPES:
        raise ValueError(f"Unsupported memory type: {memory_type}")
    if not normalized_key:
        raise ValueError("memory_key cannot be empty")
    serialized_value = json.dumps(memory_value, default=str)

    with _session_scope(db) as session:
        _require_student(session, student_id)
        memory = (
            session.query(StudentMemory)
            .filter(
                StudentMemory.student_id == student_id,
                StudentMemory.memory_type == normalized_type,
                StudentMemory.memory_key == normalized_key,
            )
            .first()
        )
        created = memory is None
        if created:
            memory = StudentMemory(
                student_id=student_id,
                memory_type=normalized_type,
                memory_key=normalized_key,
                memory_value=serialized_value,
            )
            session.add(memory)
        else:
            if memory.memory_value != serialized_value:
                memory.memory_value = serialized_value
                memory.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(memory)
        logger.info(
            "Student memory %s: student_id=%d type=%s key=%s",
            "created" if created else "updated",
            student_id,
            normalized_type,
            normalized_key,
        )
        return _memory_payload(memory)


def get_memories(
    student_id: int,
    memory_type: str | None = None,
    db: Session | None = None,
) -> list[dict]:
    with _session_scope(db) as session:
        _require_student(session, student_id)
        query = session.query(StudentMemory).filter(StudentMemory.student_id == student_id)
        if memory_type is not None:
            normalized_type = memory_type.upper()
            if normalized_type not in MEMORY_TYPES:
                raise ValueError(f"Unsupported memory type: {memory_type}")
            query = query.filter(StudentMemory.memory_type == normalized_type)
        memories = query.order_by(StudentMemory.created_at.asc(), StudentMemory.id.asc()).all()
        return [_memory_payload(memory) for memory in memories]


def update_memory(
    student_id: int,
    memory_id: int,
    memory_value,
    db: Session | None = None,
) -> dict | None:
    with _session_scope(db) as session:
        _require_student(session, student_id)
        memory = (
            session.query(StudentMemory)
            .filter(
                StudentMemory.id == memory_id,
                StudentMemory.student_id == student_id,
            )
            .first()
        )
        if memory is None:
            return None
        memory.memory_value = json.dumps(memory_value, default=str)
        memory.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(memory)
        logger.info(
            "Student memory updated: student_id=%d memory_id=%d type=%s",
            student_id,
            memory_id,
            memory.memory_type,
        )
        return _memory_payload(memory)


def delete_memory(
    student_id: int,
    memory_id: int,
    db: Session | None = None,
) -> bool:
    with _session_scope(db) as session:
        _require_student(session, student_id)
        memory = (
            session.query(StudentMemory)
            .filter(
                StudentMemory.id == memory_id,
                StudentMemory.student_id == student_id,
            )
            .first()
        )
        if memory is None:
            return False
        session.delete(memory)
        session.commit()
        logger.info(
            "Student memory deleted: student_id=%d memory_id=%d",
            student_id,
            memory_id,
        )
        return True


def update_student_profile(
    student_id: int,
    db: Session | None = None,
    **updates,
) -> dict:
    allowed = {
        "preferred_study_hours",
        "preferred_subjects",
        "current_goal",
    }
    invalid = set(updates) - allowed
    if invalid:
        raise ValueError(f"Unsupported profile fields: {', '.join(sorted(invalid))}")
    with _session_scope(db) as session:
        _require_student(session, student_id)
        profile = (
            session.query(StudentProfile)
            .filter(StudentProfile.student_id == student_id)
            .first()
        )
        if profile is None:
            profile = StudentProfile(student_id=student_id)
            session.add(profile)
        for field, value in updates.items():
            setattr(profile, field, value)
        profile.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(profile)
        return {
            "id": profile.id,
            "student_id": profile.student_id,
            "preferred_study_hours": profile.preferred_study_hours,
            "preferred_subjects": profile.preferred_subjects,
            "current_goal": profile.current_goal,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
        }


def record_readiness_snapshot(
    student_id: int,
    subject_id: int,
    readiness_score: int,
    db: Session | None = None,
) -> dict:
    if not 0 <= readiness_score <= 100:
        raise ValueError("readiness_score must be between 0 and 100")
    with _session_scope(db) as session:
        _require_student(session, student_id)
        if session.query(Subject.id).filter(Subject.id == subject_id).first() is None:
            raise ValueError("Subject not found")
        snapshot = ReadinessSnapshot(
            student_id=student_id,
            subject_id=subject_id,
            readiness_score=readiness_score,
        )
        session.add(snapshot)
        session.flush()
        store_memory(
            student_id,
            "READINESS",
            f"subject:{subject_id}",
            {"subject_id": subject_id, "score": readiness_score},
            db=session,
        )
        session.refresh(snapshot)
        payload = {
            "id": snapshot.id,
            "student_id": snapshot.student_id,
            "subject_id": snapshot.subject_id,
            "readiness_score": snapshot.readiness_score,
            "captured_at": snapshot.captured_at,
        }
        logger.info(
            "Readiness snapshot captured: student_id=%d subject_id=%d score=%d",
            student_id,
            subject_id,
            readiness_score,
        )
        return payload


def get_readiness_trend(
    student_id: int,
    subject_id: int | None = None,
    db: Session | None = None,
) -> dict:
    with _session_scope(db) as session:
        _require_student(session, student_id)
        query = session.query(ReadinessSnapshot).filter(
            ReadinessSnapshot.student_id == student_id
        )
        if subject_id is not None:
            query = query.filter(ReadinessSnapshot.subject_id == subject_id)
        snapshots = query.order_by(
            ReadinessSnapshot.captured_at.asc(), ReadinessSnapshot.id.asc()
        ).all()
        return {"history": [item.readiness_score for item in snapshots]}


def get_readiness_snapshots(student_id: int, db: Session | None = None) -> list[dict]:
    with _session_scope(db) as session:
        _require_student(session, student_id)
        snapshots = (
            session.query(ReadinessSnapshot)
            .filter(ReadinessSnapshot.student_id == student_id)
            .order_by(ReadinessSnapshot.captured_at.asc(), ReadinessSnapshot.id.asc())
            .all()
        )
        return [
            {
                "id": item.id,
                "student_id": item.student_id,
                "subject_id": item.subject_id,
                "readiness_score": item.readiness_score,
                "captured_at": item.captured_at,
            }
            for item in snapshots
        ]


def build_student_profile(student_id: int, db: Session | None = None) -> dict:
    with _session_scope(db) as session:
        _require_student(session, student_id)
        profile = (
            session.query(StudentProfile)
            .filter(StudentProfile.student_id == student_id)
            .first()
        )
        memories = get_memories(student_id, db=session)
        active = [
            item
            for item in memories
            if not isinstance(item["memory_value"], dict)
            or item["memory_value"].get("current", True)
        ]
        strengths = [
            item["memory_key"]
            for item in active
            if item["memory_type"] == "STRENGTH"
        ]
        weaknesses = [
            item["memory_key"]
            for item in active
            if item["memory_type"] == "WEAKNESS"
        ]
        habits = [
            f"{item['memory_key']}: {item['memory_value']}"
            for item in active
            if item["memory_type"] == "HABIT"
        ]
        trend = get_readiness_trend(student_id, db=session)["history"]
        result = {
            "student_id": student_id,
            "preferred_study_hours": profile.preferred_study_hours if profile else None,
            "preferred_subjects": profile.preferred_subjects if profile else [],
            "current_goal": profile.current_goal if profile else None,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "study_habits": habits,
            "readiness_trend": trend,
        }
        logger.info(
            "Student profile generated: student_id=%d strengths=%d weaknesses=%d snapshots=%d",
            student_id,
            len(strengths),
            len(weaknesses),
            len(trend),
        )
        return result


def generate_profile_summary(student_id: int, db: Session | None = None) -> dict:
    profile = build_student_profile(student_id, db=db)
    strengths = profile["strengths"]
    weaknesses = profile["weaknesses"]
    parts = []
    if strengths:
        parts.append(f"Strong in {', '.join(strengths[:3])}")
    if weaknesses:
        parts.append(f"Needs improvement in {', '.join(weaknesses[:3])}")
    if not parts:
        parts.append("Your academic profile is still developing")
    trend = profile["readiness_trend"]
    if len(trend) >= 2:
        change = trend[-1] - trend[0]
        if change > 0:
            parts.append(f"Readiness has improved by {change} points")
        elif change < 0:
            parts.append(f"Readiness has declined by {abs(change)} points")
    return {"summary": ". ".join(parts) + "."}


def sync_topic_memories(
    student_id: int,
    subject_id: int,
    weak_topics: list[dict],
    strong_topics: list[dict],
    db: Session,
) -> None:
    for memory_type, current_topics in (
        ("WEAKNESS", weak_topics),
        ("STRENGTH", strong_topics),
    ):
        current_keys = {item["topic"] for item in current_topics}
        previous = get_memories(student_id, memory_type, db=db)
        for memory in previous:
            value = memory["memory_value"]
            if (
                isinstance(value, dict)
                and value.get("subject_id") == subject_id
                and memory["memory_key"] not in current_keys
                and value.get("current", True)
            ):
                value["current"] = False
                update_memory(student_id, memory["id"], value, db=db)
        for item in current_topics:
            store_memory(
                student_id,
                memory_type,
                item["topic"],
                {"subject_id": subject_id, **item, "current": True},
                db=db,
            )