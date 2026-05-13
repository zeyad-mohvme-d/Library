"""Centralised application-level exception classes & handlers."""
from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import logger


class AppException(Exception):
    """Base application exception with HTTP status code and message."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "Application error"

    def __init__(self, detail: str | None = None, status_code: int | None = None):
        if detail is not None:
            self.detail = detail
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.detail)


class NotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Resource not found"


class ConflictError(AppException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Resource conflict"


class UnauthorizedError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Not authenticated"


class ForbiddenError(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "Insufficient permissions"


class BusinessRuleError(AppException):
    """Raised when a business rule is violated (e.g. borrow limit exceeded)."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail = "Business rule violation"


def _payload(detail, code):
    return {"detail": detail, "status_code": code}


def register_exception_handlers(app: FastAPI) -> None:
    """Wire FastAPI to our application exception handlers."""

    @app.exception_handler(AppException)
    async def _app_exc(request: Request, exc: AppException):
        logger.warning(
            "AppException at {} {}: {}", request.method, request.url.path, exc.detail
        )
        return JSONResponse(
            status_code=exc.status_code, content=_payload(exc.detail, exc.status_code)
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exc(request: Request, exc: StarletteHTTPException):
        logger.info(
            "HTTPException {} at {} {}: {}",
            exc.status_code,
            request.method,
            request.url.path,
            exc.detail,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(exc.detail, exc.status_code),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        logger.info(
            "Validation error at {} {}: {}",
            request.method,
            request.url.path,
            exc.errors(),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Validation error",
                "status_code": 422,
                "errors": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):  # pragma: no cover
        logger.exception(
            "Unhandled exception at {} {}", request.method, request.url.path
        )
        return JSONResponse(
            status_code=500,
            content=_payload("Internal server error", 500),
        )
