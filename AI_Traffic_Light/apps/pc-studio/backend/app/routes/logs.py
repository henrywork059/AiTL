from fastapi import APIRouter, Query, Request

from app.core.api_response import ok
from app.core.logging_config import get_logger, recent_log_entries

router = APIRouter()
logger = get_logger(__name__)


@router.get("/recent")
def recent_logs(request: Request, limit: int = Query(default=100, ge=1, le=200)) -> dict:
    """Return recent real backend log records from the bounded in-memory buffer."""
    data = {"logs": recent_log_entries(limit), "limit": limit, "status": "ready"}
    logger.info("Recent backend logs returned", extra={"request_id": request.state.request_id, "limit": limit})
    return ok(data, request_id=request.state.request_id)
