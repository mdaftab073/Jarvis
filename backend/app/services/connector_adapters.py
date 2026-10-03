from abc import ABC, abstractmethod
from collections.abc import Callable


class ConnectorConfigurationError(ValueError):
    pass


class ConnectorAdapter(ABC):
    @abstractmethod
    def fetch(self, credentials: dict) -> dict:
        raise NotImplementedError


ConnectorAdapterFactory = Callable[[str, dict | None], ConnectorAdapter]
_ADAPTER_FACTORIES: dict[str, ConnectorAdapterFactory] = {}


def register_connector_adapter(
    connector_type: str,
    factory: ConnectorAdapterFactory,
) -> None:
    if not connector_type.strip():
        raise ValueError("Connector type must not be empty")
    if connector_type in _ADAPTER_FACTORIES:
        raise ValueError(f"Connector adapter is already registered: {connector_type}")
    _ADAPTER_FACTORIES[connector_type] = factory


def has_connector_adapter(connector_type: str) -> bool:
    return connector_type in _ADAPTER_FACTORIES


def create_connector_adapter(
    connector_type: str,
    endpoint_url: str,
    configuration: dict | None = None,
) -> ConnectorAdapter:
    try:
        factory = _ADAPTER_FACTORIES[connector_type]
    except KeyError as error:
        raise ConnectorConfigurationError(
            f"Unsupported connector type: {connector_type}"
        ) from error
    return factory(endpoint_url, configuration)
