from pydantic import BaseModel, Field
from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from app.core.api_response import ok
from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.core.logging_config import get_logger
from app.models import CameraSimulationSettingsRequest
from app.services.camera_frames import camera_frame_service
from app.services.remote_camera import remote_camera_service

router = APIRouter()
logger = get_logger(__name__)


class RemoteCameraConnectRequest(BaseModel):
    host: str = Field(min_length=7, max_length=64)
    source_id: str = Field(default="esp32_cam_01", min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    fetch_interval_ms: int = Field(default=500, ge=100, le=5000)


@router.get("/sources")
def list_camera_sources(request: Request) -> dict:
    """Return the working receiver, remote pull, and simulation source slots."""
    data = {
        "sources": [
            {"id": "remote_esp32", "label": "ESP32-CAM by IP", "type": "http_pull", "status": "ready"},
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


@router.get("/remote/status")
def remote_camera_status(request: Request) -> dict:
    data = remote_camera_service.status()
    return ok(data, request_id=request.state.request_id)


@router.post("/remote/connect")
def connect_remote_camera(payload: RemoteCameraConnectRequest, request: Request) -> dict:
    data = remote_camera_service.connect(
        host=payload.host,
        source_id=payload.source_id,
        fetch_interval_ms=payload.fetch_interval_ms,
    )
    logger.info(
        "Remote ESP camera connection configured",
        extra={
            "request_id": request.state.request_id,
            "camera_host": data["host"],
            "source_id": data["source_id"],
        },
    )
    return ok(data, request_id=request.state.request_id)


@router.post("/remote/disconnect")
def disconnect_remote_camera(request: Request) -> dict:
    data = remote_camera_service.disconnect()
    logger.info("Remote ESP camera disconnected", extra={"request_id": request.state.request_id})
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
    """Return the latest device, remote, or simulation frame as image bytes."""
    frame = camera_frame_service.latest_frame()
    if frame is None:
        raise AppError(
            ErrorCode.CAMERA_NOT_CONNECTED,
            "No camera frame has arrived yet. Connect an ESP camera, upload an image, or start simulation mode.",
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
    """Enable the synthetic camera. Remote pull remains configured but pauses ingestion."""
    data = camera_frame_service.set_simulation(True)
    logger.info("Camera simulation started", extra={"request_id": request.state.request_id})
    return ok(data, request_id=request.state.request_id)


@router.post("/simulation/stop")
def stop_camera_simulation(request: Request) -> dict:
    """Return to device/remote receiver mode without discarding the last device frame."""
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
