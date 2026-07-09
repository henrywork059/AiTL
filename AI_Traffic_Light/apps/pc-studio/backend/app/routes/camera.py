from fastapi import APIRouter, Request

from app.core.api_response import ok
from app.core.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/sources")
def list_camera_sources(request: Request) -> dict:
    """Return planned camera source slots.

    Real webcam/ESP-CAM discovery will be added in a later patch.
    """
    data = {
        "sources": [
            {"id": "webcam_0", "label": "Local webcam", "type": "webcam", "status": "placeholder"},
            {"id": "esp_cam_01", "label": "ESP-CAM 01", "type": "mjpeg", "status": "placeholder"},
            {"id": "video_file", "label": "Traffic video file", "type": "file", "status": "placeholder"},
        ]
    }
    logger.info("Camera source template returned", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)


@router.get("/status")
def camera_status(request: Request) -> dict:
    """Return placeholder camera runtime status."""
    data = {
        "active_source_id": None,
        "streaming": False,
        "fps": 0,
        "resolution": None,
        "status": "template_only",
    }
    logger.info("Camera status template returned", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)
