from fastapi import APIRouter, Request

from app.core.api_response import ok
from app.core.logging_config import get_logger
from app.models import RuntimeSettingsRequest
from app.services.runtime_settings import runtime_settings_service

router = APIRouter()
logger = get_logger(__name__)


@router.get("/summary")
def settings_summary(request: Request) -> dict:
    """Return implemented settings groups."""
    data = {
        "groups": ["viewer", "inference", "training", "debug_logging"],
        "status": "ready",
        "runtime": runtime_settings_service.get(),
    }
    logger.info("Settings summary returned", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)


@router.get("/runtime")
def runtime_settings(request: Request) -> dict:
    data = runtime_settings_service.get()
    logger.info("Runtime settings returned", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)


@router.put("/runtime")
def save_runtime_settings(payload: RuntimeSettingsRequest, request: Request) -> dict:
    data = runtime_settings_service.save(payload.model_dump())
    logger.info("Runtime settings API updated", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)
