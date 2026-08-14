from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from app.core.api_response import ok
from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.core.logging_config import get_logger
from app.models import CameraSimulationSettingsRequest
from app.services.camera_frames import camera_frame_service

router = APIRouter()
logger = get_logger(__name__)


@router.get("/sources")
def list_camera_sources(request: Request) -> dict:
    """Return the working receiver and simulation source slots."""
    data = {
        "sources": [
            {"id": "frame_receiver", "label": "Device frame receiver", "type": "http_upload", "status": "ready"},
            {"id": "simulation_camera", "label": "PC simulation camera", "type": "simulation", "status": "ready"},
            {"id": "webcam_0", "label": "Local webcam", "type": "webcam", "status": "placeholder"},
            {"id": "video_file", "label": "Traffic video file", "type": "file", "status": "placeholder"},
        ]
    }
    logger.info("Camera source template returned", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)


@router.get("/status")
def camera_status(request: Request) -> dict:
    """Return receiver/simulation status and latest-frame metadata."""
    data = camera_frame_service.status()
    logger.debug(
        "Camera status returned",
        extra={
            "request_id": request.state.request_id,
            "camera_mode": data["mode"],
            "frame_number": data["frame_number"],
        },
    )
    return ok(data, request_id=request.state.request_id)


@router.post("/frame")
async def upload_camera_frame(
    request: Request,
    source_id: str = Query(default="device_camera", min_length=1, max_length=64),
) -> dict:
    """Accept one raw JPEG/PNG body from an ESP32 or Raspberry Pi camera node."""
    content = await request.body()
    frame = camera_frame_service.store_upload(
        source_id=source_id,
        content_type=request.headers.get("content-type", ""),
        content=content,
    )
    logger.info(
        "Camera frame received",
        extra={
            "request_id": request.state.request_id,
            "source_id": frame.source_id,
            "frame_number": frame.frame_number,
            "size_bytes": len(frame.content),
        },
    )
    return ok(frame.metadata(), request_id=request.state.request_id)


@router.get("/frame")
def latest_camera_frame(request: Request) -> Response:
    """Return the latest device or simulation frame as displayable image bytes."""
    frame = camera_frame_service.latest_frame()
    if frame is None:
        raise AppError(
            ErrorCode.CAMERA_NOT_CONNECTED,
            "No camera frame has arrived yet. Upload an image or start simulation mode.",
            status_code=404,
        )

    logger.debug(
        "Latest camera frame returned",
        extra={
            "request_id": request.state.request_id,
            "source_id": frame.source_id,
            "frame_number": frame.frame_number,
        },
    )
    return Response(
        content=frame.content,
        media_type=frame.content_type,
        headers={
            "Cache-Control": "no-store, max-age=0",
            "X-Request-ID": request.state.request_id,
            "X-Camera-Source": frame.source_id,
            "X-Frame-Number": str(frame.frame_number),
        },
    )


@router.post("/simulation/start")
def start_camera_simulation(request: Request) -> dict:
    """Enable the synthetic camera used to test the receiver/viewer workflow."""
    data = camera_frame_service.set_simulation(True)
    logger.info("Camera simulation started", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)


@router.post("/simulation/stop")
def stop_camera_simulation(request: Request) -> dict:
    """Return to device receiver mode without discarding the last device upload."""
    data = camera_frame_service.set_simulation(False)
    logger.info("Camera simulation stopped", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)


@router.post("/simulation/settings")
def update_camera_simulation_settings(
    payload: CameraSimulationSettingsRequest,
    request: Request,
) -> dict:
    """Adjust synthetic-scene density or pause/resume the active simulation."""
    data = camera_frame_service.configure_simulation(
        density=payload.density,
        paused=payload.paused,
    )
    logger.info(
        "Camera simulation settings updated",
        extra={
            "request_id": request.state.request_id,
            "simulation_density": data["simulation_density"],
            "simulation_paused": data["simulation_paused"],
        },
    )
    return ok(data, request_id=request.state.request_id)
