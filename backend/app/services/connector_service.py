from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models import AttendanceRecord, Course, GradeRecord, Student, StudentAcademicProfile, StudentConnector, Subject, SyncHistory, SyncJob
from app.services.connector_crypto_service import decrypt_credentials, encrypt_credentials
from app.services.grade_service import recalculate_profile_grades
from app.services.mis_connectors import ConnectorConfigurationError, connector_configuration, create_connector_adapter
from app.services.time_service import utc_now_naive


class ConnectorOwnershipError(ValueError):
    pass


def serialize_connector(connector: StudentConnector) -> dict:
    return {
        "id": connector.id,
        "student_id": connector.student_id,
        "connector_type": connector.connector_type,
        "enabled": connector.enabled,
        "sync_interval_minutes": connector.sync_interval_minutes,
        "status": connector.status,
        "last_sync_at": connector.last_sync_at,
        "created_at": connector.created_at,
    }


def serialize_job(job: SyncJob) -> dict:
    return {
        "id": job.id,
        "student_id": job.student_id,
        "connector_id": job.connector_id,
        "status": job.status,
        "scheduled_at": job.scheduled_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "duration_seconds": job.duration_seconds,
        "error": job.error,
    }


def create_connector(db: Session, student_id: int, connector_type: str, credentials: dict, configuration: dict | None = None, sync_interval_minutes: int | None = None) -> StudentConnector:
    if db.query(Student.id).filter_by(id=student_id).first() is None:
        raise ValueError("Student not found")
    if connector_type != "svnit_mis":
        raise ConnectorConfigurationError(f"Unsupported connector type: {connector_type}")
    endpoint_url, default_resources = connector_configuration(connector_type)
    configuration = dict(configuration or {})
    configuration.setdefault("resources", default_resources)
    create_connector_adapter(connector_type, endpoint_url, configuration)
    if sync_interval_minutes is not None and sync_interval_minutes < 5:
        raise ValueError("sync_interval_minutes must be at least 5")
    existing = db.query(StudentConnector).filter_by(student_id=student_id, connector_type=connector_type).first()
    if existing is not None:
        raise ValueError("Connector already exists for this student")
    connector = StudentConnector(
        student_id=student_id,
        connector_type=connector_type,
        endpoint_url=endpoint_url,
        encrypted_credentials=encrypt_credentials(credentials),
        configuration=configuration,
        sync_interval_minutes=sync_interval_minutes,
        status="READY",
    )
    db.add(connector)
    db.commit()
    db.refresh(connector)
    return connector


def list_connectors(db: Session, student_id: int) -> list[dict]:
    connectors = db.query(StudentConnector).filter_by(student_id=student_id).order_by(StudentConnector.id).all()
    return [serialize_connector(connector) for connector in connectors]


def get_connector(db: Session, connector_id: int) -> StudentConnector | None:
    return db.query(StudentConnector).filter_by(id=connector_id).first()


def rotate_credentials(db: Session, connector_id: int, credentials: dict) -> StudentConnector | None:
    connector = get_connector(db, connector_id)
    if connector is None:
        return None
    connector.encrypted_credentials = encrypt_credentials(credentials)
    connector.status = "READY"
    db.commit()
    db.refresh(connector)
    return connector


def enqueue_sync(db: Session, student_id: int, connector_id: int) -> SyncJob:
    connector = get_connector(db, connector_id)
    if connector is None or connector.student_id != student_id:
        raise ConnectorOwnershipError("Connector not found for student")
    if not connector.enabled:
        raise ValueError("Connector is disabled")
    active = db.query(SyncJob.id).filter(
        SyncJob.connector_id == connector_id,
        SyncJob.status.in_(("QUEUED", "RUNNING")),
    ).first()
    if active:
        raise ValueError("A sync is already queued or running")
    job = SyncJob(student_id=student_id, connector_id=connector_id, status="QUEUED", scheduled_at=utc_now_naive())
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _resolve_course(db: Session, student_id: int, configuration: dict) -> Course:
    course_id = configuration.get("course_id")
    if course_id is not None:
        course = db.query(Course).filter_by(id=course_id, student_id=student_id).first()
        if course is None:
            raise ValueError("Configured course does not belong to connector student")
        return course
    course = db.query(Course).filter_by(student_id=student_id).order_by(Course.id).first()
    if course is None:
        course = Course(name=str(configuration.get("default_course_name", "MIS Academics")), student_id=student_id)
        db.add(course)
        db.flush()
    return course


