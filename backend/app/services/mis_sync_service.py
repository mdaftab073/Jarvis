import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import Student, StudentConnector
from app.models.student_profile import MISStudentProfile
from app.services.connector_crypto_service import decrypt_credentials
from app.services.mis import MISClient, MISParser


logger = logging.getLogger(__name__)


class MISSyncError(Exception):
    pass


def _client_for(db: Session, student_id: int) -> tuple[MISClient, dict[str, str]]:
    connector = db.query(StudentConnector).filter_by(
        student_id=student_id, connector_type="svnit_mis", enabled=True
    ).first()
    if connector is None:
        raise MISSyncError("An enabled SVNIT MIS connector is not configured for this student")
    try:
        credentials = decrypt_credentials(connector.encrypted_credentials)
        client = MISClient(connector.endpoint_url, connector.configuration or {})
    except Exception as error:
        raise MISSyncError("Unable to initialize the SVNIT MIS connector") from error
    return client, credentials


def _owned_profile(db: Session, student_id: int, create: bool = False) -> MISStudentProfile | None:
    if db.query(Student.id).filter_by(id=student_id).first() is None:
        raise MISSyncError("Student not found")
    profile = db.query(MISStudentProfile).filter_by(student_id=student_id).first()
    if profile is None and create:
        profile = MISStudentProfile(student_id=student_id)
        db.add(profile)
        db.flush()
    return profile


def _run_sync(db: Session, student_id: int, resource: str):
    if db.query(Student.id).filter_by(id=student_id).first() is None:
        raise MISSyncError("Student not found")
    client, credentials = _client_for(db, student_id)
    parser = MISParser()
    try:
        client.login(credentials)
        if resource == "profile":
            data = parser.parse_student_profile(client.fetch_student_profile())
        elif resource == "attendance":
            data = parser.parse_attendance(client.fetch_attendance())
        elif resource == "results":
            data = parser.parse_results(client.fetch_results())
        elif resource == "timetable":
            data = parser.parse_timetable(client.fetch_timetable())
        else:
            raise MISSyncError(f"Unsupported MIS resource: {resource}")

        profile = _owned_profile(db, student_id, create=True)
        if resource == "profile":
            for field in ("roll_no", "name", "department", "program", "semester", "email", "phone", "raw_json"):
                value = getattr(data, field)
                if value is not None:
                    setattr(profile, field, value)
            count = sum(getattr(data, field) is not None for field in ("roll_no", "name", "department", "program", "semester", "email", "phone"))
        elif resource == "attendance":
            profile.attendance_json = [record.model_dump(mode="json") for record in data.records]
            count = len(data.records)
        elif resource == "results":
            profile.results_json = [record.model_dump(mode="json") for record in data.records]
            count = len(data.records)
        else:
            profile.timetable_json = [entry.model_dump(mode="json") for entry in data.entries]
            count = len(data.entries)
        profile.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(profile)
        return profile, count
    except Exception:
        db.rollback()
        logger.exception("SVNIT MIS %s sync failed for student %s", resource, student_id)
        raise
    finally:
        try:
            client.logout()
        except Exception:
            logger.warning("Failed to close SVNIT MIS session", exc_info=True)


def sync_profile(db: Session, student_id: int):
    return _run_sync(db, student_id, "profile")


def sync_attendance(db: Session, student_id: int):
    return _run_sync(db, student_id, "attendance")


def sync_results(db: Session, student_id: int):
    return _run_sync(db, student_id, "results")


def sync_timetable(db: Session, student_id: int):
    return _run_sync(db, student_id, "timetable")


def get_profile(db: Session, student_id: int):
    return _owned_profile(db, student_id)


def get_snapshot(db: Session, student_id: int, field: str):
    if field not in {"attendance_json", "results_json", "timetable_json"}:
        raise ValueError("Unsupported MIS snapshot")
    profile = _owned_profile(db, student_id)
    return profile