import json
from urllib.parse import urlparse

from app.core.config import settings
from app.services.mis.client import MISClientError


def get_mis_site_configuration() -> tuple[str, dict]:
    base_url = settings.SVNIT_MIS_BASE_URL.strip()
    parsed_url = urlparse(base_url)
    if not base_url:
        raise MISClientError(
            "MIS_UNAVAILABLE",
            "SVNIT_MIS_BASE_URL is not set; configure the HTTPS MIS host, "
            "for example https://mis.svnit.ac.in",
            422,
        )
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise MISClientError(
            "MIS_UNAVAILABLE",
            "SVNIT_MIS_BASE_URL must use HTTPS and include a host, "
            "for example https://mis.svnit.ac.in",
            422,
        )
    if parsed_url.username or parsed_url.password:
        raise MISClientError(
            "MIS_UNAVAILABLE",
            "SVNIT_MIS_BASE_URL must not include a username or password",
            422,
        )
    if parsed_url.path not in {"", "/"} or parsed_url.query or parsed_url.fragment:
        raise MISClientError(
            "MIS_UNAVAILABLE",
            "SVNIT_MIS_BASE_URL must be the HTTPS host origin only; "
            "configure the login page path in SVNIT_MIS_CONFIGURATION_JSON",
            422,
        )

    try:
        configuration = json.loads(settings.SVNIT_MIS_CONFIGURATION_JSON)
    except (TypeError, json.JSONDecodeError) as error:
        raise MISClientError(
            "MIS_UNAVAILABLE",
            "SVNIT MIS configuration must be valid JSON",
            422,
        ) from error
    if not isinstance(configuration, dict):
        raise MISClientError(
            "MIS_UNAVAILABLE",
            "SVNIT MIS configuration must be a JSON object",
            422,
        )
    return base_url, configuration
