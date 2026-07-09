from fastapi import APIRouter, Request

from app.core.api_response import ok
from app.core.logging_config import get_logger
from app.services.mock_data import get_mock_zones

router = APIRouter()
logger = get_logger(__name__)


@router.get("/active")
def active_zones(request: Request) -> dict:
    """Return active placeholder traffic zones."""
    zones = get_mock_zones()
    logger.info("Zone template returned", extra={"request_id": request.state.request_id, "zone_count": len(zones)})
    return ok({"zones": zones, "editable": False, "status": "template_only"}, request_id=request.state.request_id)


@router.get("/functions")
def zone_functions(request: Request) -> dict:
    """Return planned zone-editor functions."""
    data = {
        "functions": [
            "create_polygon_zone",
            "edit_polygon_points",
            "assign_zone_type",
            "validate_zone_config",
            "save_zone_file",
            "load_zone_file",
            "count_detections_inside_zones",
        ]
    }
    logger.info("Zone function template returned", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)
