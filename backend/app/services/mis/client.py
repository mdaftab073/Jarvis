from urllib.parse import urljoin, urlparse

import requests

from app.services.mis.auth import MISAuth, MISAuthResult


class MISClientError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 502):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class MISAuthenticationError(MISClientError):
    def __init__(self, message: str, code: str = "authentication_failed", required: list[str] | None = None):
        super().__init__(code, message, 422)
        self.required = required or []


class MISClient:
    def __init__(self, base_url: str, configuration: dict | None = None, session=None, password_encryptor=None):
        parsed = urlparse(base_url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise MISClientError("invalid_endpoint", "MIS endpoint must be a trusted HTTPS URL", 422)
        self.base_url = base_url.rstrip("/") + "/"
        self.configuration = configuration or {}
        self.session = session or requests.Session()
        self.timeout = self.configuration.get("timeout", 15)
        self.password_encryptor = password_encryptor
        self._auth = MISAuth(self.base_url, self.session, self.configuration, password_encryptor)
        self._logged_in = False

    def _path(self, resource: str) -> str:
        resources = self.configuration.get("resources") or {}
        path = resources.get(resource)
        if resource == "results":
            path = path or resources.get("grades")
        path = path or {
            "profile": "/profile",
            "attendance": "/attendance",
            "results": "/results",
            "timetable": "/timetable",
        }.get(resource)
        if not path:
            raise MISClientError("resource_not_configured", f"MIS resource {resource!r} is not configured", 422)
        if not path.startswith("/") or path.startswith("//") or "://" in path:
            raise MISClientError("invalid_resource_path", "MIS resource paths must be relative paths", 422)
        return path

    def login(self, credentials: dict[str, str]) -> MISAuthResult:
        try:
            result = self._auth.login(credentials)
        except requests.RequestException as error:
            raise MISClientError("request_failed", "MIS authentication request failed") from error
        if result.error_code == "request_failed":
            raise MISClientError(result.error_code, result.message or "MIS authentication request failed")
        self._logged_in = result.authenticated
        if not result.authenticated and result.requires:
            raise MISAuthenticationError(
                result.message or "MIS login needs additional input",
                result.error_code or "authentication_setup_required",
                result.requires,
            )
        if not result.authenticated:
            raise MISAuthenticationError(
                result.message or "MIS login was rejected",
                result.error_code or "authentication_failed",
            )
        return result

    def logout(self) -> None:
        path = self.configuration.get("logout_path")
        try:
            if self._logged_in and path:
                response = self.session.get(urljoin(self.base_url, path), timeout=self.timeout)
                response.raise_for_status()
        except requests.RequestException as error:
            raise MISClientError("logout_failed", "MIS logout request failed") from error
        finally:
            self._logged_in = False
            self.session.close()

    def is_logged_in(self) -> bool:
        return self._logged_in

    def refresh_session(self, credentials: dict[str, str]) -> MISAuthResult:
        if not self._logged_in:
            self.session = requests.Session()
            self._auth = MISAuth(self.base_url, self.session, self.configuration, self.password_encryptor)
        self._logged_in = False
        return self.login(credentials)

    def get_authenticated_page(self, path: str) -> str:
        if not self.is_logged_in():
            raise MISAuthenticationError("MIS session is not authenticated", "session_expired")
        if not path.startswith("/") or path.startswith("//") or "://" in path:
            raise MISClientError("invalid_resource_path", "MIS page paths must be relative paths", 422)
        try:
            response = self.session.get(urljoin(self.base_url, path.lstrip("/")), timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as error:
            raise MISClientError("request_failed", "MIS page request failed") from error

    def _fetch(self, resource: str) -> str:
        return self.get_authenticated_page(self._path(resource))

    def fetch_student_profile(self) -> str:
        return self._fetch("profile")

    def fetch_attendance(self) -> str:
        return self._fetch("attendance")

    def fetch_results(self) -> str:
        return self._fetch("results")

    def fetch_timetable(self) -> str:
        return self._fetch("timetable")