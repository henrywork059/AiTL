from fastapi import APIRouter, Request

from app.core.api_response import ok
from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.core.logging_config import get_logger
from app.services.smoke_test import get_smoke_status

router = APIRouter()
logger = get_logger(__name__)


@router.get("/status")
def smoke_status(request: Request) -> dict:
    """Return a test-ready status report for the 0_1_2 app."""
    data = get_smoke_status()
    logger.info("Smoke status returned", extra={"request_id": request.state.request_id, "version": data["version"]})
    return ok(data, request_id=request.state.request_id)


@router.get("/error-demo")
def smoke_error_demo(request: Request) -> dict:
    """Deliberately raise an AppError to verify error-code handling."""
    logger.warning("Smoke error demo requested", extra={"request_id": request.state.request_id})
    raise AppError(
        ErrorCode.TEMPLATE_ROUTE_NOT_IMPLEMENTED,
        "This is a controlled error-demo endpoint for testing the API envelope.",
        status_code=501,
        details={"version": "0_1_2", "safe_to_ignore": True},
    )
