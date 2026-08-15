from fastapi import APIRouter, Query, Request, Response

from app.core.api_response import ok
from app.core.logging_config import get_logger
from app.models import InferenceLoadRequest
from app.services.camera_frames import camera_frame_service
from app.services.inference import inference_service
from app.services.object_tracking import object_tracking_service
from app.services.zones import zone_service

router = APIRouter()
logger = get_logger(__name__)


@router.get("/status")
def inference_status(request: Request) -> dict:
    """Return trained-model discovery and live inference status."""
    data = inference_service.status()
    data["tracking"] = object_tracking_service.status()
    logger.info("Inference status returned", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)


@router.post("/load")
def load_selected_or_default_model(payload: InferenceLoadRequest, request: Request) -> dict:
    """Load a chosen model, or the default/latest when model_id is omitted."""
    if payload.model_id:
        data = inference_service.load_selected(payload.model_id)
    else:
        data = inference_service.load_default_or_latest()
    object_tracking_service.reset_active()
    logger.info(
        "Inference model loaded through API",
        extra={"request_id": request.state.request_id, "model_id": data.get("active_model_id")},
    )
    return ok(data, request_id=request.state.request_id)


@router.post("/load-latest")
def load_latest_model(request: Request) -> dict:
    """Backward-compatible load of the newest local outputs/training/*/weights/best.pt model."""
    data = inference_service.load_latest()
    object_tracking_service.reset_active()
    logger.info(
        "Latest inference model loaded through API",
        extra={"request_id": request.state.request_id, "model_id": data.get("active_model_id")},
    )
    return ok(data, request_id=request.state.request_id)


@router.post("/unload")
def unload_model(request: Request) -> dict:
    """Release the active model and clear cached live inference/tracking results."""
    data = inference_service.unload()
    object_tracking_service.reset_active()
    logger.info("Inference model unloaded through API", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)


@router.get("/detections")
def live_detections(
    request: Request,
    confidence: float = Query(default=0.10, ge=0.01, le=1.0),
) -> dict:
    """Run/cached detections for the newest frame and assign frame-deduplicated prototype track IDs."""
    frame = camera_frame_service.latest_frame()
    raw = inference_service.detect_frame(frame, confidence_threshold=confidence)
    data = object_tracking_service.update(raw, zone_service.zones())
    logger.info(
        "Live tracked detections returned",
        extra={
            "request_id": request.state.request_id,
            "frame_id": data.get("frame_id"),
            "detection_count": len(data.get("detections", [])),
            "active_track_count": data.get("tracking", {}).get("active_track_count"),
            "confidence": confidence,
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
            "load_selected_or_default_model",
            "load_latest_trained_model",
            "unload_model",
            "run_detection_on_latest_camera_frame",
            "cache_detection_per_camera_frame_and_confidence",
            "assign_cross_frame_track_ids",
            "return_original_coordinate_boxes",
            "return_exact_inferred_source_frame",
        ]
    }
    logger.info("Inference function list returned", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)
