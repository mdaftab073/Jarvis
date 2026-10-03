from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import requests

from app.services.mis.auth import MISAuth, MISAuthError, MISAuthResult, MISLoginPage
from app.services.mis.rsa import MISRSAError, build_rsa_key as make_rsa_key, encrypt_password


class MISClientError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 502):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class MISAuthenticationError(MISClientError):
    def __init__(self, message: str, code: str = "authentication_failed", required: list[str] | None = None):
        super().__init__(code, message, 422)
        self.required = required or []


@dataclass
class MISLoginPageData:
    captcha_image: str | None
    captcha_image_url: str | None
    expires_in_seconds: int
    hidden_fields: dict[str, str]
    rsa_modulus: str | None
    rsa_exponent: str | None


class MISClient:
    def __init__(self, base_url: str, configuration: dict | None = None, session=None, password_encryptor=None):
        parsed = urlparse(base_url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise MISClientError("MIS_UNAVAILABLE", "MIS endpoint must be a trusted HTTPS URL", 422)
        self.base_url = base_url.rstrip("/") + "/"
        self.configuration = configuration or {}
        self.session = session if session is not None else requests.Session()
        self.timeout = self.configuration.get("timeout", 15)
        self.password_encryptor = password_encryptor or self._encrypt_password
        self._auth = MISAuth(self.base_url, self.session, self.configuration, self.password_encryptor)
        self._logged_in = False
        self._login_html: str | None = None
        self.last_source_page: str | None = None

    def _encrypt_password(self, password: str, modulus: str, exponent: str) -> str:
        return encrypt_password(
            password,
            modulus,
            exponent,
            self.configuration.get("rsa_ciphertext_encoding", "hex"),
        )

    def build_rsa_key(self, modulus: str, exponent: str):
        try:
            return make_rsa_key(modulus, exponent)
        except MISRSAError as error:
            raise MISClientError("PARSE_ERROR", str(error), 502) from error

    def close(self) -> None:
        self._logged_in = False
        self.session.close()

    def export_session_state(self, include_login_page: bool = False) -> dict:
        cookies = [
            {
                "name": cookie.name,
                "value": cookie.value,
                "domain": cookie.domain,
                "path": cookie.path,
                "secure": cookie.secure,
                "expires": cookie.expires,
            }
            for cookie in self.session.cookies
        ]
        state = {
            "cookies": cookies,
            "login_url": self._auth._login_url,
            "logged_in": self._logged_in,
        }
        if include_login_page:
            state["login_html"] = self._login_html
        return state

    def restore_session_state(self, state: dict) -> None:
        cookies = state.get("cookies", [])
        if not isinstance(cookies, list):
            raise MISClientError("MIS_UNAVAILABLE", "Stored MIS session state is invalid")
        for cookie in cookies:
            if not isinstance(cookie, dict) or not cookie.get("name"):
                raise MISClientError("MIS_UNAVAILABLE", "Stored MIS session cookie is invalid")
            self.session.cookies.set(
                cookie["name"],
                cookie.get("value", ""),
                domain=cookie.get("domain"),
                path=cookie.get("path", "/"),
                secure=bool(cookie.get("secure", False)),
                expires=cookie.get("expires"),
            )
        self._login_html = state.get("login_html")
        self._auth._login_html = self._login_html
        self._auth._login_url = state.get("login_url")
        self._logged_in = bool(state.get("logged_in"))

    def fetch_login_page(self) -> MISLoginPageData:
        try:
            page: MISLoginPage = self._auth.fetch_login_page()
            self._login_html = self._auth._login_html
            return MISLoginPageData(
                captcha_image=page.captcha_image,
                captcha_image_url=page.captcha_image_url,
                expires_in_seconds=int(self.configuration.get("login_challenge_ttl_seconds", 600)),
                hidden_fields=page.hidden_fields,
                rsa_modulus=page.rsa_modulus,
                rsa_exponent=page.rsa_exponent,
            )
        except MISAuthError as error:
            raise MISClientError(error.code, str(error), 502) from error
        except requests.RequestException as error:
            code = "PAGE_NOT_FOUND" if (
                isinstance(error, requests.HTTPError)
                and error.response is not None
                and error.response.status_code == 404
            ) else "MIS_UNAVAILABLE"
            raise MISClientError(code, "MIS login page request failed", 404 if code == "PAGE_NOT_FOUND" else 502) from error

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
            raise MISClientError("PAGE_NOT_FOUND", f"MIS resource {resource!r} is not configured", 422)
        if not path.startswith("/") or path.startswith("//") or "://" in path:
            raise MISClientError("MIS_UNAVAILABLE", "MIS resource paths must be relative paths", 422)
        return path

    def login(self, credentials: dict[str, str]) -> MISAuthResult:
        try:
            result = self._auth.login(credentials, self._login_html)
        except requests.RequestException as error:
            raise MISClientError("MIS_UNAVAILABLE", "MIS authentication request failed") from error
        self._login_html = None
        if result.error_code in {"MIS_UNAVAILABLE", "PAGE_NOT_FOUND"}:
            status_code = 404 if result.error_code == "PAGE_NOT_FOUND" else 502
            raise MISClientError(
                result.error_code,
                result.message or "MIS authentication request failed",
                status_code,
            )
        self._logged_in = result.authenticated
        if not result.authenticated and result.requires:
            raise MISAuthenticationError(
                result.message or "MIS login needs additional input",
                result.error_code or "LOGIN_FAILED",
                result.requires,
            )
        if not result.authenticated:
            raise MISAuthenticationError(
                result.message or "MIS login was rejected",
                result.error_code or "LOGIN_FAILED",
            )
        return result

    def logout(self) -> None:
        path = self.configuration.get("logout_path")
        try:
            if self._logged_in and path:
                if not path.startswith("/") or path.startswith("//") or "://" in path:
                    raise MISClientError("MIS_UNAVAILABLE", "MIS logout path must be relative")
                logout_url = urljoin(self.base_url, path)
                if urlparse(logout_url).netloc != urlparse(self.base_url).netloc:
                    raise MISClientError("MIS_UNAVAILABLE", "MIS logout path must stay on the configured host")
                response = self.session.get(logout_url, timeout=self.timeout)
                response.raise_for_status()
        except MISClientError:
            raise
        except requests.RequestException as error:
            raise MISClientError("MIS_UNAVAILABLE", "MIS logout request failed") from error
        finally:
            self._logged_in = False
            self.session.close()

    def refresh_session(self, credentials: dict[str, str]) -> MISAuthResult:
        self.session.close()
        self.session = requests.Session()
        self._auth = MISAuth(self.base_url, self.session, self.configuration, self.password_encryptor)
        self._login_html = None
        self._logged_in = False
        return self.login(credentials)

    def is_logged_in(self) -> bool:
        if not self._logged_in:
            return False
        path = self.configuration.get("session_check_path")
        if not path:
            return True
        try:
            page = self.get_authenticated_page(path)
            return bool(page)
        except MISAuthenticationError:
            self._logged_in = False
            return False
        except MISClientError as error:
            if error.code == "SESSION_EXPIRED":
                self._logged_in = False
                return False
            raise

    @property
    def has_login_challenge(self) -> bool:
        return self._login_html is not None

    def get_authenticated_page(self, path: str) -> str:
        if not self._logged_in:
            raise MISAuthenticationError("MIS session is not authenticated", "SESSION_EXPIRED")
        if not path.startswith("/") or path.startswith("//") or "://" in path:
            raise MISClientError("MIS_UNAVAILABLE", "MIS page paths must be relative paths", 422)
        try:
            response = self.session.get(urljoin(self.base_url, path.lstrip("/")), timeout=self.timeout)
            response.raise_for_status()
            response_url = urlparse(response.url)
            base_url = urlparse(self.base_url)
            if (response_url.scheme, response_url.netloc) != (base_url.scheme, base_url.netloc):
                raise MISClientError("MIS_UNAVAILABLE", "MIS page redirected outside the configured host")
            login_markers = (
                "hdnrsamodulus",
                'name="username"',
                "name='username'",
            )
            lowered = response.text.casefold()
            if any(marker in lowered for marker in login_markers):
                self._logged_in = False
                raise MISAuthenticationError("MIS session has expired", "SESSION_EXPIRED", ["captcha"])
            self.last_source_page = path
            return response.text
        except MISAuthenticationError:
            raise
        except requests.HTTPError as error:
            status = error.response.status_code if error.response is not None else None
            if status == 404:
                raise MISClientError("PAGE_NOT_FOUND", "MIS page was not found", 404) from error
            if status in (401, 403):
                self._logged_in = False
                raise MISAuthenticationError("MIS session has expired", "SESSION_EXPIRED", ["captcha"]) from error
            raise MISClientError("MIS_UNAVAILABLE", "MIS page request failed") from error
        except requests.RequestException as error:
            raise MISClientError("MIS_UNAVAILABLE", "MIS page request failed") from error

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