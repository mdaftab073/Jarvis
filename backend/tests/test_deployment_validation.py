import unittest
from unittest.mock import patch

from app.core.config import settings
from scripts.validate_deployment import environment_status, format_report


class DeploymentValidationTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()