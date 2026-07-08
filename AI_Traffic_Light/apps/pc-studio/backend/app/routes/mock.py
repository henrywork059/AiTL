from fastapi import APIRouter

from app.services.mock_data import get_mock_detection_frame, get_mock_zones

router = APIRouter()


@router.get("/frame")
def mock_frame() -> dict:
    """Return fake object detections for GUI development."""
    return get_mock_detection_frame()


@router.get("/zones")
def mock_zones() -> dict:
    """Return fake traffic zones for GUI development."""
    return {"zones": get_mock_zones()}
