from fastapi import APIRouter, Request

from app.core.api_response import ok
from app.core.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/registry")
def model_registry(request: Request) -> dict:
    """Return placeholder model registry entries."""
    data = {
        "models": [
            {"id": "pretrained_yolo_placeholder", "label": "Pretrained YOLO placeholder", "status": "planned"},
            {"id": "traffic_custom_placeholder", "label": "Custom traffic model placeholder", "status": "planned"},
        ]
    }
    logger.info("Model registry template returned", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)
