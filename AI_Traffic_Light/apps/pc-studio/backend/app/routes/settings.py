from fastapi import APIRouter, Request

from app.core.api_response import ok
from app.core.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/summary")
def settings_summary(request: Request) -> dict:
    """Return placeholder settings groups."""
    data = {
        "groups": [
            "camera",
            "inference",
            "traffic_logic",
            "dataset_paths",
            "viewer",
            "debug_logging",
        ],
        "status": "template_only",
    }
    logger.info("Settings template returned", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)
