import logging
import re
from dataclasses import dataclass, field
from typing import Callable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)


@dataclass
class MISLoginPage:
    url: str
    hidden_fields: dict[str, str]
    rsa_modulus: str | None
    rsa_exponent: str | None
    captcha_image_url: str | None
    captcha_image: str | None


class MISAuthError(Exception):
    def __init__(self, code: str, message: str, required: list[str] | None = None):
        super().__init__(message)
        self.code = code
        self.required = required or []


@dataclass
class MISAuthResult:
    authenticated: bool
    requires: list[str] = field(default_factory=list)
    message: str | None = None
    error_code: str | None = None


class MISAuth:
    """Owns WebForms login-page state and delegates institution-specific crypto."""

    def __init__(
        self,
        base_url: str,
        session: requests.Session,
        configuration: dict | None = None,
        password_encryptor: Callable[[str, str, str], str] | None = None,
    ):
        self.base_url = base_url.rstrip("/") + "/"
        self.session = session
        self.configuration = configuration or {}
        self.password_encryptor = password_encryptor
        self.timeout = self.configuration.get("timeout", 15)
        self._login_html: str | None = None
        self._login_url: str | None = None

    def get_login_page(self) -> str:
        path = self.configuration.get("login_path", "/")
        target = urljoin(self.base_url, path)
        base = urlparse(self.base_url)
        destination = urlparse(target)
        if (base.scheme, base.netloc) != (destination.scheme, destination.netloc):
            raise MISAuthError("MIS_UNAVAILABLE", "MIS login path must stay on the configured host")
        response = self.session.get(target, timeout=self.timeout)
        response.raise_for_status()
        response_url = urlparse(response.url)
        if (base.scheme, base.netloc) != (response_url.scheme, response_url.netloc):
            raise MISAuthError("MIS_UNAVAILABLE", "MIS login page redirected outside the configured host")
        self._login_html = response.text
        self._login_url = response.url
        return response.text

    def extract_hidden_fields(self, html: str) -> dict[str, str]:
        soup = BeautifulSoup(html, "html.parser")
        fields = {}
        for element in soup.select('input[type="hidden"][name]'):
            fields[element["name"]] = element.get("value", "")
        return fields

    def _redact_login_values(
        self,
        text: str,
        credentials: dict[str, str],
        payload: dict[str, str],
    ) -> str:
        values = [
            credentials.get("username", ""),
            credentials.get("password", ""),
            credentials.get("captcha", ""),
            payload.get(
                self.configuration.get("login_fields", {}).get(
                    "encrypted_password", "hdnEncPwd"
                ),
                "",
            ),
        ]
        for value in sorted((value for value in values if value), key=len, reverse=True):
            text = re.sub(re.escape(value), "[REDACTED]", text, flags=re.IGNORECASE)
        return text

    def _log_login_failure(
        self,
        response: requests.Response,
        target: str,
        credentials: dict[str, str],
        payload: dict[str, str],
        classification: str,
        matched_marker: str | None = None,
    ) -> None:
        soup = BeautifulSoup(response.text, "html.parser")
        for element in soup.select("script, style, noscript"):
            element.decompose()
        returned_fields = sorted(
            {
                element.get("name")
                for element in soup.select("input[name], select[name], textarea[name], button[name]")
                if element.get("name")
            }
        )
        text = self._redact_login_values(
            " ".join(soup.stripped_strings),
            credentials,
            payload,
        )
        feedback_terms = (
            "captcha",
            "invalid",
            "incorrect",
            "wrong",
            "password",
            "username",
            "user name",
            "login",
            "error",
            "failed",
        )
        feedback = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+|\s{2,}", text)
            if any(term in sentence.casefold() for term in feedback_terms)
        ]
        excerpt = " | ".join(feedback)[:1000] or "<no recognizable login feedback>"
        logger.warning(
            "SVNIT MIS login response rejected: classification=%s status=%s "
            "redirected=%s returned_form_fields=%s matched_marker=%s feedback=%s",
            classification,
            response.status_code,
            bool(getattr(response, "history", []))
            and getattr(response, "url", target) != target,
            returned_fields,
            matched_marker,
            excerpt,
        )

    def fetch_login_page(self) -> MISLoginPage:
        html = self.get_login_page()
        soup = BeautifulSoup(html, "html.parser")
        keys = self.extract_rsa_keys(html)
        if not keys["modulus"] or not keys["exponent"]:
            raise MISAuthError("MIS_UNAVAILABLE", "MIS login page did not expose both RSA key values")
        captcha = soup.select_one(
            self.configuration.get(
                "captcha_image_selector",
                'img[src*="captcha" i], img[id*="captcha" i], img[name*="captcha" i]',
            )
        )
        captcha_url = (
            urljoin(self._login_url or self.base_url, captcha.get("src", ""))
            if captcha is not None
            else None
        )
        captcha_image = None
        if captcha_url:
            base = urlparse(self.base_url)
            target = urlparse(captcha_url)
            if (base.scheme, base.netloc) != (target.scheme, target.netloc):
                raise MISAuthError("MIS_UNAVAILABLE", "MIS captcha image must be served by the configured host")
            if target.scheme != "https":
                raise MISAuthError("MIS_UNAVAILABLE", "MIS captcha image must use HTTPS")
            try:
                response = self.session.get(captcha_url, timeout=self.timeout)
                response.raise_for_status()
            except requests.RequestException as error:
                raise MISAuthError("MIS_UNAVAILABLE", "MIS captcha image request failed") from error
            content_type = getattr(response, "headers", {}).get("Content-Type", "image/png").split(";", 1)[0]
            if content_type not in {"image/png", "image/jpeg", "image/gif", "image/webp"}:
                raise MISAuthError("PARSE_ERROR", "MIS captcha endpoint did not return an image")
            if len(response.content) > 2 * 1024 * 1024:
                raise MISAuthError("PARSE_ERROR", "MIS captcha image exceeds the supported size limit")
            import base64

            captcha_image = f"data:{content_type};base64,{base64.b64encode(response.content).decode('ascii')}"
        return MISLoginPage(
            url=self._login_url or self.base_url,
            hidden_fields=self.extract_hidden_fields(html),
            rsa_modulus=keys["modulus"],
            rsa_exponent=keys["exponent"],
            captcha_image_url=captcha_url,
            captcha_image=captcha_image,
        )

    def extract_rsa_keys(self, html: str) -> dict[str, str | None]:
        soup = BeautifulSoup(html, "html.parser")
        names = self.configuration.get("rsa_fields", {})
        result = {}
        for key, default_name in (("modulus", "hdnRsaModulus"), ("exponent", "hdnRsaExponent")):
            field_name = names.get(key, default_name)
            element = soup.find(attrs={"name": field_name})
            if element is None:
                element = soup.find(id=field_name)
            result[key] = element.get("value") if element is not None else None
        return result

    def encrypt_password(self, password: str, modulus: str, exponent: str) -> str:
        if self.password_encryptor is None:
            raise MISAuthError(
                "MIS_UNAVAILABLE",
                "SVNIT MIS password encryption is not configured",
                ["rsa_password_encryptor"],
            )
        try:
            encrypted = self.password_encryptor(password, modulus, exponent)
        except (ValueError, TypeError) as error:
            raise MISAuthError("MIS_UNAVAILABLE", "MIS password encryption failed") from error
        if not encrypted:
            raise MISAuthError("MIS_UNAVAILABLE", "Password encryption returned no value")
        return encrypted

    def build_login_payload(self, credentials: dict[str, str], html: str) -> dict[str, str]:
        payload = self.extract_hidden_fields(html)
        keys = self.extract_rsa_keys(html)
        if not keys["modulus"] or not keys["exponent"]:
            raise MISAuthError("MIS_UNAVAILABLE", "MIS login page did not expose RSA keys", ["rsa_keys"])
        username = credentials.get("username")
        password = credentials.get("password")
        if not username or not password:
            raise MISAuthError("LOGIN_FAILED", "MIS username and password are required")

        fields = self.configuration.get("login_fields", {})
        soup = BeautifulSoup(html, "html.parser")
        form = soup.find("form") or soup
        username_element = form.select_one(
            'input[name*="username" i], input[id*="username" i], '
            'input[name*="userid" i], input[id*="userid" i]'
        )
        username_field = fields.get("username") or (
            username_element.get("name") or username_element.get("id")
            if username_element is not None
            else "username"
        )
        if fields.get("username") and form.find(attrs={"name": username_field}) is None:
            raise MISAuthError(
                "MIS_UNAVAILABLE",
                f"Configured MIS username field {username_field!r} is not present on the login form",
            )
        payload[username_field] = username
        password_field = fields.get("encrypted_password", "hdnEncPwd")
        if fields.get("encrypted_password") and form.find(attrs={"name": password_field}) is None:
            raise MISAuthError(
                "MIS_UNAVAILABLE",
                f"Configured encrypted password field {password_field!r} is not present on the login form",
            )
        payload[password_field] = self.encrypt_password(password, keys["modulus"], keys["exponent"])

        captcha_element = form.select_one(
            'input[name*="captcha" i], input[id*="captcha" i]'
        )
        captcha_field = fields.get("captcha") or (
            captcha_element.get("name") or captcha_element.get("id")
            if captcha_element is not None
            else "captcha"
        )
        if fields.get("captcha") and form.find(attrs={"name": captcha_field}) is None:
            raise MISAuthError(
                "MIS_UNAVAILABLE",
                f"Configured MIS captcha field {captcha_field!r} is not present on the login form",
            )
        captcha = credentials.get("captcha")
        has_captcha = captcha_element is not None or form.select_one(
            'img[src*="captcha" i], img[id*="captcha" i], img[name*="captcha" i]'
        ) is not None
        if has_captcha and not captcha:
            raise MISAuthError("INVALID_CAPTCHA", "MIS login requires a captcha value", ["captcha"])
        if captcha:
            payload[captcha_field] = captcha
        image_submit = form.select_one('input[type="image"][name]')
        if image_submit is not None:
            image_name = image_submit["name"]
            payload[f"{image_name}.x"] = "0"
            payload[f"{image_name}.y"] = "0"
        for name, value in self.configuration.get("submit_fields", {}).items():
            payload[name] = str(value)
        return payload

    def login(self, credentials: dict[str, str], html: str | None = None) -> MISAuthResult:
        if html is None:
            try:
                html = self.get_login_page()
            except requests.HTTPError as error:
                code = "PAGE_NOT_FOUND" if error.response is not None and error.response.status_code == 404 else "MIS_UNAVAILABLE"
                return MISAuthResult(False, message="MIS login page request failed", error_code=code)
            except requests.RequestException:
                return MISAuthResult(False, message="MIS login page request failed", error_code="MIS_UNAVAILABLE")
        try:
            payload = self.build_login_payload(credentials, html)
        except MISAuthError as error:
            return MISAuthResult(False, error.required, str(error), error.code)

        soup = BeautifulSoup(html, "html.parser")
        form = soup.find("form")
        action = form.get("action", "") if form else ""
        target = urljoin(self._login_url or self.base_url, action)
        base = urlparse(self.base_url)
        destination = urlparse(target)
        if (base.scheme, base.netloc) != (destination.scheme, destination.netloc):
            return MISAuthResult(
                False,
                message="MIS login form action must stay on the configured host",
                error_code="MIS_UNAVAILABLE",
            )
        encrypted_password_field = self.configuration.get("login_fields", {}).get(
            "encrypted_password", "hdnEncPwd"
        )
        logger.info(
            "Submitting SVNIT MIS login form: field_names=%s encrypted_password_present=%s",
            sorted(payload),
            bool(payload.get(encrypted_password_field)),
        )
        try:
            response = self.session.post(target, data=payload, timeout=self.timeout)
            response.raise_for_status()
        except requests.HTTPError as error:
            response = error.response
            if response is not None:
                self._log_login_failure(
                    response,
                    target,
                    credentials,
                    payload,
                    "http_error_response",
                )
            code = "PAGE_NOT_FOUND" if error.response is not None and error.response.status_code == 404 else "MIS_UNAVAILABLE"
            return MISAuthResult(False, message="MIS login submission failed", error_code=code)
        except requests.RequestException:
            return MISAuthResult(False, message="MIS login submission failed", error_code="MIS_UNAVAILABLE")
        checker = self.configuration.get("authenticated_marker")
        response_soup = BeautifulSoup(response.text, "html.parser")
        names = self.configuration.get("login_fields", {})
        rsa_names = self.configuration.get("rsa_fields", {})
        username_field = names.get("username", "username")
        still_login = (
            response_soup.find(attrs={"name": username_field}) is not None
            or response_soup.find(attrs={"name": names.get("encrypted_password", "hdnEncPwd")})
            is not None
            or response_soup.find(
                attrs={"name": rsa_names.get("modulus", "hdnRsaModulus")}
            )
            is not None
        )
        final_url = getattr(response, "url", target)
        was_redirected = bool(getattr(response, "history", [])) and final_url != target
        redirected_to_authenticated_location = (
            was_redirected
            and urlparse(final_url).path != urlparse(self._login_url or "").path
        )
        failure_markers = self.configuration.get(
            "authentication_failure_markers",
            ("invalid password", "invalid user", "login failed", "invalid captcha", "wrong captcha"),
        )
        if isinstance(failure_markers, str):
            failure_markers = (failure_markers,)
        matched_failure_marker = next(
            (
                marker
                for marker in failure_markers
                if marker.casefold() in response.text.casefold()
            ),
            None,
        )
        credential_markers = self.configuration.get(
            "credential_failure_markers",
            ("invalid password", "incorrect password", "wrong password", "invalid user", "invalid username"),
        )
        if isinstance(credential_markers, str):
            credential_markers = (credential_markers,)
        matched_credential_marker = next(
            (
                marker
                for marker in credential_markers
                if marker.casefold() in response.text.casefold()
            ),
            None,
        )
        captcha_markers = self.configuration.get(
            "captcha_failure_markers",
            ("invalid captcha", "captcha is incorrect", "wrong captcha"),
        )
        if isinstance(captcha_markers, str):
            captcha_markers = (captcha_markers,)
        matched_captcha_marker = next(
            (
                marker
                for marker in captcha_markers
                if marker.casefold() in response.text.casefold()
            ),
            None,
        )
        if checker:
            authenticated = checker in response.text
        else:
            authenticated = (
                not still_login
                and matched_failure_marker is None
                and (redirected_to_authenticated_location or not was_redirected)
            )
        if not authenticated:
            classification = (
                "captcha_rejected"
                if matched_captcha_marker
                else "credentials_rejected"
                if matched_credential_marker
                else "login_rejected_reason_unspecified"
                if matched_failure_marker
                else "login_form_returned_without_recognized_rejection_reason"
                if still_login
                else "response_did_not_match_authenticated_page"
            )
            self._log_login_failure(
                response,
                target,
                credentials,
                payload,
                classification,
                matched_captcha_marker or matched_credential_marker or matched_failure_marker,
            )
        if not authenticated and matched_captcha_marker:
            return MISAuthResult(
                False,
                message="The captcha was not accepted; fetch a new captcha and try again",
                error_code="INVALID_CAPTCHA",
            )
        if not authenticated:
            return MISAuthResult(
                False,
                message="MIS login was rejected",
                error_code="LOGIN_FAILED",
            )
        
        logger.info(
            "Response URL: %s",
            response.url
        )

        logger.info(
            "Response status: %s",
            response.status_code
        )

        logger.info(
            "Response title: %s",
            soup.title.string if soup.title else "NO TITLE"
        )

        logger.info(
            "Returned controls: %s",
            [
                tag.get("name")
                for tag in soup.select("input[name]")
            ][:50]
        )
        return MISAuthResult(
            authenticated,
            message=None,
            error_code=None,
        )