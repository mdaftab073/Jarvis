import logging
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import log_api_request
from app.core.metrics import metrics

logger = logging.getLogger("jarvis.request")


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that assigns a unique request_id to each incoming HTTP request,
    tracks duration, updates application metrics, logs the request, and appends
    the X-Request-ID header to the HTTP response.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # 1. Determine or generate request_id
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        request.state.request_id = request_id
        start_time = time.time()

        # 2. Extract client IP and path
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path
        method = request.method

        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as exc:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            metrics.record_request(method, path, 500, duration_ms)
            log_api_request(
                logger=logger,
                request_id=request_id,
                method=method,
                endpoint=path,
                status_code=500,
                duration_ms=duration_ms,
                client_ip=client_ip,
            )
            raise exc

        # 3. Complete tracking
        duration_ms = round((time.time() - start_time) * 1000, 2)
        metrics.record_request(method, path, status_code, duration_ms)
        log_api_request(
            logger=logger,
            request_id=request_id,
            method=method,
            endpoint=path,
            status_code=status_code,
            duration_ms=duration_ms,
            client_ip=client_ip,
        )

        # 4. Attach request_id to response header
        response.headers["X-Request-ID"] = request_id
        return response
