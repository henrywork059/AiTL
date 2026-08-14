from fastapi import APIRouter, Request

from app.core.api_response import ok
from app.core.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/recent")
def recent_logs(request: Request) -> dict:
    """Return placeholder recent logs for the GUI log page."""
    data = {
        "logs": [
            {
                "timestamp": "mock",
                "level": "info",
                "code": "ATL-SMOKE-001",
                "scope": "startup",
                "message": "PC Studio 0_1_1 camera receiver version loaded.",
            },
            {
                "timestamp": "mock",
                "level": "info",
                "code": "ATL-SMOKE-002",
                "scope": "safety",
                "message": "Camera frame receiving and simulation are enabled; AI inference, training, and physical traffic control remain disabled.",
            },
            {
                "timestamp": "mock",
                "level": "info",
                "code": "ATL-SMOKE-003",
                "scope": "api",
                "message": "Use /api/smoke/status for frontend-backend smoke testing.",
            },
        ]
    }
    logger.info("Log template returned", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)
