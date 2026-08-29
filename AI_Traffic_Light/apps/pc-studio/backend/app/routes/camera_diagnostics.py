from fastapi import APIRouter, Request

from app.core.api_response import ok
from app.core.logging_config import get_logger
from app.services.camera_diagnostics import camera_diagnostic_service

router = APIRouter()
logger = get_logger(__name__)


@router.post("/run")
def run_camera_diagnostics(request: Request) -> dict:
    """Run the one-click diagnostic against the currently selected saved ESP camera."""
    data = camera_diagnostic_service.run()
    logger.info(
        "Camera diagnostics returned",
        extra={
            "request_id": request.state.request_id,
            "run_id": data["run_id"],
            "source_id": data["source_id"],
            "diagnosis_code": data["diagnosis_code"],
        },
    )
    return ok(data, request_id=request.state.request_id)
