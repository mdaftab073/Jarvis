import unittest
import os
import json
from unittest.mock import Mock, patch

from cryptography.fernet import Fernet
from pydantic import ValidationError

from app.core.config import settings
from app.core.config import Settings
from app.main import validate_startup_dependencies
from scripts.validate_deployment import environment_status, format_report, health_status
from scripts.validate_production import validate_endpoint


class DeploymentValidationTests(unittest.TestCase):
    def test_production_settings_reject_disabled_student_authentication(self):
        with self.assertRaises(ValidationError):
            Settings(
                DATABASE_URL="postgresql://db/jarvis",
                GROQ_API_KEY="groq-test",
                ENVIRONMENT="production",
                REQUIRE_AUTHENTICATED_STUDENT=False,
                JWT_SECRET_KEY="j" * 32,
                GOOGLE_CLIENT_ID="google-client",
                METRICS_ADMIN_TOKEN="metrics-token",
                CONNECTOR_ENCRYPTION_KEY=Fernet.generate_key().decode(),
                ALLOWED_ORIGINS="https://frontend.example.test",
            )

    def test_student_authentication_is_enabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            configured = Settings(
                DATABASE_URL="postgresql://db/jarvis",
                GROQ_API_KEY="groq-test",
                ENVIRONMENT="test",
            )
        self.assertTrue(configured.REQUIRE_AUTHENTICATED_STUDENT)

    def test_production_settings_require_jwt_secret(self):
        with self.assertRaisesRegex(ValidationError, "JWT_SECRET_KEY"):
            Settings(
                DATABASE_URL="postgresql://db/jarvis",
                GROQ_API_KEY="groq-test",
                ENVIRONMENT="production",
                GOOGLE_CLIENT_ID="google-client",
                METRICS_ADMIN_TOKEN="metrics-token",
                CONNECTOR_ENCRYPTION_KEY=Fernet.generate_key().decode(),
                ALLOWED_ORIGINS="https://frontend.example.test",
            )

    def test_production_settings_accept_valid_secrets(self):
        configured = Settings(
            DATABASE_URL="postgresql://db/jarvis",
            GROQ_API_KEY="groq-test",
            ENVIRONMENT="production",
            REQUIRE_AUTHENTICATED_STUDENT=True,
            JWT_SECRET_KEY="j" * 32,
            GOOGLE_CLIENT_ID="google-client",
            METRICS_ADMIN_TOKEN="metrics-token",
            CONNECTOR_ENCRYPTION_KEY=Fernet.generate_key().decode(),
            ALLOWED_ORIGINS="https://frontend.example.test",
        )

        self.assertTrue(configured.REQUIRE_AUTHENTICATED_STUDENT)

    def test_production_settings_require_a_frontend_origin(self):
        with self.assertRaisesRegex(ValidationError, "ALLOWED_ORIGINS"):
            Settings(
                DATABASE_URL="postgresql://db/jarvis",
                GROQ_API_KEY="groq-test",
                ENVIRONMENT="production",
                REQUIRE_AUTHENTICATED_STUDENT=True,
                JWT_SECRET_KEY="j" * 32,
                GOOGLE_CLIENT_ID="google-client",
                METRICS_ADMIN_TOKEN="metrics-token",
                CONNECTOR_ENCRYPTION_KEY=Fernet.generate_key().decode(),
            )

    def test_production_settings_reject_placeholder_secrets(self):
        with self.assertRaisesRegex(ValidationError, "real production value"):
            Settings(
                DATABASE_URL="postgresql://db/jarvis",
                GROQ_API_KEY="groq-test",
                ENVIRONMENT="production",
                JWT_SECRET_KEY="replace-with-at-least-32-random-bytes",
                GOOGLE_CLIENT_ID="google-client",
                METRICS_ADMIN_TOKEN="metrics-token",
                CONNECTOR_ENCRYPTION_KEY=Fernet.generate_key().decode(),
                ALLOWED_ORIGINS="https://frontend.example.test",
            )

    def test_production_settings_require_a_valid_connector_key(self):
        with self.assertRaisesRegex(ValidationError, "valid Fernet key"):
            Settings(
                DATABASE_URL="postgresql://db/jarvis",
                GROQ_API_KEY="groq-test",
                ENVIRONMENT="production",
                JWT_SECRET_KEY="j" * 32,
                GOOGLE_CLIENT_ID="google-client",
                METRICS_ADMIN_TOKEN="metrics-token",
                CONNECTOR_ENCRYPTION_KEY="not-a-fernet-key",
                ALLOWED_ORIGINS="https://frontend.example.test",
            )

    def test_production_startup_fails_when_database_is_unavailable(self):
        with (
            patch.object(settings, "ENVIRONMENT", "production"),
            patch("app.main.engine.connect", side_effect=OSError("offline")),
        ):
            with self.assertRaisesRegex(RuntimeError, "PostgreSQL connectivity check failed"):
                validate_startup_dependencies()

    def test_production_startup_fails_when_chromadb_is_unavailable(self):
        connection = Mock()
        connection.__enter__ = Mock(return_value=connection)
        connection.__exit__ = Mock(return_value=False)
        collection = Mock()
        collection.count.side_effect = OSError("offline")
        with (
            patch.object(settings, "ENVIRONMENT", "production"),
            patch("app.main.engine.connect", return_value=connection),
            patch("app.main.get_collection", return_value=collection),
        ):
            with self.assertRaisesRegex(RuntimeError, "ChromaDB initialization check failed"):
                validate_startup_dependencies()

    def test_nonproduction_startup_skips_external_dependency_checks(self):
        with (
            patch.object(settings, "ENVIRONMENT", "test"),
            patch("app.main.engine.connect") as database_connect,
            patch("app.main.get_collection") as get_collection,
        ):
            validate_startup_dependencies()
        database_connect.assert_not_called()
        get_collection.assert_not_called()

    def test_environment_requires_strict_auth_and_complete_credentials(self):
        with (
            patch.object(settings, "DATABASE_URL", "postgresql://db/jarvis"),
            patch.object(settings, "GROQ_API_KEY", "groq-test"),
            patch.object(settings, "GOOGLE_CLIENT_ID", "google-client"),
            patch.object(settings, "JWT_SECRET_KEY", "x" * 32),
            patch.object(settings, "JWT_ALGORITHM", "HS256"),
            patch.object(settings, "METRICS_ADMIN_TOKEN", "metrics-token"),
            patch.object(settings, "REQUIRE_AUTHENTICATED_STUDENT", True),
            patch.object(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 15),
            patch.object(settings, "REFRESH_TOKEN_EXPIRE_DAYS", 30),
            patch.object(settings, "BACKGROUND_JOBS_ENABLED", True),
        ):
            passed, detail = environment_status()
        self.assertTrue(passed, detail)

        with patch.object(settings, "REQUIRE_AUTHENTICATED_STUDENT", False):
            passed, detail = environment_status()
        self.assertFalse(passed)
        self.assertIn("REQUIRE_AUTHENTICATED_STUDENT", detail)

    def test_report_marks_failed_checks_and_calls_out_risks(self):
        report = format_report({"environment": {"ok": False, "detail": "missing JWT_SECRET_KEY"}})
        self.assertIn("| Environment | FAIL | missing JWT_SECRET_KEY |", report)
        self.assertIn("## Known Risks", report)
        self.assertIn("not a production sign-off", report)

    def test_deployment_health_check_reads_success_envelope(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.status = 200
        response.read.return_value = json.dumps({
            "success": True,
            "data": {"status": "ready", "ready": True, "database": "ok"},
        }).encode()
        with patch("scripts.validate_deployment.urlopen", return_value=response):
            passed, detail = health_status("http://localhost:8000", "/health/ready")

        self.assertTrue(passed)
        self.assertEqual(detail, "database=ok")

    def test_production_health_check_reads_success_envelope(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.status = 200
        response.read.return_value = json.dumps({
            "success": True,
            "data": {"status": "alive"},
        }).encode()
        with patch("scripts.validate_production.urlopen", return_value=response):
            passed, detail = validate_endpoint("http://localhost:8000", "/health/live")

        self.assertTrue(passed)
        self.assertEqual(detail, "alive")

    def test_health_checks_reject_unwrapped_payload(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.status = 200
        response.read.return_value = json.dumps({"status": "alive"}).encode()
        with patch("scripts.validate_deployment.urlopen", return_value=response):
            passed, detail = health_status("http://localhost:8000", "/health/live")

        self.assertFalse(passed)
        self.assertEqual(detail, "Invalid health response envelope")


if __name__ == "__main__":
    unittest.main()