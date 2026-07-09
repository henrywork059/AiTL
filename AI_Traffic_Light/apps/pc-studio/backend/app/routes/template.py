from fastapi import APIRouter, Request

from app.core.api_response import ok
from app.core.logging_config import get_logger
from app.services.template_state import get_template_summary

router = APIRouter()
logger = get_logger(__name__)


@router.get("/pc-studio")
def pc_studio_template(request: Request) -> dict:
    """Return the planned PC Studio page structure for GUI confirmation."""
    data = get_template_summary()
    logger.info("PC Studio template summary returned", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)
