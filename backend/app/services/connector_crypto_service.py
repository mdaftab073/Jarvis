import json

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class ConnectorCredentialError(ValueError):
    pass


def _fernet(key: str | None = None) -> Fernet:
    configured_key = key or settings.CONNECTOR_ENCRYPTION_KEY
    if not configured_key:
        raise ConnectorCredentialError("CONNECTOR_ENCRYPTION_KEY is required")
    try:
        return Fernet(configured_key.encode("ascii"))
    except (ValueError, TypeError, UnicodeEncodeError) as error:
        raise ConnectorCredentialError("CONNECTOR_ENCRYPTION_KEY must be a valid Fernet key") from error


def encrypt_credentials(credentials: dict, key: str | None = None) -> str:
    if not isinstance(credentials, dict):
        raise ConnectorCredentialError("Connector credentials must be a JSON object")
    payload = json.dumps(credentials, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _fernet(key).encrypt(payload).decode("ascii")


def decrypt_credentials(ciphertext: str, key: str | None = None) -> dict:
    try:
        payload = _fernet(key).decrypt(ciphertext.encode("ascii"))
        credentials = json.loads(payload)
    except InvalidToken as error:
        raise ConnectorCredentialError("Connector credentials could not be decrypted") from error
    except (UnicodeEncodeError, json.JSONDecodeError) as error:
        raise ConnectorCredentialError("Connector credentials are invalid") from error
    if not isinstance(credentials, dict):
        raise ConnectorCredentialError("Connector credentials must be a JSON object")
    return credentials
