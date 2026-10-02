from dataclasses import dataclass, field
from typing import Callable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


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
        response = self.session.get(urljoin(self.base_url, path), timeout=self.timeout)
        response.raise_for_status()
        self._login_html = response.text
        self._login_url = response.url
        return response.text

    def extract_hidden_fields(self, html: str) -> dict[str, str]:
        soup = BeautifulSoup(html, "html.parser")
        fields = {}
        for element in soup.select('input[type="hidden"][name]'):
            fields[element["name"]] = element.get("value", "")
        return fields

    def extract_rsa_keys(self, html: str) -> dict[str, str | None]:
        soup = BeautifulSoup(html, "html.parser")
        names = self.configuration.get("rsa_fields", {})
        result = {}
        for key, default_name in (("modulus", "hdnRsaModulus"), ("exponent", "hdnRsaExponent")):
            field_name = names.get(key, default_name)
            element = soup.find(attrs={"name": field_name}) or soup.find(id=field_name)
            result[key] = element.get("value") if element else None
        return result

    def encrypt_password(self, password: str, modulus: str, exponent: str) -> str:
        if self.password_encryptor is None:
            raise MISAuthError(
                "rsa_not_configured",
                "SVNIT MIS password encryption is not configured",
                ["rsa_password_encryptor"],
            )
        encrypted = self.password_encryptor(password, modulus, exponent)
        if not encrypted:
            raise MISAuthError("rsa_encryption_failed", "Password encryption returned no value")
        return encrypted

    def build_login_payload(self, credentials: dict[str, str], html: str) -> dict[str, str]:
        payload = self.extract_hidden_fields(html)
        keys = self.extract_rsa_keys(html)
        if not keys["modulus"] or not keys["exponent"]:
            raise MISAuthError("rsa_keys_missing", "MIS login page did not expose RSA keys", ["rsa_keys"])
        username = credentials.get("username")
        password = credentials.get("password")
        if not username or not password:
            raise MISAuthError("credentials_missing", "MIS username and password are required")

        fields = self.configuration.get("login_fields", {})
        payload[fields.get("username", "username")] = username
        password_field = fields.get("encrypted_password", "hdnEncPwd")
        payload[password_field] = self.encrypt_password(password, keys["modulus"], keys["exponent"])

        captcha_field = fields.get("captcha", "captcha")
        captcha = credentials.get("captcha")
        has_captcha = bool(
            BeautifulSoup(html, "html.parser").select_one(
                'img[src*="captcha" i], input[name*="captcha" i], input[id*="captcha" i]'
            )
        )
        if has_captcha and not captcha:
            raise MISAuthError("captcha_required", "MIS login requires a captcha value", ["captcha"])
        if captcha:
            payload[captcha_field] = captcha
        return payload

    def login(self, credentials: dict[str, str]) -> MISAuthResult:
        try:
            html = self.get_login_page()
        except requests.RequestException:
            return MISAuthResult(False, message="MIS login page request failed", error_code="request_failed")
        try:
            payload = self.build_login_payload(credentials, html)
        except MISAuthError as error:
            return MISAuthResult(False, error.required, str(error), error.code)

        soup = BeautifulSoup(html, "html.parser")
        form = soup.find("form")
        action = form.get("action", "") if form else ""
        target = urljoin(self._login_url or self.base_url, action)
        try:
            response = self.session.post(target, data=payload, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException:
            return MISAuthResult(False, message="MIS login submission failed", error_code="request_failed")
        checker = self.configuration.get("authenticated_marker")
        if checker:
            authenticated = checker in response.text
        else:
            authenticated = not any(
                marker in response.text.lower()
                for marker in ("hdnrsamodulus", "name=\"username\"", "name='username'")
            )
        return MISAuthResult(
            authenticated,
            message=None if authenticated else "MIS login was rejected",
            error_code=None if authenticated else "authentication_failed",
        )