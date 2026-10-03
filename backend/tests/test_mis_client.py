import base64
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from cryptography.hazmat.primitives.asymmetric import padding, rsa
from requests import Session

from app.services.mis.client import MISAuthenticationError, MISClient
from app.services.mis.rsa import encrypt_password


def _hex(value: int) -> str:
    return format(value, "x")


class MISClientTests(unittest.TestCase):
    def setUp(self):
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        numbers = self.private_key.public_key().public_numbers()
        self.modulus = _hex(numbers.n)
        self.exponent = _hex(numbers.e)
        self.html = f"""
        <form action="signin">
          <input type="hidden" name="__VIEWSTATE" value="state">
          <input type="hidden" name="__VIEWSTATEGENERATOR" value="generator">
          <input type="hidden" name="__EVENTVALIDATION" value="validation">
          <input type="hidden" name="hdnRsaModulus" value="{self.modulus}">
          <input type="hidden" name="hdnRsaExponent" value="{self.exponent}">
          <input name="ctl00$Main$txtUserName"><input name="ctl00$Main$txtCaptcha">
          <img id="captchaImage" src="/captcha.png">
        </form>
        """
        self.session = Mock()
        self.login_response = SimpleNamespace(
            text=self.html,
            url="https://mis.example/login",
            headers={},
            content=b"",
            raise_for_status=Mock(),
        )
        self.captcha_response = SimpleNamespace(
            content=b"png-image",
            headers={"Content-Type": "image/png"},
            raise_for_status=Mock(),
        )
        self.success_response = SimpleNamespace(
            text="<html><h1>Welcome</h1></html>",
            url="https://mis.example/home",
            history=[object()],
            raise_for_status=Mock(),
        )
        self.session.get.side_effect = [self.login_response, self.captcha_response]
        self.session.post.return_value = self.success_response

    def test_fetch_page_and_login_reuse_session_and_hidden_fields(self):
        client = MISClient(
            "https://mis.example",
            {"resources": {"profile": "/student/profile"}},
            session=self.session,
        )
        page = client.fetch_login_page()
        self.assertEqual(page.captcha_image_url, "https://mis.example/captcha.png")
        self.assertTrue(page.captcha_image.startswith("data:image/png;base64,"))
        client.login({"username": "student", "password": "private", "captcha": "1234"})
        payload = self.session.post.call_args.kwargs["data"]
        self.assertEqual(payload["__VIEWSTATE"], "state")
        self.assertEqual(payload["__VIEWSTATEGENERATOR"], "generator")
        self.assertEqual(payload["__EVENTVALIDATION"], "validation")
        self.assertEqual(payload["ctl00$Main$txtUserName"], "student")
        self.assertEqual(payload["ctl00$Main$txtCaptcha"], "1234")
        self.assertNotEqual(payload["hdnEncPwd"], "private")
        cipher = bytes.fromhex(payload["hdnEncPwd"])
        plaintext = self.private_key.decrypt(cipher, padding.PKCS1v15())
        self.assertEqual(plaintext, b"private")
        self.assertTrue(client.is_logged_in())
        self.assertEqual(self.session.get.call_count, 2)
        client.close()

    def test_browser_pkcs1_hex_payload_can_be_decoded(self):
        encrypted = encrypt_password("password", self.modulus, self.exponent)
        decoded = self.private_key.decrypt(bytes.fromhex(encrypted), padding.PKCS1v15())
        self.assertEqual(decoded, b"password")
        encoded = encrypt_password("password", self.modulus, self.exponent, "base64")
        self.assertEqual(
            self.private_key.decrypt(base64.b64decode(encoded), padding.PKCS1v15()),
            b"password",
        )

    def test_svnit_form_fields_and_rsa_ciphertext_are_submitted(self):
        html = f"""
        <form method="post" action="./default.aspx?return=%2fSVNIT%2f">
          <input type="hidden" name="__VIEWSTATE" value="view-state">
          <input type="hidden" name="__VIEWSTATEGENERATOR" value="generator">
          <input type="hidden" name="__VIEWSTATEENCRYPTED" value="encrypted-view-state">
          <input type="hidden" name="__EVENTVALIDATION" value="event-validation">
          <input type="hidden" name="hdnRsaModulus" value="{self.modulus}">
          <input type="hidden" name="hdnRsaExponent" value="{self.exponent}">
          <input type="hidden" name="hdnEncPwd" value="">
          <input type="text" name="txt_username">
          <input type="password" name="txt_password">
          <input type="text" name="txtcaptcha">
          <img src="CaptchaImage.axd?guid=challenge">
          <input type="image" name="ImageButton1" onclick="submitLogin()">
        </form>
        """
        self.session.get.side_effect = [
            SimpleNamespace(
                text=html,
                url="https://mis.example/SVNIT/",
                headers={},
                content=b"",
                raise_for_status=Mock(),
            ),
            self.captcha_response,
        ]
        self.session.post.return_value = SimpleNamespace(
            text="<html><h1>Welcome</h1></html>",
            url="https://mis.example/Student/Profile.aspx",
            history=[object()],
            status_code=200,
            raise_for_status=Mock(),
        )
        client = MISClient(
            "https://mis.example",
            {
                "login_path": "/SVNIT/",
                "login_fields": {
                    "username": "txt_username",
                    "encrypted_password": "hdnEncPwd",
                    "captcha": "txtcaptcha",
                },
                "rsa_ciphertext_encoding": "base64",
            },
            session=self.session,
        )

        client.fetch_login_page()
        client.login(
            {"username": "student", "password": "private", "captcha": "1234"}
        )

        submitted = self.session.post.call_args.kwargs["data"]
        self.assertEqual(submitted["txt_username"], "student")
        self.assertEqual(submitted["txtcaptcha"], "1234")
        self.assertEqual(submitted["__VIEWSTATE"], "view-state")
        self.assertEqual(submitted["__VIEWSTATEGENERATOR"], "generator")
        self.assertEqual(submitted["__VIEWSTATEENCRYPTED"], "encrypted-view-state")
        self.assertEqual(submitted["__EVENTVALIDATION"], "event-validation")
        self.assertEqual(submitted["hdnRsaModulus"], self.modulus)
        self.assertEqual(submitted["hdnRsaExponent"], self.exponent)
        self.assertNotIn("txt_password", submitted)
        self.assertEqual(submitted["ImageButton1.x"], "0")
        self.assertEqual(submitted["ImageButton1.y"], "0")
        encrypted = base64.b64decode(submitted["hdnEncPwd"], validate=True)
        self.assertEqual(
            self.private_key.decrypt(encrypted, padding.PKCS1v15()),
            b"private",
        )
        client.close()

    def test_failed_login_logs_redacted_response_diagnostics(self):
        self.session.post.return_value = SimpleNamespace(
            text=(
                '<form><input name="ctl00$Main$txtUserName">'
                '<input name="hdnEncPwd"></form><div>Invalid captcha</div>'
            ),
            url="https://mis.example/login",
            history=[],
            status_code=200,
            raise_for_status=Mock(),
        )
        client = MISClient("https://mis.example", session=self.session)
        client._login_html = self.html
        client._auth._login_html = self.html
        client._auth._login_url = "https://mis.example/login"

        with self.assertLogs("app.services.mis.auth", level="WARNING") as captured:
            with self.assertRaises(MISAuthenticationError) as error:
                client.login(
                    {"username": "student-private", "password": "private-secret", "captcha": "1234"}
                )

        self.assertEqual(error.exception.code, "INVALID_CAPTCHA")
        diagnostic = "\n".join(captured.output)
        self.assertIn("captcha_rejected", diagnostic)
        self.assertIn("Invalid captcha", diagnostic)
        self.assertNotIn("student-private", diagnostic)
        self.assertNotIn("private-secret", diagnostic)
        self.assertNotIn("1234", diagnostic)
        client.close()

    def test_failed_login_diagnostics_distinguish_credentials_from_unknown_rejection(self):
        client = MISClient("https://mis.example", session=self.session)
        client._login_html = self.html
        client._auth._login_html = self.html
        client._auth._login_url = "https://mis.example/login"
        cases = (
            ("Invalid password", "credentials_rejected"),
            (
                "Please try again",
                "login_form_returned_without_recognized_rejection_reason",
            ),
        )
        for message, classification in cases:
            with self.subTest(classification=classification):
                self.session.post.return_value = SimpleNamespace(
                    text=(
                        '<form><input name="hdnRsaModulus">'
                        '<input name="hdnEncPwd"></form>'
                        f"<div>{message}</div>"
                    ),
                    url="https://mis.example/login",
                    history=[],
                    status_code=200,
                    raise_for_status=Mock(),
                )
                with self.assertLogs("app.services.mis.auth", level="WARNING") as captured:
                    with self.assertRaises(MISAuthenticationError):
                        client.login(
                            {
                                "username": "student-private",
                                "password": "private-secret",
                                "captcha": "1234",
                            }
                        )
                self.assertIn(classification, "\n".join(captured.output))
        client.close()

    def test_login_refuses_to_submit_plaintext_if_key_is_missing(self):
        from app.services.mis.auth import MISAuth

        auth = MISAuth("https://mis.example", Mock())
        with self.assertRaises(Exception):
            auth.build_login_payload({"username": "student", "password": "secret"}, "<form></form>")

    def test_session_state_round_trips_cookies_and_pending_form(self):
        client = MISClient("https://mis.example", session=Session())
        client.session.cookies.set(
            "ASP.NET_SessionId", "opaque-session", domain="mis.example", path="/"
        )
        client._login_html = "<form>pending</form>"
        client._auth._login_url = "https://mis.example/login"
        state = client.export_session_state(include_login_page=True)

        restored = MISClient("https://mis.example", session=Session())
        restored.restore_session_state(state)
        self.assertEqual(restored.session.cookies.get("ASP.NET_SessionId"), "opaque-session")
        self.assertTrue(restored.has_login_challenge)
        self.assertEqual(restored._auth._login_url, "https://mis.example/login")
        client.close()
        restored.close()


if __name__ == "__main__":
    unittest.main()
