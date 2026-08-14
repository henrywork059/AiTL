from fastapi import APIRouter, Request

from app.core.api_response import ok
from app.core.logging_config import get_logger

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
            "version": "0_1_3",
            "mode": "manual_labeling_test_ready",
            "safe_mode": True,
            "message": "Backend is ready for capture, manual bounding-box labeling, managed YOLO dataset builds, and optional training tests.",
        },
        request_id=request.state.request_id,
    )
