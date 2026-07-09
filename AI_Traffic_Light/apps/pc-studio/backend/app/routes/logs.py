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
            {"level": "info", "code": "ATL-TEMPLATE-000", "message": "PC Studio template loaded."},
            {"level": "info", "code": "ATL-TEMPLATE-001", "message": "No real camera or AI model is connected in 0_0_4."},
        ]
    }
    logger.info("Log template returned", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)
