"""Request ID and access logging middleware."""

from contextvars import ContextVar
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Context variable holding the current request's correlation ID.
# Accessible from anywhere in the call stack via request_id_ctx.get().
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")

logger = logging.getLogger("app.access")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every inbound request.

    - If the caller sends an X-Request-ID header, reuse it (for distributed
      tracing when an upstream service already assigned an ID).
    - Otherwise generate a new UUID4.
    - Store the ID in a contextvar so the structured logger can include it
      automatically in every log line within this request's scope.
    - Echo the ID back in the X-Request-ID response header so the caller
      can correlate their request with our logs.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        rid = request.headers.get("x-request-id", str(uuid.uuid4()))
        request_id_ctx.set(rid)
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Log every request/response with method, path, status, and latency.

    Replaces uvicorn's default access log with a structured JSON version
    that includes the request ID (set by RequestIDMiddleware, which must
    run before this middleware).
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
        logger.info(
            "%s %s %d %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response
