import unittest
from unittest.mock import Mock, patch

from fastapi import APIRouter, FastAPI, Request
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.rate_limit import limiter
from app.api.responses import handle_rate_limit_error
from app.core.config import Settings, settings
from app.core.cors import add_cors_middleware
from app.db.database import Base, get_db
from app.db.models import Course, Student, Subject
from app.main import app as api_app
from app.models import ChatSession, Topic
from app.services.auth.jwt_service import JWTService


class ApiHardeningTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.db = self.Session()
        self.owner = Student(name="API Owner", email="api-owner@example.com")
        self.other = Student(name="Other Owner", email="api-other@example.com")
        self.owner_course = Course(name="Owner Course", student=self.owner)
        self.other_course = Course(name="Other Course", student=self.other)
        self.owner_subject = Subject(name="Owner Subject", course=self.owner_course)
        self.other_subject = Subject(name="Other Subject", course=self.other_course)
        self.owner_topic = Topic(subject_id=1, name="Owner Topic")
        self.other_topic = Topic(subject_id=2, name="Other Topic")
        self.db.add_all(
            [
                self.owner,
                self.other,
                self.owner_course,
                self.other_course,
                self.owner_subject,
                self.other_subject,
            ]
        )
        self.db.flush()
        self.owner_topic.subject_id = self.owner_subject.id
        self.other_topic.subject_id = self.other_subject.id
        self.db.add_all([self.owner_topic, self.other_topic])
        self.chat_session = ChatSession(student_id=self.other.id, title="Private chat")
        self.db.add(self.chat_session)
        self.db.commit()

        self._old_overrides = api_app.dependency_overrides.copy()
        api_app.dependency_overrides[get_db] = self._get_db
        self._settings_patches = [
            patch.object(settings, "REQUIRE_AUTHENTICATED_STUDENT", True),
            patch.object(settings, "JWT_SECRET_KEY", "api-hardening-test-secret-32-bytes"),
        ]
        for setting_patch in self._settings_patches:
            setting_patch.start()
        self._session_local_patch = patch(
            "app.core.auth_middleware.SessionLocal",
            side_effect=lambda: self.Session(),
        )
        self._session_local_patch.start()
        self.client = TestClient(api_app)
        self.owner_headers = self._auth_headers(self.owner.id)
        self.other_headers = self._auth_headers(self.other.id)

    def tearDown(self):
        self.client.close()
        self._session_local_patch.stop()
        for setting_patch in reversed(self._settings_patches):
            setting_patch.stop()
        api_app.dependency_overrides.clear()
        api_app.dependency_overrides.update(self._old_overrides)
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _get_db(self):
        session = self.Session()
        try:
            yield session
        finally:
            session.close()

    @staticmethod
    def _auth_headers(student_id: int) -> dict[str, str]:
        return {"Authorization": f"Bearer {JWTService().create_access_token(student_id)}"}

    def test_cross_account_course_subject_topic_and_chat_access_is_denied(self):
        for path in (
            f"/api/courses/{self.other_course.id}",
            f"/api/subjects/{self.other_subject.id}",
            f"/api/topics/{self.other_topic.id}",
            f"/api/chat/sessions/{self.chat_session.id}",
        ):
            with self.subTest(path=path):
                response = self.client.get(path, headers=self.owner_headers)
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json()["success"], False)
                self.assertEqual(response.json()["error"]["code"], "forbidden")
                self.assertTrue(response.json()["error"]["message"])

    def test_topic_listing_is_scoped_to_authenticated_student(self):
        response = self.client.get("/api/topics", headers=self.owner_headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["success"], True)
        self.assertEqual(
            [topic["name"] for topic in response.json()["data"]],
            ["Owner Topic"],
        )

    def test_subject_mastery_and_learning_session_reject_foreign_subjects(self):
        mastery = self.client.get(
            f"/api/mastery/subject/{self.other_subject.id}",
            params={"student_id": self.owner.id},
            headers=self.owner_headers,
        )
        self.assertEqual(mastery.status_code, 404)
        self.assertEqual(mastery.json()["error"]["code"], "not_found")

        learning = self.client.post(
            "/api/learning/session",
            json={
                "student_id": self.owner.id,
                "subject_id": self.other_subject.id,
                "activity_type": "quiz",
            },
            headers=self.owner_headers,
        )
        self.assertEqual(learning.status_code, 404)
        self.assertEqual(learning.json()["error"]["code"], "not_found")

    def test_quiz_cannot_reference_another_students_topic(self):
        response = self.client.post(
            "/api/quizzes/generate",
            headers=self.owner_headers,
            json={
                "student_id": self.owner.id,
                "subject_id": self.owner_subject.id,
                "questions": [
                    {
                        "topic_id": self.other_topic.id,
                        "question": "Cross-account topic",
                        "question_type": "short_answer",
                        "correct_answer": "blocked",
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "not_found")

    def test_debug_retrieval_requires_a_subject_and_filters_chroma_to_owner(self):
        unrestricted = self.client.get(
            "/api/rag/debug-search",
            params={"query": "private"},
            headers=self.owner_headers,
        )
        self.assertEqual(unrestricted.status_code, 422)

        collection = Mock()
        collection.get.return_value = {
            "ids": ["owner-chunk"],
            "metadatas": [{"subject_id": self.owner_subject.id}],
        }
        with patch("app.services.vector_service.get_collection", return_value=collection):
            response = self.client.get(
                "/api/debug/chroma",
                headers=self.owner_headers,
            )
        self.assertEqual(response.status_code, 200)
        collection.get.assert_called_once_with(
            where={"subject_id": {"$in": [self.owner_subject.id]}}
        )

    def test_success_and_error_responses_use_the_standard_envelopes(self):
        success = self.client.get(
            f"/api/courses/{self.owner_course.id}",
            headers=self.owner_headers,
        )
        self.assertEqual(success.status_code, 200)
        self.assertEqual(set(success.json()), {"success", "data"})
        self.assertTrue(success.json()["success"])
        self.assertEqual(success.json()["data"]["id"], self.owner_course.id)

        failure = self.client.get("/api/auth/me")
        self.assertEqual(failure.status_code, 401)
        self.assertEqual(
            set(failure.json()),
            {"success", "error"},
        )
        self.assertEqual(
            set(failure.json()["error"]),
            {"code", "message"},
        )

    def test_all_openapi_operations_declare_success_response_schemas(self):
        schema = api_app.openapi()
        operations = 0
        for path_item in schema["paths"].values():
            for method, operation in path_item.items():
                if method not in {"get", "post", "put", "patch", "delete", "options"}:
                    continue
                operations += 1
                success_responses = [
                    response
                    for code, response in operation["responses"].items()
                    if code.startswith("2")
                ]
                self.assertTrue(success_responses, operation["operationId"])
                self.assertTrue(
                    any(
                        response.get("content", {})
                        .get("application/json", {})
                        .get("schema")
                        for response in success_responses
                    ),
                    operation["operationId"],
                )
        self.assertGreater(operations, 100)

    def test_auth_rag_chat_and_upload_routes_have_explicit_limits(self):
        required = {
            "app.api.routes.auth.login_with_google",
            "app.api.routes.auth.refresh_access_token",
            "app.api.routes.auth.get_me",
            "app.api.routes.auth.logout",
            "app.api.routes.rag.ask",
            "app.api.routes.rag.rag_debug_search",
            "app.api.routes.chat.post_chat",
            "app.api.routes.chat.post_chat_session",
            "app.api.routes.chat.get_chat_sessions",
            "app.api.routes.chat.get_chat_session",
            "app.api.routes.chat.get_chat_messages",
            "app.api.routes.chat.delete_chat_session",
            "app.api.routes.study_materials._upload_material_background",
            "app.api.routes.study_materials.enqueue_material_embedding",
        }
        self.assertTrue(required.issubset(limiter._route_limits))

    def test_rate_limit_errors_use_the_standard_error_envelope(self):
        router = APIRouter()

        @router.get("/limited")
        @limiter.limit("1/minute")
        def limited(request: Request):
            return {"ok": True}

        app = FastAPI()
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, handle_rate_limit_error)
        app.add_middleware(SlowAPIMiddleware)
        app.include_router(router)

        with TestClient(app, client=("api-hardening-429", 6147)) as client:
            self.assertEqual(client.get("/limited").status_code, 200)
            limited_response = client.get("/limited")

        self.assertEqual(limited_response.status_code, 429)
        self.assertEqual(
            limited_response.json(),
            {
                "success": False,
                "error": {
                    "code": "rate_limited",
                    "message": "Too many requests.",
                },
            },
        )


class CorsConfigurationTests(unittest.TestCase):
    def test_configured_origins_are_applied_and_unlisted_origins_are_rejected(self):
        configured = Settings(
            DATABASE_URL="sqlite://",
            GROQ_API_KEY="test-key",
            ENVIRONMENT="test",
            ALLOWED_ORIGINS="https://frontend.example.test, http://localhost:3000",
        )
        app = FastAPI()
        app.get("/resource")(lambda: {"ok": True})
        add_cors_middleware(app, configured.allowed_origins)

        with TestClient(app) as client:
            allowed = client.options(
                "/resource",
                headers={
                    "Origin": "https://frontend.example.test",
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "authorization",
                },
            )
            denied = client.options(
                "/resource",
                headers={
                    "Origin": "https://unlisted.example.test",
                    "Access-Control-Request-Method": "GET",
                },
            )

        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(
            allowed.headers["access-control-allow-origin"],
            "https://frontend.example.test",
        )
        self.assertEqual(allowed.headers["access-control-allow-credentials"], "true")
        self.assertNotIn("access-control-allow-origin", denied.headers)

    def test_wildcard_origins_are_rejected_with_credentials(self):
        with self.assertRaises(ValueError):
            add_cors_middleware(FastAPI(), ["*"])

    def test_production_settings_reject_wildcard_origins(self):
        with self.assertRaises(ValueError):
            Settings(
                DATABASE_URL="postgresql://db/jarvis",
                GROQ_API_KEY="groq-key",
                ENVIRONMENT="production",
                GOOGLE_CLIENT_ID="google-client",
                JWT_SECRET_KEY="j" * 32,
                ALLOWED_ORIGINS="*",
            )


if __name__ == "__main__":
    unittest.main()
