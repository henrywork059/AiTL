from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.api_response import fail
from app.core.error_codes import ErrorCode, default_message
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Expected project error with a stable error code."""

    def __init__(
        self,
        code: ErrorCode,
        message: str | None = None,
        *,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message or default_message(code)
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Convert expected AppError exceptions to standard API error responses."""
    request_id = getattr(request.state, "request_id", None)
    logger.warning(
        "Handled project error",
        extra={
            "request_id": request_id,
            "error_code": exc.code.value,
            "path": request.url.path,
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=fail(
            code=exc.code,
            message=exc.message,
            request_id=request_id,
            details=exc.details,
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Convert unexpected exceptions to safe API error responses."""
    request_id = getattr(request.state, "request_id", None)
    logger.exception(
        "Unhandled backend exception",
        extra={
            "request_id": request_id,
            "error_code": ErrorCode.UNKNOWN_ERROR.value,
            "path": request.url.path,
        },
    )
    return JSONResponse(
        status_code=500,
        content=fail(
            code=ErrorCode.UNKNOWN_ERROR,
            message=default_message(ErrorCode.UNKNOWN_ERROR),
            request_id=request_id,
        ),
    )


async def request_validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return FastAPI/Pydantic request validation failures in the project envelope."""
    request_id = getattr(request.state, "request_id", None)
    details = {
        "fields": [
            {
                "location": [str(part) for part in error.get("loc", ())],
                "message": error.get("msg", "Invalid value"),
                "type": error.get("type", "validation_error"),
            }
            for error in exc.errors()
        ]
    }
    logger.warning(
        "Request validation failed",
        extra={
            "request_id": request_id,
            "error_code": ErrorCode.INVALID_REQUEST.value,
            "path": request.url.path,
        },
    )
    return JSONResponse(
        status_code=422,
        content=fail(
            code=ErrorCode.INVALID_REQUEST,
            message=default_message(ErrorCode.INVALID_REQUEST),
            request_id=request_id,
            details=details,
        ),
    )
