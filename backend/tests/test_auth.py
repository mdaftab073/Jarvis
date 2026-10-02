import unittest
from unittest.mock import patch

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.api.student_scope import require_student_scope
from app.core.auth_middleware import StudentIdentityMiddleware
from app.core.config import settings
from app.db.database import Base, get_db
from app.db.models import AuthRefreshToken, Course, Student, Subject
from app.models.audit_log import AuditLog
from app.services.auth.auth_service import AuthService
from app.services.auth.google_auth import GoogleAuthService, GoogleTokenError
from app.services.auth.jwt_service import JWTService, JWTTokenError


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.db = self.Session()
        self.student = Student(name="Verified Student", email="verified@example.com")
        self.other = Student(name="Other Student", email="other@example.com")
        self.db.add_all([self.student, self.other])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_google_verification_checks_provider_claims_and_extracts_profile(self):
        claims = {
            "iss": "https://accounts.google.com",
            "aud": "jarvis-client",
            "sub": "google-123",
            "email": "STUDENT@example.com",
            "email_verified": True,
            "name": "Student Name",
            "picture": "https://example.com/picture.png",
        }
        with patch.object(settings, "GOOGLE_CLIENT_ID", "jarvis-client"), patch(
            "app.services.auth.google_auth.id_token.verify_oauth2_token", return_value=claims
        ) as verify:
            verified = GoogleAuthService().verify_google_token("signed-token")
            profile = GoogleAuthService.extract_profile(verified)
        verify.assert_called_once()
        self.assertEqual(profile["google_id"], "google-123")
        self.assertEqual(profile["email"], "student@example.com")
        self.assertTrue(profile["is_verified"])

    def test_google_verification_rejects_unverified_email(self):
        claims = {
            "iss": "accounts.google.com",
            "aud": "jarvis-client",
            "sub": "google-123",
            "email": "student@example.com",
            "email_verified": False,
        }
        with patch.object(settings, "GOOGLE_CLIENT_ID", "jarvis-client"), patch(
            "app.services.auth.google_auth.id_token.verify_oauth2_token", return_value=claims
        ):
            with self.assertRaises(GoogleTokenError):
                GoogleAuthService().verify_google_token("signed-token")

    def test_jwt_creation_validation_expiration_and_invalid_tokens(self):
        with patch.object(settings, "JWT_SECRET_KEY", "test-secret-key-with-at-least-32-bytes"):
            service = JWTService()
            token = service.create_access_token(self.student.id)
            claims = service.verify_token(token, "access")
            self.assertEqual(claims["student_id"], self.student.id)
            with self.assertRaises(JWTTokenError):
                service.verify_token("not-a-token", "access")
            with self.assertRaises(JWTTokenError):
                service.verify_token(token, "refresh")
            with patch.object(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", -1):
                expired = service.create_access_token(self.student.id)
            with self.assertRaises(JWTTokenError):
                service.verify_token(expired, "access")

    def test_google_login_creates_student_and_refresh_rotates_token(self):
        claims = {
            "sub": "google-login-456",
            "email": "newstudent@example.com",
            "email_verified": True,
            "name": "New Student",
            "picture": "https://example.com/new.png",
        }
        with patch.object(settings, "JWT_SECRET_KEY", "test-secret-key-with-at-least-32-bytes"), patch.object(
            GoogleAuthService, "verify_google_token", return_value=claims
        ):
            service = AuthService(self.db)
            login = service.login_with_google("google-id-token")
            student = self.db.query(Student).filter_by(google_id="google-login-456").one()
            self.assertEqual(login["student"]["id"], student.id)
            self.assertEqual(login["student"]["full_name"], "New Student")
            self.assertTrue(login["student"]["is_verified"])
            self.assertEqual(self.db.query(AuthRefreshToken).count(), 1)
            self.assertEqual(
                self.db.query(AuditLog).filter_by(event_type="AUTHENTICATION").count(),
                1,
            )

            rotated = service.refresh_access_token(login["tokens"]["refresh_token"])
            self.assertNotEqual(rotated["tokens"]["refresh_token"], login["tokens"]["refresh_token"])
            with self.assertRaises(HTTPException) as reused_token:
                service.refresh_access_token(login["tokens"]["refresh_token"])
            self.assertEqual(reused_token.exception.status_code, 401)
            principal = service.get_current_student(rotated["tokens"]["access_token"])
            self.assertEqual(principal.id, student.id)

    def test_existing_email_is_linked_only_when_google_identity_does_not_conflict(self):
        self.student.google_id = "different-google-id"
        self.db.commit()
        claims = {
            "sub": "incoming-google-id",
            "email": self.student.email,
            "email_verified": True,
            "name": "Verified Student",
        }
        with patch.object(GoogleAuthService, "verify_google_token", return_value=claims):
            with self.assertRaises(HTTPException) as identity_collision:
                AuthService(self.db).login_with_google("google-id-token")
            self.assertEqual(identity_collision.exception.status_code, 409)
        self.assertEqual(self.student.google_id, "different-google-id")

    def test_google_identity_and_email_cannot_select_different_students(self):
        self.student.google_id = "google-student-owner"
        self.db.commit()
        claims = {
            "sub": "google-student-owner",
            "email": self.other.email,
            "email_verified": True,
            "name": "Ambiguous Identity",
        }
        with patch.object(GoogleAuthService, "verify_google_token", return_value=claims):
            with self.assertRaises(HTTPException) as ambiguous_identity:
                AuthService(self.db).login_with_google("google-id-token")
        self.assertEqual(ambiguous_identity.exception.status_code, 409)
        self.assertEqual(self.student.google_id, "google-student-owner")
        self.assertIsNone(self.other.google_id)

    def test_bearer_middleware_sets_identity_and_enforces_student_scope(self):
        app = FastAPI()
        app.add_middleware(StudentIdentityMiddleware)

        @app.get("/api/protected/{student_id}")
        def protected(
            student_id: int,
            request: Request,
            _scope: int = Depends(require_student_scope),
        ):
            return {"student_id": request.state.student_id}

        def override_get_db():
            session = self.Session()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = override_get_db
        jwt = JWTService()
        with patch.object(settings, "JWT_SECRET_KEY", "test-secret-key-with-at-least-32-bytes"), patch.object(
            settings, "REQUIRE_AUTHENTICATED_STUDENT", True
        ), patch("app.core.auth_middleware.SessionLocal", self.Session):
            token = jwt.create_access_token(self.student.id)
            client = TestClient(app)
            self.assertEqual(client.get(f"/api/protected/{self.student.id}").status_code, 401)
            invalid = client.get(
                f"/api/protected/{self.student.id}",
                headers={"Authorization": "Bearer invalid"},
            )
            own = client.get(
                f"/api/protected/{self.student.id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            other = client.get(
                f"/api/protected/{self.other.id}",
                headers={"Authorization": f"Bearer {token}"},
            )
        self.assertEqual(own.status_code, 200)
        self.assertEqual(invalid.status_code, 401)
        self.assertEqual(own.json()["student_id"], self.student.id)
        self.assertEqual(other.status_code, 403)

    def test_strict_student_course_and_subject_routes_never_enumerate_other_users(self):
        own_course = Course(name="Own Course", student_id=self.student.id)
        other_course = Course(name="Other Course", student_id=self.other.id)
        self.db.add_all([own_course, other_course])
        self.db.flush()
        self.db.add_all([
            Subject(name="Own Subject", course_id=own_course.id),
            Subject(name="Other Subject", course_id=other_course.id),
        ])
        self.db.commit()

        from app.main import app as api_app

        def override_get_db():
            session = self.Session()
            try:
                yield session
            finally:
                session.close()

        api_app.dependency_overrides[get_db] = override_get_db
        with patch.object(settings, "JWT_SECRET_KEY", "test-secret-key-with-at-least-32-bytes"), patch.object(
            settings, "REQUIRE_AUTHENTICATED_STUDENT", True
        ), patch("app.core.auth_middleware.SessionLocal", self.Session):
            token = JWTService().create_access_token(self.student.id)
            client = TestClient(api_app)
            headers = {"Authorization": f"Bearer {token}"}
            students = client.get("/api/students", headers=headers)
            courses = client.get("/api/courses", headers=headers)
            subjects = client.get("/api/subjects", headers=headers)
            creation = client.post(
                "/api/students",
                headers=headers,
                json={"name": "Unverified", "email": "unverified@example.com"},
            )
            mismatched_mis_job = client.post(
                f"/api/mis/jobs?student_id={self.student.id}",
                headers=headers,
                json={"student_id": self.other.id, "resource": "profile"},
            )
        api_app.dependency_overrides.clear()
        self.assertEqual([student["id"] for student in students.json()], [self.student.id])
        self.assertEqual([course["student_id"] for course in courses.json()], [self.student.id])
        self.assertEqual([subject["name"] for subject in subjects.json()], ["Own Subject"])
        self.assertEqual(creation.status_code, 403)
        self.assertEqual(mismatched_mis_job.status_code, 403)


if __name__ == "__main__":
    unittest.main()