def _persist_normalized_data(db: Session, connector: StudentConnector, data: dict) -> int:
    student_id = connector.student_id
    profile_data = {key: value for key, value in data.get("profile", {}).items() if value is not None}
    profile_data.pop("academic_status", None) if profile_data.get("academic_status") not in {"ACTIVE", "PROBATION", "GRADUATED", "SUSPENDED", "DROPOUT"} else None
    profile = db.query(StudentAcademicProfile).filter_by(student_id=student_id).first()
    if profile is None:
        profile = StudentAcademicProfile(student_id=student_id, **profile_data)
        db.add(profile)
        db.flush()
    else:
        for key, value in profile_data.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
    course = _resolve_course(db, student_id, connector.configuration or {})
    subject_map: dict[str, Subject] = {}
    for item in data.get("subjects", []):
        name = item["name"].strip()
        subject = db.query(Subject).filter_by(course_id=course.id, name=name).first()
        if subject is None:
            subject = Subject(name=name, description=item.get("code"), course_id=course.id)
            db.add(subject)
            db.flush()
        subject_map[str(item["external_id"])] = subject
        subject_map[name] = subject
        if item.get("code"):
            subject_map[str(item["code"])] = subject
    processed = len(profile_data)
    for row in data.get("attendance", []):
        subject = subject_map.get(row["subject_external_id"])
        if subject is None and row.get("subject_name"):
            subject = subject_map.get(row["subject_name"])
        if subject is None:
            continue
        record = db.query(AttendanceRecord).filter_by(student_id=student_id, subject_id=subject.id).first()
        if record is None:
            record = AttendanceRecord(
                student_id=student_id,
                academic_profile_id=profile.id,
                subject_id=subject.id,
            )
            db.add(record)
        attended = row["attended_classes"]
        total = row["total_classes"]
        if attended < 0 or total < 0 or attended > total:
            raise ValueError("MIS attendance values are invalid")
        record.attended_classes = attended
        record.total_classes = total
        record.attendance_percentage = round(100 * attended / total, 2) if total else None
        processed += 1
    for row in data.get("grades", []):
        subject = subject_map.get(row["subject_external_id"])
        if subject is None and row.get("subject_name"):
            subject = subject_map.get(row["subject_name"])
        if subject is None:
            continue
        fields = {key: row.get(key) for key in (
            "semester", "credits", "grade", "grade_points", "obtained_marks", "max_marks"
        )}
        fields["max_marks"] = fields["max_marks"] or 100
        if fields["semester"] is None or fields["credits"] is None or fields["credits"] <= 0:
            raise ValueError("MIS final grade requires semester and positive credits")
        if fields["grade_points"] is None or not 0 <= fields["grade_points"] <= 10:
            raise ValueError("MIS final grade points are invalid")
        grade = db.query(GradeRecord).filter_by(
            student_id=student_id,
            subject_id=subject.id,
            semester=fields["semester"],
            grade_type="FINAL",
        ).first()
        if grade is None:
            grade = GradeRecord(
                student_id=student_id,
                academic_profile_id=profile.id,
                subject_id=subject.id,
                component_type="OTHER",
                grade_type="FINAL",
            )
            db.add(grade)
        for key, value in fields.items():
            setattr(grade, key, value)
        grade.subject_id = subject.id
        processed += 1
    recalculate_profile_grades(db, student_id)
    return processed + len(data.get("subjects", []))


