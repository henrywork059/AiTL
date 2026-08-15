from fastapi import APIRouter, Request

from app.core.api_response import ok
from app.core.logging_config import get_logger
from app.models import SaveZonesRequest
from app.services.zones import zone_service

router = APIRouter()
logger = get_logger(__name__)


@router.get("/active")
def active_zones(request: Request) -> dict:
    """Return the persisted editable prototype traffic zones."""
    data = zone_service.status()
    logger.info("Active zones returned", extra={"request_id": request.state.request_id, "zone_count": len(data["zones"])})
    return ok(data, request_id=request.state.request_id)


@router.put("/active")
def save_active_zones(payload: SaveZonesRequest, request: Request) -> dict:
    """Validate and persist the complete active zone set."""
    data = zone_service.save([zone.model_dump() for zone in payload.zones])
    logger.info("Active zones saved", extra={"request_id": request.state.request_id, "zone_count": len(data["zones"])})
    return ok(data, request_id=request.state.request_id)


@router.post("/reset")
def reset_active_zones(request: Request) -> dict:
    """Restore the built-in reference zones used by the V016/V017 simulation."""
    data = zone_service.reset_defaults()
    logger.info("Active zones reset", extra={"request_id": request.state.request_id, "zone_count": len(data["zones"])})
    return ok(data, request_id=request.state.request_id)


@router.get("/functions")
def zone_functions(request: Request) -> dict:
    data = {
        "functions": [
            "create_polygon_zone",
            "edit_polygon_points",
            "assign_zone_type",
            "validate_zone_config",
            "save_zone_file",
            "load_zone_file",
            "reset_reference_zones",
            "count_live_detections_inside_zones",
        ]
    }
    logger.info("Zone functions returned", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)
