from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from jwt.exceptions import InvalidTokenError

from app.core.config import settings


class JWTTokenError(ValueError):
    """Raised when a Jarvis JWT is missing, invalid, or used for the wrong purpose."""


class JWTService:
    @staticmethod
    def _secret() -> str:
        if not settings.JWT_SECRET_KEY:
            raise RuntimeError("JWT_SECRET_KEY is not configured")
        if len(settings.JWT_SECRET_KEY.encode("utf-8")) < 32:
            raise RuntimeError("JWT_SECRET_KEY must contain at least 32 bytes")
        return settings.JWT_SECRET_KEY

    @staticmethod
    def _algorithm() -> str:
        if settings.JWT_ALGORITHM not in {"HS256", "HS384", "HS512"}:
            raise RuntimeError("JWT_ALGORITHM must be HS256, HS384, or HS512")
        return settings.JWT_ALGORITHM

    def _create_token(self, student_id: int, token_type: str, expires_delta: timedelta) -> str:
        now = datetime.now(timezone.utc)
        claims = {
            "sub": str(student_id),
            "typ": token_type,
            "jti": str(uuid4()),
            "iat": now,
            "exp": now + expires_delta,
        }
        return jwt.encode(claims, self._secret(), algorithm=self._algorithm())

    def create_access_token(self, student_id: int) -> str:
        return self._create_token(
            student_id,
            "access",
            timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

    def create_refresh_token(self, student_id: int) -> str:
        return self._create_token(
            student_id,
            "refresh",
            timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )

    def verify_token(self, token: str, expected_type: str | None = None) -> dict:
        try:
            claims = jwt.decode(
                token,
                self._secret(),
                algorithms=[self._algorithm()],
                options={"require": ["sub", "typ", "jti", "iat", "exp"]},
            )
            if expected_type is not None and claims.get("typ") != expected_type:
                raise JWTTokenError("JWT has the wrong token type")
            claims["student_id"] = int(claims["sub"])
            if claims["student_id"] < 1:
                raise JWTTokenError("JWT has an invalid subject")
            return claims
        except (InvalidTokenError, TypeError, ValueError) as error:
            if isinstance(error, JWTTokenError):
                raise
            raise JWTTokenError("Invalid or expired JWT") from error