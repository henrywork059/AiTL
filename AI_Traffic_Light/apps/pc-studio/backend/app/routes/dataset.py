from fastapi import APIRouter, Request

from app.core.api_response import ok
from app.core.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/status")
def dataset_status(request: Request) -> dict:
    """Return placeholder dataset status."""
    data = {
        "active_dataset_id": None,
        "frame_count": 0,
        "label_count": 0,
        "capture_enabled": False,
        "status": "template_only",
    }
    logger.info("Dataset status template returned", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)


@router.get("/functions")
def dataset_functions(request: Request) -> dict:
    """Return planned dataset functions for review."""
    data = {
        "functions": [
            "capture_frame",
            "save_raw_image",
            "save_detection_json",
            "mark_frame_useful_or_bad",
            "review_captured_frame",
            "export_dataset_split",
            "import_label_file",
        ]
    }
    logger.info("Dataset function template returned", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)
