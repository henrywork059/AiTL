from fastapi import APIRouter, Request

from app.core.api_response import ok
from app.core.logging_config import get_logger
from app.services.traffic_logic import get_mock_traffic_state

router = APIRouter()
logger = get_logger(__name__)


@router.get("/state")
def traffic_state(request: Request) -> dict:
    """Return mock traffic-light state.

    Replace this later with real zone-counting and rule-based decisions.
    """
    state = get_mock_traffic_state()
    logger.info(
        "Traffic state returned",
        extra={
            "request_id": request.state.request_id,
            "phase": state.get("phase"),
            "decision": state.get("decision"),
        },
    )
    return ok(state, request_id=request.state.request_id)
