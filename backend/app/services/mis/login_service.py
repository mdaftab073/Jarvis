from datetime import timedelta

from sqlalchemy.orm import Session

from app.db.models import MISLoginSession
from app.services.connector_crypto_service import decrypt_credentials, encrypt_credentials
from app.services.mis.client import MISClient, MISClientError, MISLoginPageData
from app.services.time_service import utc_now_naive


def _store_state(
    db: Session,
    student_id: int,
    client: MISClient,
    ttl_seconds: int,
    include_login_page: bool,
) -> None:
    state = encrypt_credentials(client.export_session_state(include_login_page))
    row = db.query(MISLoginSession).filter_by(student_id=student_id).with_for_update().first()
    expires_at = utc_now_naive() + timedelta(seconds=ttl_seconds)
    if row is None:
        row = MISLoginSession(
            student_id=student_id,
            encrypted_state=state,
            expires_at=expires_at,
        )
        db.add(row)
    else:
        row.encrypted_state = state
        row.expires_at = expires_at
    db.commit()


def start_login(
    db: Session,
    student_id: int,
    base_url: str,
    configuration: dict,
) -> MISLoginPageData:
    client = MISClient(base_url, configuration)
    try:
        page = client.fetch_login_page()
        _store_state(
            db,
            student_id,
            client,
            int(configuration.get("login_challenge_ttl_seconds", 600)),
            include_login_page=True,
        )
        return page
    except Exception:
        db.rollback()
        client.close()
        raise


def complete_login(
    db: Session,
    student_id: int,
    username: str,
    password: str,
    captcha: str,
    base_url: str,
    configuration: dict,
) -> MISClient:
    row = db.query(MISLoginSession).filter_by(student_id=student_id).with_for_update().first()
    now = utc_now_naive()
    if row is None or row.expires_at <= now:
        if row is not None:
            db.delete(row)
            db.commit()
        raise MISClientError("SESSION_EXPIRED", "Start a new MIS login challenge")

    client = MISClient(base_url, configuration)
    try:
        client.restore_session_state(decrypt_credentials(row.encrypted_state))
        if not client.has_login_challenge:
            raise MISClientError("SESSION_EXPIRED", "Start a new MIS login challenge")
        client.login({"username": username, "password": password, "captcha": captcha})
        row.encrypted_state = encrypt_credentials(client.export_session_state())
        row.expires_at = now + timedelta(
            seconds=int(configuration.get("authenticated_session_ttl_seconds", 7200))
        )
        db.commit()
    except Exception:
        db.rollback()
        stale = db.query(MISLoginSession).filter_by(student_id=student_id).first()
        if stale is not None:
            db.delete(stale)
            db.commit()
        client.close()
        raise
    return client


def cancel_login(db: Session, student_id: int) -> None:
    row = db.query(MISLoginSession).filter_by(student_id=student_id).first()
    if row is not None:
        db.delete(row)
        db.commit()
