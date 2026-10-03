from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.api.responses import error_response
from app.db.database import SessionLocal
from app.services.auth.auth_service import AuthService


_PUBLIC_PATHS = {
    "/api/auth/google",
    "/api/auth/refresh",
    "/api/health",
    "/api/health/live",
    "/api/health/ready",
    "/api/health/dependencies",
    "/health",
    "/health/live",
    "/health/ready",
    "/health/dependencies",
}


class StudentIdentityMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        authorization = request.headers.get("Authorization")
        token = None
        if authorization:
            scheme, separator, credentials = authorization.partition(" ")
            if not separator or scheme.lower() != "bearer" or not credentials.strip():
                return error_response(401, "unauthorized", "Invalid authorization header.")
            token = credentials.strip()

        is_public = request.url.path in _PUBLIC_PATHS
        if (
            token is None
            and settings.REQUIRE_AUTHENTICATED_STUDENT
            and not is_public
            and request.url.path.startswith("/api/")
        ):
            return error_response(401, "unauthorized", "Authentication required.")
        if token is not None:
            db = SessionLocal()
            try:
                auth_service = AuthService(db)
                student = auth_service.get_current_student(token)
                claims = auth_service.jwt.verify_token(token, "access")
            except HTTPException as error:
                return error_response(error.status_code, "unauthorized", str(error.detail))
            except RuntimeError:
                return error_response(503, "authentication_unavailable", "Authentication is not configured.")
            finally:
                db.close()
            request.state.student_id = student.id
            request.state.student = student
            request.state.auth_claims = claims
        return await call_next(request)