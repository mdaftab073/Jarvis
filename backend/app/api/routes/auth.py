from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.auth.auth_service import AuthService
from app.services.auth.google_auth import GoogleTokenError
from app.api.rate_limit import limiter
from app.core.config import settings


router = APIRouter()


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(min_length=1)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


@router.post("/auth/google")
@limiter.limit(settings.AUTH_RATE_LIMIT)
def login_with_google(
    request: Request,
    payload: GoogleLoginRequest,
    db: Session = Depends(get_db),
):
    try:
        return AuthService(db).login_with_google(payload.id_token)
    except GoogleTokenError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail="Authentication is not configured") from error


@router.post("/auth/refresh")
@limiter.limit(settings.REFRESH_RATE_LIMIT)
def refresh_access_token(
    request: Request,
    payload: RefreshRequest,
    db: Session = Depends(get_db),
):
    try:
        return AuthService(db).refresh_access_token(payload.refresh_token)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail="Authentication is not configured") from error


@router.get("/auth/me")
@limiter.limit(settings.AUTH_RATE_LIMIT)
def get_me(request: Request):
    student = getattr(request.state, "student", None)
    claims = getattr(request.state, "auth_claims", None)
    if student is None or claims is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    expires_at = datetime.fromtimestamp(claims["exp"], timezone.utc).isoformat()
    return {
        "student": AuthService.student_data(student),
        "tokens": {"token_type": "bearer", "expires_at": expires_at},
    }


@router.post("/auth/logout")
@limiter.limit(settings.AUTH_RATE_LIMIT)
def logout(
    payload: RefreshRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    student_id = getattr(request.state, "student_id", None)
    if student_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        AuthService(db).revoke_refresh_token(payload.refresh_token, expected_student_id=student_id)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail="Authentication is not configured") from error
    return {
        "student": AuthService.student_data(request.state.student),
        "tokens": {"token_type": "bearer", "revoked": True},
    }