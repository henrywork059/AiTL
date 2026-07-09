from fastapi import APIRouter, Request

from app.core.api_response import ok
from app.core.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/status")
def inference_status(request: Request) -> dict:
    """Return placeholder inference engine status."""
    data = {
        "model_loaded": False,
        "active_model_id": None,
        "backend": "placeholder",
        "last_latency_ms": None,
        "supported_tasks": ["object_detection", "future_instance_segmentation"],
    }
    logger.info("Inference status template returned", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)


@router.get("/functions")
def inference_functions(request: Request) -> dict:
    """Return planned inference functions for GUI confirmation."""
    data = {
        "functions": [
            "load_model",
            "unload_model",
            "run_detection_on_frame",
            "filter_detections_by_class_and_confidence",
            "convert_model_boxes_to_original_image_coordinates",
            "return_detection_frame_json",
        ]
    }
    logger.info("Inference function template returned", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)
