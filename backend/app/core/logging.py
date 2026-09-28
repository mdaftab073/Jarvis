import datetime
import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Optional


class JSONFormatter(logging.Formatter):
    """
    Formats log records as single-line JSON objects with standard fields.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include request_id if present
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id

        # Include structured extra fields if provided
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_obj.update(record.extra_data)

        # Include exception tracebacks if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj, default=str)


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    log_filename: str = "jarvis.log",
    enable_json: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
) -> logging.Logger:
    """
    Configures root and application loggers with console output and rotating file output.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicates on re-initialization
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    # Choose formatter
    if enable_json:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
        )

    # 1. Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 2. Rotating File Handler
    try:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_path / log_filename,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(JSONFormatter())  # Always JSON in files
        root_logger.addHandler(file_handler)
    except Exception as exc:
        root_logger.warning("Could not setup file logging: %s", exc)

    logger = logging.getLogger("jarvis")
    logger.setLevel(level)
    return logger


# Convenience logging helpers
def log_api_request(
    logger: logging.Logger,
    request_id: str,
    method: str,
    endpoint: str,
    status_code: int,
    duration_ms: float,
    client_ip: Optional[str] = None,
) -> None:
    logger.info(
        "API Request completed",
        extra={
            "request_id": request_id,
            "extra_data": {
                "event": "api_request",
                "method": method,
                "endpoint": endpoint,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "client_ip": client_ip,
            },
        },
    )


def log_agent_execution(
    logger: logging.Logger,
    agent_name: str,
    goal: str,
    duration_ms: float,
    success: bool,
    error: Optional[str] = None,
    request_id: Optional[str] = None,
) -> None:
    level = logging.INFO if success else logging.ERROR
    logger.log(
        level,
        f"Agent execution {agent_name} {'succeeded' if success else 'failed'}",
        extra={
            "request_id": request_id,
            "extra_data": {
                "event": "agent_execution",
                "agent_name": agent_name,
                "goal": goal,
                "duration_ms": duration_ms,
                "success": success,
                "error": error,
            },
        },
    )


def log_retrieval_query(
    logger: logging.Logger,
    query: str,
    subject_id: Optional[int],
    hybrid_count: int,
    vector_hits: int,
    keyword_hits: int,
    duration_ms: float,
    request_id: Optional[str] = None,
) -> None:
    logger.info(
        "Retrieval query executed",
        extra={
            "request_id": request_id,
            "extra_data": {
                "event": "retrieval_query",
                "query": query,
                "subject_id": subject_id,
                "hybrid_count": hybrid_count,
                "vector_hits": vector_hits,
                "keyword_hits": keyword_hits,
                "duration_ms": duration_ms,
            },
        },
    )


def log_database_failure(
    logger: logging.Logger,
    operation: str,
    error: Exception,
    request_id: Optional[str] = None,
) -> None:
    logger.error(
        f"Database operation failed: {operation}",
        exc_info=error,
        extra={
            "request_id": request_id,
            "extra_data": {
                "event": "database_failure",
                "operation": operation,
                "error": str(error),
            },
        },
    )


def log_validation_failure(
    logger: logging.Logger,
    context: str,
    error: str,
    request_id: Optional[str] = None,
) -> None:
    logger.warning(
        f"Validation failure in {context}: {error}",
        extra={
            "request_id": request_id,
            "extra_data": {
                "event": "validation_failure",
                "context": context,
                "error": error,
            },
        },
    )
