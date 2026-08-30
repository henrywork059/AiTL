from fastapi import APIRouter, Request

from app.core.api_response import ok
from app.core.logging_config import get_logger
from app.services.camera_diagnostic_dispatch import camera_diagnostic_dispatch_service

router = APIRouter()
logger = get_logger(__name__)


@router.post("/run")
def run_camera_diagnostics(request: Request) -> dict:
    """Run adaptive one-click diagnostics against the selected ESP camera.

    Normal AiTL firmware uses the established production diagnostic pipeline.
    R5 transport-benchmark firmware automatically runs the full transport matrix
    and maps its evidence into the same Camera Diagnostics report surface.
    """
    data = camera_diagnostic_dispatch_service.run()
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


@router.get("/progress")
def camera_diagnostic_progress(request: Request) -> dict:
    """Return live phase/test progress for the active Camera Diagnostics run."""
    return ok(camera_diagnostic_dispatch_service.progress(), request_id=request.state.request_id)
