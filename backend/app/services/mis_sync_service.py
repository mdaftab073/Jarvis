from datetime import timedelta

from sqlalchemy.orm import Session

from app.db.models import MISAccount, MISLoginSession, Student
from app.models.student_profile import MISStudentProfile
from app.services.connector_crypto_service import decrypt_credentials, encrypt_credentials
from app.services.mis import MISClient, MISClientError, MISParser
from app.services.time_service import utc_now_naive


class MISSyncError(Exception):
    pass


def _client_for(db: Session, student_id: int) -> tuple[MISClient, dict[str, str], bool]:
    account = db.query(MISAccount).filter_by(student_id=student_id, enabled=True).first()
    if account is None:
        raise MISSyncError("An enabled SVNIT MIS account is not configured for this student")
    client = None
    try:
        session_state = db.query(MISLoginSession).filter_by(
            student_id=student_id
        ).with_for_update().first()
        if session_state is not None:
            if session_state.expires_at <= utc_now_naive():
                db.delete(session_state)
                db.commit()
                raise MISClientError("SESSION_EXPIRED", "MIS session has expired")
            client = MISClient(account.endpoint_url, account.configuration or {})
            client.restore_session_state(decrypt_credentials(session_state.encrypted_state))
            if not client.is_logged_in():
                client.close()
                db.delete(session_state)
                db.commit()
                raise MISClientError("SESSION_EXPIRED", "MIS session has expired")
            return client, {}, True
        credentials = decrypt_credentials(account.encrypted_credentials)
        client = MISClient(account.endpoint_url, account.configuration or {})
    except MISClientError:
        if client is not None:
            client.close()
        raise
    except (ValueError, TypeError) as error:
        if client is not None:
            client.close()
        raise MISSyncError("Unable to initialize the SVNIT MIS account") from error
    return client, credentials, False


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
    client, credentials, reusable_session = _client_for(db, student_id)
    parser = MISParser()
    try:
        if not reusable_session:
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
        synced_at = utc_now_naive()
        source_page = client.last_source_page
        if not isinstance(source_page, str):
            source_page = None
        if resource == "profile":
            for field in ("roll_no", "name", "department", "program", "semester", "email", "phone", "raw_json"):
                value = getattr(data, field)
                if value is not None:
                    setattr(profile, field, value)
            profile.raw_json = data.model_dump(mode="json")
            profile.synced_at = synced_at
            profile.source_page = source_page
            count = sum(getattr(data, field) is not None for field in ("roll_no", "name", "department", "program", "semester", "email", "phone"))
        elif resource == "attendance":
            rows = [record.model_dump(mode="json") for record in data.records]
            profile.attendance_json = rows
            profile.attendance_raw_json = rows
            profile.attendance_synced_at = synced_at
            profile.attendance_source_page = source_page
            count = len(data.records)
        elif resource == "results":
            rows = [record.model_dump(mode="json") for record in data.records]
            profile.results_json = rows
            profile.results_raw_json = rows
            profile.results_synced_at = synced_at
            profile.results_source_page = source_page
            count = len(data.records)
        else:
            rows = [entry.model_dump(mode="json") for entry in data.entries]
            profile.timetable_json = rows
            profile.timetable_raw_json = rows
            profile.timetable_synced_at = synced_at
            profile.timetable_source_page = source_page
            count = len(data.entries)
        profile.updated_at = utc_now_naive()
        if reusable_session:
            session_state = db.query(MISLoginSession).filter_by(
                student_id=student_id
            ).with_for_update().first()
            ttl = int(client.configuration.get("authenticated_session_ttl_seconds", 7200))
            encrypted_state = encrypt_credentials(client.export_session_state())
            if session_state is None:
                session_state = MISLoginSession(
                    student_id=student_id,
                    encrypted_state=encrypted_state,
                    expires_at=synced_at + timedelta(seconds=ttl),
                )
                db.add(session_state)
            else:
                session_state.encrypted_state = encrypted_state
                session_state.expires_at = synced_at + timedelta(seconds=ttl)
        db.commit()
        db.refresh(profile)
        return profile, count
    except Exception as error:
        db.rollback()
        if isinstance(error, MISClientError) and error.code == "SESSION_EXPIRED":
            session_state = db.query(MISLoginSession).filter_by(student_id=student_id).first()
            if session_state is not None:
                db.delete(session_state)
                db.commit()
        raise
    finally:
        if reusable_session:
            client.close()
        else:
            try:
                client.logout()
            except Exception:
                client.close()


def sync_profile(db: Session, student_id: int):
    return _run_sync(db, student_id, "profile")


def sync_attendance(db: Session, student_id: int):
    return _run_sync(db, student_id, "attendance")


def sync_results(db: Session, student_id: int):
    return _run_sync(db, student_id, "results")


def sync_timetable(db: Session, student_id: int):
    return _run_sync(db, student_id, "timetable")


def full_sync(db: Session, student_id: int) -> dict[str, tuple[MISStudentProfile, int]]:
    return {
        resource: _run_sync(db, student_id, resource)
        for resource in ("profile", "attendance", "results", "timetable")
    }


def get_profile(db: Session, student_id: int):
    return _owned_profile(db, student_id)


def get_snapshot(db: Session, student_id: int, field: str):
    if field not in {"attendance_json", "results_json", "timetable_json"}:
        raise ValueError("Unsupported MIS snapshot")
    profile = _owned_profile(db, student_id)
    return profile