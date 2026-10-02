import asyncio
from datetime import date, datetime
from enum import Enum
import logging
import time
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.tools.base import BaseTool
from app.tools.exceptions import (
    ToolError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolOwnershipError,
    ToolValidationError,
)
from app.tools.schemas import ToolMetadata, ToolResponse
from app.services.audit_log_service import AuditLogService


logger = logging.getLogger(__name__)
TTool = TypeVar("TTool", bound=BaseTool)
_TOOL_TYPES: dict[str, type[BaseTool]] = {}
tool_registry: "ToolRegistry"


def register_tool(tool_type: type[TTool]) -> type[TTool]:
    if not getattr(tool_type, "name", None) or tool_type.name == "base":
        raise ValueError("Registered tools must define a name")
    if tool_type.name in _TOOL_TYPES:
        raise ValueError(f"Tool already registered: {tool_type.name}")
    _TOOL_TYPES[tool_type.name] = tool_type
    if _defaults_loaded:
        tool_registry.register_tool(tool_type())
    return tool_type


def _json_safe(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, BaseModel):
        return _json_safe(value.model_dump(mode="python"))
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(item) for item in value]
    table = getattr(value, "__table__", None)
    if table is not None:
        return {column.name: _json_safe(getattr(value, column.name)) for column in table.columns}
    return str(value)


class ToolRegistry:
    def __init__(self, tools: list[BaseTool] | None = None):
        self._tools: dict[str, BaseTool] = {}
        for tool in tools or []:
            self.register_tool(tool)

    def register_tool(self, tool: BaseTool) -> None:
        if not isinstance(tool, BaseTool):
            raise TypeError("Registered tools must derive from BaseTool")
        if not tool.name or tool.name == "base":
            raise ValueError("Registered tools must define a name")
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> BaseTool:
        self._ensure_default_tools()
        try:
            return self._tools[name]
        except KeyError as error:
            raise ToolNotFoundError(name) from error

    def list_tools(self) -> list[dict]:
        self._ensure_default_tools()
        metadata = []
        for tool in self._tools.values():
            schema = tool.input_model.model_json_schema()
            hidden_fields = {"db", "student_id", "principal_id"}
            for field in hidden_fields:
                schema.get("properties", {}).pop(field, None)
            schema.get("required", [])[:] = [field for field in schema.get("required", []) if field not in hidden_fields]
            metadata.append(ToolMetadata(
                name=tool.name,
                description=tool.description,
                input_schema=schema,
            ).model_dump())
        return metadata

    async def execute_tool_async(self, name: str, payload: dict | BaseModel) -> ToolResponse:
        self._ensure_default_tools()
        tool = self.get_tool(name)
        started = time.perf_counter()
        student_id = payload.get("student_id") if isinstance(payload, dict) else getattr(payload, "student_id", None)
        request_fields = sorted(payload.keys()) if isinstance(payload, dict) else sorted(payload.model_fields_set)
        try:
            request = tool.input_model.model_validate(payload)
        except ValidationError as error:
            logger.info("Tool validation failed: tool=%s student_id=%s", name, student_id)
            self._audit_tool(name, student_id, started, False, error, request_fields)
            raise ToolValidationError(name, str(error)) from error

        principal_id = getattr(request, "principal_id", None)
        if principal_id is not None and student_id is not None and principal_id != student_id:
            error = ToolOwnershipError()
            self._audit_tool(name, student_id, started, False, error, request_fields)
            raise error
        try:
            data = await tool.execute(request)
        except ToolError as error:
            logger.info("Tool rejected request: tool=%s student_id=%s code=%s", name, student_id, getattr(error, "code", "tool_error"))
            self._audit_tool(name, student_id, started, False, error, request_fields)
            raise
        except Exception as error:
            logger.exception("Tool execution failed: tool=%s student_id=%s", name, student_id)
            self._audit_tool(name, student_id, started, False, error, request_fields)
            raise ToolExecutionError(name) from error
        logger.info(
            "Tool executed: tool=%s student_id=%s duration_seconds=%.4f",
            name,
            student_id,
            time.perf_counter() - started,
        )
        self._audit_tool(name, student_id, started, True, None, request_fields)
        response = ToolResponse(tool=name, data=_json_safe(data))
        response._raw_data = data
        return response

    @staticmethod
    def _audit_tool(name, student_id, started, success, error, request_fields) -> None:
        AuditLogService.record_event_isolated(
            event_type="TOOL_EXECUTION",
            resource_type="tool",
            resource_id=name,
            action="execute",
            student_id=student_id,
            metadata_json={
                "tool_name": name,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                "success": success,
                "error_type": type(error).__name__ if error else None,
                "error_message": str(error)[:500] if error else None,
                "request_fields": request_fields,
            },
        )

    def execute_tool(self, name: str, payload: dict | BaseModel) -> ToolResponse:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.execute_tool_async(name, payload))
        raise ToolExecutionError(
            name,
            "Synchronous tool execution is unavailable inside an event loop; await execute_tool_async.",
        )

    def _ensure_default_tools(self) -> None:
        if self is globals().get("tool_registry") and not globals().get("_defaults_loaded", False):
            get_tool_registry()


tool_registry = ToolRegistry()
_defaults_loaded = False


def get_tool_registry() -> ToolRegistry:
    global _defaults_loaded
    if not _defaults_loaded:
        from app.tools.academic import tools as _academic_tools  # noqa: F401
        from app.tools.calendar import tools as _calendar_tools  # noqa: F401
        from app.tools.dashboard import tools as _dashboard_tools  # noqa: F401
        from app.tools.learning import tools as _learning_tools  # noqa: F401
        from app.tools.mis import tools as _mis_tools  # noqa: F401
        from app.tools.productivity import tools as _productivity_tools  # noqa: F401
        from app.tools.study import tools as _study_tools  # noqa: F401

        for tool_type in _TOOL_TYPES.values():
            tool_registry.register_tool(tool_type())
        _defaults_loaded = True
    return tool_registry