def run_sync_job(job_id: int) -> dict:
    with SessionLocal() as db:
        job = db.query(SyncJob).filter_by(id=job_id).first()
        if job is None:
            raise ValueError("Sync job not found")
        if job.status in {"SUCCEEDED", "FAILED"}:
            return serialize_job(job)
        connector = get_connector(db, job.connector_id)
        if connector is None or connector.student_id != job.student_id:
            raise ConnectorOwnershipError("Sync connector ownership mismatch")
        started = utc_now_naive()
        job.status = "RUNNING"
        job.started_at = started
        connector.status = "SYNCING"
        db.commit()
        processed = 0
        failure = None
        try:
            credentials = decrypt_credentials(connector.encrypted_credentials)
            adapter = create_connector_adapter(connector.connector_type, connector.endpoint_url, connector.configuration or {})
            normalized = adapter.fetch(credentials)
            processed = _persist_normalized_data(db, connector, normalized)
            finished = utc_now_naive()
            job.status = "SUCCEEDED"
            connector.status = "READY"
            connector.last_sync_at = finished
            history_status = "SUCCEEDED"
            summary = {"records_processed": processed, "resources": ["profile", "subjects", "attendance", "grades"]}
        except Exception as error:
            db.rollback()
            job = db.query(SyncJob).filter_by(id=job_id).first()
            connector = db.query(StudentConnector).filter_by(id=job.connector_id).first()
            finished = utc_now_naive()
            failure = type(error).__name__
            job.status = "FAILED"
            job.error = failure
            connector.status = "ERROR"
            history_status = "FAILED"
            summary = {"records_processed": processed}
        job.finished_at = finished
        job.duration_seconds = max(0.0, (finished - started).total_seconds())
        history = SyncHistory(
            student_id=job.student_id,
            connector_id=connector.id,
            status=history_status,
            started_at=started,
            finished_at=finished,
            duration_seconds=job.duration_seconds,
            records_processed=processed,
            summary=summary,
            error=failure,
        )
        db.add(history)
        db.commit()
        db.refresh(job)
        return serialize_job(job)


def queue_due_sync_jobs(db: Session, now: datetime | None = None) -> list[int]:
    now = now or utc_now_naive()
    connectors = db.query(StudentConnector).filter(
        StudentConnector.enabled.is_(True),
        StudentConnector.sync_interval_minutes.is_not(None),
    ).all()
    job_ids = []
    for connector in connectors:
        last_sync = connector.last_sync_at or connector.created_at
        due_at = last_sync + timedelta(minutes=connector.sync_interval_minutes)
        if due_at > now:
            continue
        active = db.query(SyncJob.id).filter(
            SyncJob.connector_id == connector.id,
            SyncJob.status.in_(("QUEUED", "RUNNING")),
        ).first()
        if active:
            continue
        job = SyncJob(student_id=connector.student_id, connector_id=connector.id, status="QUEUED", scheduled_at=now)
        db.add(job)
        db.flush()
        job_ids.append(job.id)
    db.commit()
    return job_ids


def list_sync_history(db: Session, connector_id: int) -> list[SyncHistory]:
    return db.query(SyncHistory).filter_by(connector_id=connector_id).order_by(SyncHistory.started_at.desc()).all()


def list_sync_jobs(db: Session, student_id: int) -> list[SyncJob]:
    return db.query(SyncJob).filter_by(student_id=student_id).order_by(SyncJob.scheduled_at.desc()).all()


def run_scheduled_syncs(now: datetime | None = None) -> list[dict]:
    with SessionLocal() as db:
        job_ids = queue_due_sync_jobs(db, now)
        queued_ids = [job_id for (job_id,) in db.query(SyncJob.id).filter_by(status="QUEUED").order_by(SyncJob.scheduled_at, SyncJob.id).all()]
        job_ids = list(dict.fromkeys([*job_ids, *queued_ids]))
    return [run_sync_job(job_id) for job_id in job_ids]
