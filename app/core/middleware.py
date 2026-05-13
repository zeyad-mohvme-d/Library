"""Request/response logging middleware."""
from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import logger


class RequestLogMiddleware(BaseHTTPMiddleware):
    """Log every incoming request with method, path, status, latency."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        start = time.perf_counter()

        logger.info(
            "REQ  id={} {} {} client={}",
            request_id,
            request.method,
            request.url.path,
            request.client.host if request.client else "-",
        )

        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "RESP id={} {} {} -> 500 ({:.2f}ms)",
                request_id,
                request.method,
                request.url.path,
                elapsed_ms,
            )
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["x-request-id"] = request_id
        response.headers["x-process-time-ms"] = f"{elapsed_ms:.2f}"

        log_fn = logger.info if response.status_code < 400 else logger.warning
        log_fn(
            "RESP id={} {} {} -> {} ({:.2f}ms)",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response
