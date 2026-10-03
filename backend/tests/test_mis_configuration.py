import unittest
from unittest.mock import patch

from app.core.config import settings
from app.services.mis.client import MISClientError
from app.services.mis.configuration import get_mis_site_configuration


class MISConfigurationTests(unittest.TestCase):
    def test_accepts_https_host_origin(self):
        with (
            patch.object(settings, "SVNIT_MIS_BASE_URL", "https://mis.svnit.ac.in"),
            patch.object(settings, "SVNIT_MIS_CONFIGURATION_JSON", "{}"),
        ):
            self.assertEqual(
                get_mis_site_configuration(),
                ("https://mis.svnit.ac.in", {}),
            )

    def test_rejects_login_path_in_base_url_with_actionable_error(self):
        with (
            patch.object(
                settings,
                "SVNIT_MIS_BASE_URL",
                "https://mis.svnit.ac.in/Login.aspx",
            ),
            patch.object(settings, "SVNIT_MIS_CONFIGURATION_JSON", "{}"),
        ):
            with self.assertRaisesRegex(MISClientError, "host origin only"):
                get_mis_site_configuration()

    def test_rejects_missing_or_non_https_base_url_with_actionable_error(self):
        for base_url, expected_message in (
            ("", "SVNIT_MIS_BASE_URL is not set"),
            ("http://mis.svnit.ac.in", "must use HTTPS"),
            ("https://", "must use HTTPS"),
        ):
            with self.subTest(base_url=base_url):
                with (
                    patch.object(settings, "SVNIT_MIS_BASE_URL", base_url),
                    patch.object(settings, "SVNIT_MIS_CONFIGURATION_JSON", "{}"),
                ):
                    with self.assertRaisesRegex(MISClientError, expected_message):
                        get_mis_site_configuration()


if __name__ == "__main__":
    unittest.main()
