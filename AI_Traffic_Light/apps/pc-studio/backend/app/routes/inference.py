from fastapi import APIRouter, Query, Request, Response

from app.core.api_response import ok
from app.core.logging_config import get_logger
from app.services.camera_frames import camera_frame_service
from app.services.inference import inference_service

router = APIRouter()
logger = get_logger(__name__)


@router.get("/status")
def inference_status(request: Request) -> dict:
    """Return trained-model discovery and live inference status."""
    data = inference_service.status()
    logger.info("Inference status returned", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)


@router.post("/load-latest")
def load_latest_model(request: Request) -> dict:
    """Load the newest local outputs/training/*/weights/best.pt model."""
    data = inference_service.load_latest()
    logger.info(
        "Latest inference model loaded through API",
        extra={"request_id": request.state.request_id, "model_id": data.get("active_model_id")},
    )
    return ok(data, request_id=request.state.request_id)


@router.post("/unload")
def unload_model(request: Request) -> dict:
    """Release the active model and clear cached live inference results."""
    data = inference_service.unload()
    logger.info("Inference model unloaded through API", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)


@router.get("/detections")
def live_detections(request: Request) -> dict:
    """Run or return cached detection results for the newest camera frame."""
    frame = camera_frame_service.latest_frame()
    data = inference_service.detect_frame(frame)
    logger.info(
        "Live detections returned",
        extra={
            "request_id": request.state.request_id,
            "frame_id": data.get("frame_id"),
            "detection_count": len(data.get("detections", [])),
        },
    )
    return ok(data, request_id=request.state.request_id)


@router.get("/frame")
def inferred_source_frame(
    request: Request,
    source_id: str | None = Query(default=None, min_length=1, max_length=64),
    frame_number: int | None = Query(default=None, ge=1),
) -> Response:
    """Return an exact recent source frame used for inference."""
    frame = inference_service.source_frame(source_id=source_id, frame_number=frame_number)
    return Response(
        content=frame.content,
        media_type=frame.content_type,
        headers={
            "Cache-Control": "no-store, max-age=0",
            "X-Request-ID": request.state.request_id,
            "X-Frame-Number": str(frame.frame_number),
            "X-Source-ID": frame.source_id,
        },
    )


@router.get("/functions")
def inference_functions(request: Request) -> dict:
    """Return implemented inference functions for GUI confirmation."""
    data = {
        "functions": [
            "discover_trained_best_models",
            "load_latest_trained_model",
            "unload_model",
            "run_detection_on_latest_camera_frame",
            "cache_detection_per_camera_frame",
            "return_original_coordinate_boxes",
            "return_exact_inferred_source_frame",
        ]
    }
    logger.info("Inference function list returned", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)
