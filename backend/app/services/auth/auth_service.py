from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import AuthRefreshToken, Student
from app.services.audit_log_service import AuditLogService
from app.services.auth.google_auth import GoogleAuthService
from app.services.auth.jwt_service import JWTService, JWTTokenError
from app.db.models import (
    AuthRefreshToken,
    Student,
    StudentAcademicProfile,
)

class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.google_auth = GoogleAuthService()
        self.jwt = JWTService()

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def student_data(student: Student) -> dict:
        return {
            "id": student.id,
            "email": student.email,
            "full_name": student.full_name or student.name,
            "profile_picture": student.profile_picture,
            "is_verified": student.is_verified,
        }
        
    def _ensure_academic_profile(self, student_id: int) -> None:
        """
        Create a blank academic profile if one does not already exist.
        """

        profile = (
            self.db.query(StudentAcademicProfile)
            .filter_by(student_id=student_id)
            .first()
        )

        if profile is None:
            self.db.add(
                StudentAcademicProfile(
                    student_id=student_id,
                    academic_status="ACTIVE",
                    total_credits=0,
                    earned_credits=0,
                )
            )        

    def _issue_tokens(self, student: Student) -> dict:
        access_token = self.jwt.create_access_token(student.id)
        refresh_token = self.jwt.create_refresh_token(student.id)
        refresh_claims = self.jwt.verify_token(refresh_token, "refresh")
        self.db.add(
            AuthRefreshToken(
                jti=refresh_claims["jti"],
                student_id=student.id,
                expires_at=datetime.fromtimestamp(refresh_claims["exp"], timezone.utc).replace(tzinfo=None),
            )
        )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 60 * settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        }

    def _response(self, student: Student, audit_action: str) -> dict:
        tokens = self._issue_tokens(student)
        AuditLogService.record_event(
            self.db,
            "AUTHENTICATION",
            "student",
            audit_action,
            student_id=student.id,
            metadata_json={"provider": "google"} if audit_action == "google_login" else {},
        )
        self.db.commit()
        return {"student": self.student_data(student), "tokens": tokens}

    def login_with_google(self, google_id_token: str) -> dict:
        claims = self.google_auth.verify_google_token(
            google_id_token
        )

        profile = self.google_auth.extract_profile(
            claims
        )

        google_student = (
            self.db.query(Student)
            .filter_by(
                google_id=profile["google_id"]
            )
            .first()
        )

        email_student = (
            self.db.query(Student)
            .filter(
                func.lower(Student.email)
                == profile["email"]
            )
            .first()
        )

        if (
            google_student is not None
            and email_student is not None
            and google_student.id != email_student.id
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Google identity and email belong "
                    "to different accounts"
                ),
            )

        if (
            email_student is not None
            and email_student.google_id
            not in (
                None,
                profile["google_id"],
            )
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Google identity is already linked "
                    "to another account"
                ),
            )

        student = google_student or email_student

        is_new_student = False

        if student is None:
            student = Student(
                name=profile["full_name"],
                email=profile["email"],
                google_id=profile["google_id"],
                full_name=profile["full_name"],
                profile_picture=profile["profile_picture"],
                is_verified=True,
                is_active=True,
            )

            self.db.add(student)

            is_new_student = True

        else:
            student.google_id = profile["google_id"]
            student.full_name = profile["full_name"]
            student.name = profile["full_name"]
            student.profile_picture = profile["profile_picture"]
            student.is_verified = True

        if not student.is_active:
            raise HTTPException(
                status_code=403,
                detail="Student account is inactive",
            )

        student.last_login_at = self._now()

        self.db.flush()

        # Create academic profile automatically
        self._ensure_academic_profile(student.id)

        self.db.flush()

        return self._response(
            student,
            "google_login",
        )

    def refresh_access_token(self, refresh_token: str) -> dict:
        try:
            claims = self.jwt.verify_token(refresh_token, "refresh")
        except JWTTokenError as error:
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token") from error
        token_record = self.db.get(AuthRefreshToken, claims["jti"])
        student = self.db.get(Student, claims["student_id"])
        if (
            token_record is None
            or token_record.revoked_at is not None
            or token_record.expires_at <= self._now()
            or student is None
            or not student.is_active
        ):
            raise HTTPException(status_code=401, detail="Refresh token is no longer valid")
        now = self._now()
        revoked = self.db.execute(
            update(AuthRefreshToken)
            .where(
                AuthRefreshToken.jti == claims["jti"],
                AuthRefreshToken.student_id == claims["student_id"],
                AuthRefreshToken.revoked_at.is_(None),
                AuthRefreshToken.expires_at > now,
            )
            .values(revoked_at=now)
        )
        if revoked.rowcount != 1:
            raise HTTPException(status_code=401, detail="Refresh token is no longer valid")
        return self._response(student, "refresh")

    def get_current_student(self, access_token: str) -> Student:
        try:
            claims = self.jwt.verify_token(access_token, "access")
        except JWTTokenError as error:
            raise HTTPException(status_code=401, detail="Invalid or expired access token") from error
        student = self.db.get(Student, claims["student_id"])
        if student is None or not student.is_active:
            raise HTTPException(status_code=401, detail="Student account is unavailable")
        return student

    def revoke_refresh_token(self, refresh_token: str, expected_student_id: int) -> None:
        try:
            claims = self.jwt.verify_token(refresh_token, "refresh")
        except JWTTokenError as error:
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token") from error
        token_record = self.db.get(AuthRefreshToken, claims["jti"])
        if claims["student_id"] != expected_student_id:
            raise HTTPException(status_code=403, detail="Refresh token belongs to another student")
        if token_record is not None and token_record.student_id == claims["student_id"]:
            token_record.revoked_at = token_record.revoked_at or self._now()
            AuditLogService.record_event(
                self.db,
                "AUTHENTICATION",
                "student",
                "logout",
                student_id=expected_student_id,
            )
            self.db.commit()