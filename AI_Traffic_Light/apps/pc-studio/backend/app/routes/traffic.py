from fastapi import APIRouter, Request

from app.core.api_response import ok
from app.core.logging_config import get_logger
from app.services.traffic_logic import get_live_traffic_state

router = APIRouter()
logger = get_logger(__name__)


@router.get("/state")
def traffic_state(request: Request) -> dict:
    """Return the current live-detection-based traffic-light simulation recommendation."""
    state = get_live_traffic_state()
    logger.info(
        "Traffic simulation state returned",
        extra={
            "request_id": request.state.request_id,
            "phase": state.get("phase"),
            "decision": state.get("decision"),
            "frame_number": state.get("evaluated_frame_number"),
        },
    )
    return ok(state, request_id=request.state.request_id)
