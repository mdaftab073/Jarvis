import inspect
import logging
from typing import Any, Generic, TypeVar

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute, request_response
from fastapi.utils import create_model_field
from pydantic import BaseModel
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)
T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


def error_response(
    status_code: int,
    code: str,
    message: str,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {"code": code, "message": message},
        },
        headers=headers,
    )


def _exception_code(status_code: int, detail: Any) -> tuple[str, str]:
    if isinstance(detail, dict):
        code = detail.get("code") or detail.get("error")
        message = detail.get("message")
        if code and message:
            return str(code), str(message)
    code_by_status = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        413: "payload_too_large",
        422: "validation_error",
        429: "rate_limited",
    }
    message = detail if isinstance(detail, str) else "Request could not be completed."
    return code_by_status.get(status_code, f"http_{status_code}"), message


async def handle_http_exception(
    request: Request, error: StarletteHTTPException
) -> JSONResponse:
    code, message = _exception_code(error.status_code, error.detail)
    return error_response(error.status_code, code, message, error.headers)


async def handle_validation_error(
    request: Request, error: RequestValidationError
) -> JSONResponse:
    return error_response(422, "validation_error", "Request validation failed.")


async def handle_rate_limit_error(
    request: Request, error: RateLimitExceeded
) -> JSONResponse:
    return error_response(429, "rate_limited", "Too many requests.")


async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
    logger.exception("Unhandled API error", exc_info=error)
    return error_response(500, "internal_server_error", "An unexpected error occurred.")


def _response_endpoint(endpoint: Any, encode_result: bool) -> Any:
    def envelope(result: Any, kwargs: dict[str, Any]) -> Any:
        response = kwargs.get("response")
        if getattr(response, "status_code", 200) >= 400:
            detail = jsonable_encoder(result)
            status = response.status_code
            message = "Request could not be completed."
            if isinstance(detail, dict) and detail.get("status"):
                checks = ", ".join(
                    f"{key}={value}"
                    for key, value in detail.items()
                    if key != "status"
                )
                message = f"{detail['status']}: {checks}" if checks else str(detail["status"])
            return error_response(status, f"http_{status}", message)
        return SuccessResponse(data=jsonable_encoder(result) if encode_result else result)

    if inspect.iscoroutinefunction(endpoint):
        async def wrapped_endpoint(*args: Any, **kwargs: Any):
            result = await endpoint(*args, **kwargs)
            return envelope(result, kwargs)
    else:
        def wrapped_endpoint(*args: Any, **kwargs: Any):
            result = endpoint(*args, **kwargs)
            return envelope(result, kwargs)

    wrapped_endpoint.__signature__ = inspect.signature(endpoint)
    wrapped_endpoint.__name__ = endpoint.__name__
    wrapped_endpoint.__module__ = endpoint.__module__
    return wrapped_endpoint


def envelope_routes(routes: list[Any]) -> None:
    pending = list(routes)
    expanded: set[int] = set()
    api_routes: list[APIRoute] = []
    while pending:
        route = pending.pop()
        if isinstance(route, APIRoute):
            api_routes.append(route)
            continue
        router = getattr(route, "original_router", None)
        if router is not None and id(router) not in expanded:
            expanded.add(id(router))
            pending.extend(router.routes)

    for route in api_routes:
        if not isinstance(route, APIRoute) or getattr(route, "_response_enveloped", False):
            continue

        original_model = route.response_model
        data_model = original_model if original_model is not None else Any
        envelope_model = SuccessResponse[data_model]
        original_endpoint = route.dependant.call
        wrapped_endpoint = _response_endpoint(original_endpoint, original_model is None)

        route.dependant.call = wrapped_endpoint
        route.endpoint = wrapped_endpoint
        route.response_model = envelope_model
        route.response_field = create_model_field(
            name=f"Response_{route.unique_id}",
            type_=envelope_model,
            mode="serialization",
        )
        route.app = request_response(route.get_route_handler())
        route.responses = {
            **route.responses,
            **{
                status_code: {
                    "model": ErrorResponse,
                    "description": description,
                }
                for status_code, description in {
                    400: "Bad request",
                    401: "Authentication required",
                    403: "Forbidden",
                    404: "Resource not found",
                    409: "Conflict",
                    413: "Payload too large",
                    422: "Request validation failed",
                    429: "Rate limit exceeded",
                    500: "Internal server error",
                    503: "Service unavailable",
                }.items()
            },
        }
        route._response_enveloped = True
