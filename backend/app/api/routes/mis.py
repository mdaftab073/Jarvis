from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, Field, SecretStr
from sqlalchemy.orm import Session

from app.api.rate_limit import limiter
from app.api.student_scope import require_student_scope
from app.core.config import settings
from app.db.database import get_db
from app.db.models import MISAccount, MISLoginSession
from app.schemas.jobs import JobExecutionResponse
from app.schemas.mis import (
    AttendanceRecord,
    AttendanceResponse,
    ResultResponse,
    SemesterResult,
    StudentProfileResponse,
    TimetableEntry,
    TimetableResponse,
)
from app.services.connector_crypto_service import ConnectorCredentialError, encrypt_credentials
from app.services.job_service import enqueue_job
from app.services.mis.client import MISClient, MISClientError
from app.services.mis.configuration import get_mis_site_configuration
from app.services.mis.login_service import complete_login, start_login
from app.services.mis.parser import MISParseError
from app.services.mis_sync_service import MISSyncError, get_profile


router = APIRouter()


class MISLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=255)
    password: SecretStr
    captcha: str | None = Field(default=None, max_length=100)


class MISJobRequest(BaseModel):
    student_id: int = Field(gt=0)
    resource: str = Field(pattern="^(profile|attendance|results|timetable)$")


def _translate_error(error: Exception):
    if isinstance(error, MISClientError):
        status_code = error.status_code
        if error.code in {"LOGIN_FAILED", "INVALID_CAPTCHA", "SESSION_EXPIRED"}:
            status_code = 401 if error.code != "INVALID_CAPTCHA" else 422
        detail = {"code": error.code, "message": str(error)}
        if getattr(error, "required", None):
            detail["required"] = error.required
        raise HTTPException(status_code=status_code, detail=detail) from error
    if isinstance(error, MISParseError):
        raise HTTPException(status_code=502, detail={"code": "PARSE_ERROR", "message": str(error)}) from error
    if isinstance(error, MISSyncError):
        status_code = 404 if str(error) == "Student not found" else 409
        raise HTTPException(
            status_code=status_code,
            detail={"code": "MIS_UNAVAILABLE", "message": str(error)},
        ) from error
    if isinstance(error, ConnectorCredentialError):
        raise HTTPException(
            status_code=503,
            detail={"code": "MIS_UNAVAILABLE", "message": str(error)},
        ) from error
    raise error


def _site_configuration(db: Session, student_id: int) -> tuple[str, dict]:
    account = db.query(MISAccount).filter_by(student_id=student_id).first()
    if account is not None:
        if not account.enabled:
            raise HTTPException(
                status_code=409,
                detail={"code": "LOGIN_FAILED", "message": "SVNIT MIS account is disabled"},
            )
        return account.endpoint_url, account.configuration or {}
    return get_mis_site_configuration()


def _persist_credentials(
    db: Session,
    student_id: int,
    client: MISClient,
    username: str,
    password: str,
) -> None:
    try:
        encrypted = encrypt_credentials({"username": username, "password": password})
        account = db.query(MISAccount).filter_by(student_id=student_id).first()
        if account is None:
            account = MISAccount(
                student_id=student_id,
                endpoint_url=client.base_url.rstrip("/"),
                encrypted_credentials=encrypted,
                configuration=client.configuration,
                enabled=True,
                status="READY",
            )
            db.add(account)
        else:
            account.endpoint_url = client.base_url.rstrip("/")
            account.encrypted_credentials = encrypted
            account.configuration = client.configuration
            account.enabled = True
            account.status = "READY"
        db.commit()
    except Exception:
        db.rollback()
        row = db.query(MISLoginSession).filter_by(student_id=student_id).first()
        if row is not None:
            db.delete(row)
            db.commit()
        raise


@router.post("/mis/login/start")
@limiter.limit(settings.MIS_SYNC_RATE_LIMIT)
def post_login_start(
    request: Request,
    student_id: int,
    db: Session = Depends(get_db),
    _scope: int = Depends(require_student_scope),
):
    try:
        base_url, configuration = _site_configuration(db, student_id)
        page = start_login(db, student_id, base_url, configuration)
    except Exception as error:
        _translate_error(error)
    return {
        "captcha_image": page.captcha_image,
        "captcha_image_url": page.captcha_image_url,
        "expires_in_seconds": page.expires_in_seconds,
    }


