from fastapi import APIRouter, Request

from app.core.api_response import ok
from app.core.logging_config import get_logger
from app.services.mock_data import get_mock_detection_frame, get_mock_zones

router = APIRouter()
logger = get_logger(__name__)


@router.get("/frame")
def mock_frame(request: Request) -> dict:
    """Return fake object detections for GUI development."""
    frame = get_mock_detection_frame()
    logger.info(
        "Mock frame returned",
        extra={"request_id": request.state.request_id, "frame_id": frame.get("frame_id")},
    )
    return ok(frame, request_id=request.state.request_id)


@router.get("/zones")
def mock_zones(request: Request) -> dict:
    """Return fake traffic zones for GUI development."""
    zones = get_mock_zones()
    logger.info(
        "Mock zones returned",
        extra={"request_id": request.state.request_id, "zone_count": len(zones)},
    )
    return ok({"zones": zones}, request_id=request.state.request_id)
