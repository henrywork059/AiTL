from fastapi import APIRouter, Query, Request
from fastapi.responses import FileResponse

from app.core.api_response import ok
from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.core.logging_config import get_logger
from app.models import BuildTrainingDatasetRequest, CaptureFrameRequest, SaveCaptureLabelsRequest
from app.services.camera_frames import camera_frame_service
from app.services.dataset_capture import dataset_capture_service
from app.services.dataset_labeling import dataset_labeling_service

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


@router.get("/captures")
def list_captures(
    request: Request,
    limit: int = Query(default=200, ge=1, le=1000),
    session_id: str | None = Query(default=None, max_length=64),
) -> dict:
    """List persisted captures with labeling state for the Dataset Review UI."""
    data = dataset_labeling_service.list_captures(limit=limit, session_id=session_id)
    logger.info(
        "Dataset capture list returned",
        extra={"request_id": request.state.request_id, "count": len(data["captures"])},
    )
    return ok(data, request_id=request.state.request_id)


@router.get("/captures/{capture_id}/image")
def captured_image(capture_id: str, request: Request) -> FileResponse:
    """Return one saved capture image for local review."""
    image_path, content_type = dataset_labeling_service.get_capture_image(capture_id)
    logger.info(
        "Captured image returned",
        extra={"request_id": request.state.request_id, "capture_id": capture_id},
    )
    return FileResponse(
        image_path,
        media_type=content_type,
        headers={"X-Request-ID": request.state.request_id, "Cache-Control": "no-store"},
    )


@router.get("/captures/{capture_id}/labels")
def capture_labels(capture_id: str, request: Request) -> dict:
    """Return saved manual labels or an unreviewed empty label document."""
    data = dataset_labeling_service.get_labels(capture_id)
    return ok(data, request_id=request.state.request_id)


@router.put("/captures/{capture_id}/labels")
def save_capture_labels(capture_id: str, payload: SaveCaptureLabelsRequest, request: Request) -> dict:
    """Replace the manual bounding-box labels for one captured frame."""
    data = dataset_labeling_service.save_labels(
        capture_id,
        [label.model_dump() for label in payload.labels],
    )
    logger.info(
        "Capture labels API completed",
        extra={"request_id": request.state.request_id, "capture_id": capture_id, "label_count": len(payload.labels)},
    )
    return ok(data, request_id=request.state.request_id)


@router.get("/training-dataset/status")
def training_dataset_status(request: Request) -> dict:
    """Report whether the managed in-app labeled YOLO dataset is current."""
    return ok(dataset_labeling_service.training_dataset_status(), request_id=request.state.request_id)


@router.post("/training-dataset")
def build_training_dataset(payload: BuildTrainingDatasetRequest, request: Request) -> dict:
    """Build datasets/yolo from reviewed captures for the existing training runner."""
    data = dataset_labeling_service.build_training_dataset(validation_fraction=payload.validation_fraction)
    logger.info(
        "Managed training dataset API completed",
        extra={"request_id": request.state.request_id, "train_count": data["train_count"], "val_count": data["val_count"]},
    )
    return ok(data, request_id=request.state.request_id)


@router.get("/functions")
def dataset_functions(request: Request) -> dict:
    """Return implemented and planned dataset functions."""
    data = {
        "functions": [
            "capture_frame",
            "save_raw_image",
            "save_capture_metadata_json",
            "capture_receiver_or_simulation_frame",
            "browse_captured_frames",
            "save_manual_bounding_box_labels",
            "save_reviewed_negative_frame",
            "exclude_bad_frames_from_training_build",
            "build_managed_yolo_train_val_split",
            "use_managed_dataset_in_training",
            "automatic_labeling_later",
        ]
    }
    logger.info("Dataset function list returned", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)