@router.post("/mis/login/complete")
@limiter.limit(settings.MIS_SYNC_RATE_LIMIT)
def post_login_complete(
    payload: MISLoginRequest,
    request: Request,
    student_id: int,
    db: Session = Depends(get_db),
    _scope: int = Depends(require_student_scope),
):
    if not payload.captcha or not payload.captcha.strip():
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_CAPTCHA", "message": "A manually entered captcha is required"},
        )
    password = payload.password.get_secret_value()
    client: MISClient | None = None
    try:
        base_url, configuration = _site_configuration(db, student_id)
        client = complete_login(
            db,
            student_id,
            payload.username,
            password,
            payload.captcha,
            base_url,
            configuration,
        )
        _persist_credentials(db, student_id, client, payload.username, password)
    except Exception as error:
        _translate_error(error)
    finally:
        if client is not None:
            client.close()
        password = ""
    return {"authenticated": True, "student_id": student_id}


@router.post("/mis/sync-profile", response_model=JobExecutionResponse, status_code=202)
@limiter.limit(settings.MIS_SYNC_RATE_LIMIT)
def post_sync_profile(
    student_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _scope: int = Depends(require_student_scope),
):
    return enqueue_job(db, background_tasks, "sync_mis_resource", {"student_id": student_id, "resource": "profile"}, student_id)


@router.get("/mis/profile", response_model=StudentProfileResponse)
def read_mis_profile(student_id: int, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    profile = get_profile(db, student_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="MIS profile not found")
    return profile


@router.post("/mis/sync-attendance", response_model=JobExecutionResponse, status_code=202)
@limiter.limit(settings.MIS_SYNC_RATE_LIMIT)
def post_sync_attendance(
    student_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _scope: int = Depends(require_student_scope),
):
    return enqueue_job(db, background_tasks, "sync_mis_resource", {"student_id": student_id, "resource": "attendance"}, student_id)


@router.get("/mis/attendance", response_model=AttendanceResponse)
def read_mis_attendance(student_id: int, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    profile = get_profile(db, student_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="MIS attendance not found")
    return AttendanceResponse(
        student_id=student_id,
        records=[AttendanceRecord.model_validate(row) for row in profile.attendance_json],
        updated_at=profile.updated_at,
        synced_at=profile.attendance_synced_at,
        source_page=profile.attendance_source_page,
        raw_json=profile.attendance_raw_json,
    )


@router.post("/mis/sync-results", response_model=JobExecutionResponse, status_code=202)
@limiter.limit(settings.MIS_SYNC_RATE_LIMIT)
def post_sync_results(
    student_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _scope: int = Depends(require_student_scope),
):
    return enqueue_job(db, background_tasks, "sync_mis_resource", {"student_id": student_id, "resource": "results"}, student_id)


@router.get("/mis/results", response_model=ResultResponse)
def read_mis_results(student_id: int, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    profile = get_profile(db, student_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="MIS results not found")
    return ResultResponse(
        student_id=student_id,
        records=[SemesterResult.model_validate(row) for row in profile.results_json],
        updated_at=profile.updated_at,
        synced_at=profile.results_synced_at,
        source_page=profile.results_source_page,
        raw_json=profile.results_raw_json,
    )


@router.get("/mis/timetable", response_model=TimetableResponse)
def read_mis_timetable(student_id: int, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    profile = get_profile(db, student_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="MIS timetable not found")
    return TimetableResponse(
        student_id=student_id,
        entries=[TimetableEntry.model_validate(row) for row in profile.timetable_json],
        updated_at=profile.updated_at,
        synced_at=profile.timetable_synced_at,
        source_page=profile.timetable_source_page,
        raw_json=profile.timetable_raw_json,
    )


@router.post("/mis/sync-timetable", response_model=JobExecutionResponse, status_code=202)
@limiter.limit(settings.MIS_SYNC_RATE_LIMIT)
def post_sync_timetable(
    student_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _scope: int = Depends(require_student_scope),
):
    return enqueue_job(db, background_tasks, "sync_mis_resource", {"student_id": student_id, "resource": "timetable"}, student_id)


@router.post("/mis/jobs", response_model=JobExecutionResponse, status_code=202)
@limiter.limit(settings.MIS_SYNC_RATE_LIMIT)
def enqueue_mis_sync(
    payload: MISJobRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _scope: int = Depends(require_student_scope),
):
    principal_id = getattr(request.state, "student_id", None)
    if principal_id is not None and payload.student_id != principal_id:
        raise HTTPException(status_code=403, detail="Student scope mismatch")
    return enqueue_job(
        db,
        background_tasks,
        "sync_mis_resource",
        {"student_id": payload.student_id, "resource": payload.resource},
        payload.student_id,
    )
