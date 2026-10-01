import json
from abc import ABC, abstractmethod
from urllib.parse import urlparse

import httpx

from app.core.config import settings


class ConnectorConfigurationError(ValueError):
    pass


class MISConnector(ABC):
    connector_type: str

    def __init__(self, endpoint_url: str, resources: dict[str, str] | None = None):
        parsed = urlparse(endpoint_url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise ConnectorConfigurationError("Connector endpoint must be a trusted HTTPS URL")
        self.endpoint_url = endpoint_url.rstrip("/")
        self.resources = resources or {}

    @abstractmethod
    def fetch(self, credentials: dict) -> dict:
        raise NotImplementedError

    def normalize(self, payload: dict) -> dict:
        return normalize_mis_payload(payload)


class SVNITMISConnector(MISConnector):
    connector_type = "svnit_mis"

    def fetch(self, credentials: dict) -> dict:
        token = credentials.get("token")
        username = credentials.get("username")
        password = credentials.get("password")
        if not token and not (username and password):
            raise ConnectorConfigurationError("MIS credentials require token or username/password")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        auth = (username, password) if username and password else None
        result = {}
        paths = self.resources or {
            "profile": "/profile",
            "subjects": "/subjects",
            "attendance": "/attendance",
            "grades": "/grades",
        }
        timeout = max(1, settings.CONNECTOR_HTTP_TIMEOUT_SECONDS)
        with httpx.Client(
            base_url=self.endpoint_url,
            headers=headers,
            auth=auth,
            timeout=timeout,
            follow_redirects=False,
        ) as client:
            for name, path in paths.items():
                if name not in {"profile", "subjects", "attendance", "grades"}:
                    continue
                if not path.startswith("/") or path.startswith("//") or "://" in path:
                    raise ConnectorConfigurationError("MIS resource paths must be relative paths")
                response = client.get(path)
                response.raise_for_status()
                result[name] = response.json()
        return self.normalize(result)


def _unwrap_rows(payload):
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("items", "results", "data", "records"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
        return [payload]
    raise ConnectorConfigurationError("MIS resource response must be a JSON object or array")


def normalize_mis_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ConnectorConfigurationError("MIS response must be a JSON object")
    profile_payload = payload.get("profile") or {}
    if isinstance(profile_payload, list):
        profile_payload = profile_payload[0] if profile_payload else {}
    if not isinstance(profile_payload, dict):
        raise ConnectorConfigurationError("MIS profile response must be an object")
    profile = {
        "enrollment_number": profile_payload.get("enrollment_number") or profile_payload.get("roll_number"),
        "branch": profile_payload.get("branch"),
        "department": profile_payload.get("department"),
        "semester": profile_payload.get("semester"),
        "section": profile_payload.get("section"),
        "batch_year": profile_payload.get("batch_year"),
        "current_cpi": profile_payload.get("current_cpi", profile_payload.get("cpi")),
        "current_spi": profile_payload.get("current_spi", profile_payload.get("spi")),
        "earned_credits": profile_payload.get("earned_credits"),
        "total_credits": profile_payload.get("total_credits"),
        "academic_status": profile_payload.get("academic_status", "ACTIVE"),
    }
    subjects = []
    for row in _unwrap_rows(payload.get("subjects")):
        if not isinstance(row, dict):
            raise ConnectorConfigurationError("MIS subject records must be objects")
        name = row.get("name") or row.get("subject_name") or row.get("title")
        if not name:
            continue
        subjects.append({
            "external_id": str(row.get("id") or row.get("code") or name),
            "code": row.get("code"),
            "name": str(name).strip(),
            "credits": row.get("credits"),
        })
    attendances = []
    for row in _unwrap_rows(payload.get("attendance")):
        if not isinstance(row, dict):
            raise ConnectorConfigurationError("MIS attendance records must be objects")
        attendances.append({
            "subject_external_id": str(row.get("subject_id") or row.get("subject_code") or row.get("subject_name") or ""),
            "subject_name": row.get("subject_name"),
            "attended_classes": int(row.get("attended_classes", row.get("attended", 0))),
            "total_classes": int(row.get("total_classes", row.get("total", 0))),
        })
    grades = []
    for row in _unwrap_rows(payload.get("grades")):
        if not isinstance(row, dict):
            raise ConnectorConfigurationError("MIS grade records must be objects")
        grades.append({
            "subject_external_id": str(row.get("subject_id") or row.get("subject_code") or row.get("subject_name") or ""),
            "subject_name": row.get("subject_name"),
            "semester": int(row["semester"]) if row.get("semester") is not None else None,
            "credits": float(row["credits"]) if row.get("credits") is not None else None,
            "grade": row.get("grade") or row.get("grade_letter"),
            "grade_points": float(row["grade_points"]) if row.get("grade_points") is not None else None,
            "obtained_marks": float(row["obtained_marks"]) if row.get("obtained_marks") is not None else None,
            "max_marks": float(row.get("max_marks", 100)),
        })
    return {"profile": profile, "subjects": subjects, "attendance": attendances, "grades": grades}


def connector_configuration(connector_type: str) -> tuple[str, dict[str, str]]:
    try:
        entries = json.loads(settings.CONNECTOR_ENDPOINTS_JSON)
        config = entries[connector_type]
        endpoint = config["base_url"]
        resources = config.get("resources", {})
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise ConnectorConfigurationError(f"Connector {connector_type!r} is not configured") from error
    if not isinstance(resources, dict) or any(not isinstance(path, str) for path in resources.values()):
        raise ConnectorConfigurationError("Connector resource paths must be a string map")
    return endpoint, resources


def create_connector_adapter(connector_type: str, endpoint_url: str, configuration: dict | None = None) -> MISConnector:
    if connector_type == SVNITMISConnector.connector_type:
        resources = (configuration or {}).get("resources")
        return SVNITMISConnector(endpoint_url, resources)
    raise ConnectorConfigurationError(f"Unsupported connector type: {connector_type}")
