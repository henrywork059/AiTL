from fastapi import APIRouter, Request

from app.core.api_response import ok
from app.core.logging_config import get_logger
from app.core.project_version import PROJECT_MODE, PROJECT_VERSION

router = APIRouter()
logger = get_logger(__name__)


@router.get("/health")
def health(request: Request) -> dict:
    """Return backend health and version status."""
    logger.info("Health check requested", extra={"request_id": request.state.request_id})
    return ok(
        {
            "status": "ok",
            "app": "pc-studio-backend",
            "version": PROJECT_VERSION,
            "mode": PROJECT_MODE,
            "safe_mode": True,
            "message": (
                "Backend is ready for camera/simulation, camera-aligned persistent zones, Live AI zone/signal overlays, "
                "capture deletion, capture/label/train/model workflows, convergence monitoring, settings, and logs."
            ),
        },
        request_id=request.state.request_id,
    )
