from fastapi import APIRouter, Request

from app.core.api_response import ok
from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.core.logging_config import get_logger
from app.models import CaptureFrameRequest
from app.services.camera_frames import camera_frame_service
from app.services.dataset_capture import dataset_capture_service

router = APIRouter()
logger = get_logger(__name__)


@router.get("/status")
def dataset_status(request: Request) -> dict:
    """Return persistent capture counts and the latest save result."""
    data = dataset_capture_service.status()
    logger.info("Dataset capture status returned", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)


@router.post("/captures")
def capture_latest_frame(payload: CaptureFrameRequest, request: Request) -> dict:
    """Persist the latest receiver or simulation frame and its metadata."""
    frame = camera_frame_service.latest_frame()
    if frame is None:
        raise AppError(
            ErrorCode.CAMERA_NOT_CONNECTED,
            "No camera frame is available to capture. Upload a frame or start simulation mode.",
            status_code=409,
        )
    record = dataset_capture_service.capture_frame(
        frame,
        session_id=payload.session_id,
        quality_tag=payload.quality_tag,
        note=payload.note,
    )
    logger.info(
        "Dataset capture API completed",
        extra={
            "request_id": request.state.request_id,
            "capture_id": record.capture_id,
            "origin": record.origin,
        },
    )
    return ok(record.to_dict(), request_id=request.state.request_id)


@router.get("/functions")
def dataset_functions(request: Request) -> dict:
    """Return implemented and planned dataset functions."""
    data = {
        "functions": [
            "capture_frame",
            "save_raw_image",
            "save_capture_metadata_json",
            "capture_receiver_or_simulation_frame",
            "save_detection_json_later",
            "mark_frame_useful_or_bad",
            "review_captured_frame",
            "export_dataset_split",
            "import_label_file",
        ]
    }
    logger.info("Dataset function template returned", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)
