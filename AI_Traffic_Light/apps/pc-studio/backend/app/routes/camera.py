import time
from typing import Iterator, Literal

from pydantic import BaseModel, Field
from fastapi import APIRouter, Query, Request
from fastapi.responses import Response, StreamingResponse

from app.core.api_response import ok
from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.core.logging_config import get_logger
from app.models import CameraSimulationSettingsRequest
from app.services.camera_frames import camera_frame_service
from app.services.remote_camera_manager import remote_camera_manager as remote_camera_service

router = APIRouter()
logger = get_logger(__name__)

MJPEG_BOUNDARY = b"--frame\r\n"


class RemoteCameraConnectRequest(BaseModel):
    host: str = Field(min_length=7, max_length=64)
    source_id: str = Field(default="esp32_cam_01", min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")


class RemoteCameraSettingsRequest(BaseModel):
    frame_size: Literal["QQVGA", "HQVGA", "QVGA", "CIF", "VGA", "SVGA", "XGA", "SXGA", "UXGA"] = "VGA"
    jpeg_quality: int = Field(default=14, ge=4, le=63)
    brightness: int = Field(default=0, ge=-2, le=2)
    contrast: int = Field(default=0, ge=-2, le=2)
    saturation: int = Field(default=0, ge=-2, le=2)
    special_effect: int = Field(default=0, ge=0, le=6)
    awb: bool = True
    awb_gain: bool = True
    wb_mode: int = Field(default=0, ge=0, le=4)
    aec: bool = True
    aec2: bool = False
    ae_level: int = Field(default=0, ge=-2, le=2)
    aec_value: int = Field(default=300, ge=0, le=1200)
    agc: bool = True
    agc_gain: int = Field(default=0, ge=0, le=30)
    gainceiling: int = Field(default=0, ge=0, le=6)
    bpc: bool = False
    wpc: bool = True
    raw_gma: bool = True
    lenc: bool = True
    hmirror: bool = False
    vflip: bool = False
    dcw: bool = True
    colorbar: bool = False




class RemoteCameraProfileRequest(BaseModel):
    host: str = Field(min_length=7, max_length=64)
    source_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    target_fps: int = Field(default=15, ge=1, le=30)
    settings: RemoteCameraSettingsRequest = Field(default_factory=RemoteCameraSettingsRequest)


class RemoteCameraSelectRequest(BaseModel):
    source_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")

class RemoteCameraStartRequest(BaseModel):
    target_fps: int = Field(default=15, ge=1, le=30)
    # Retained so V033-V035 callers remain accepted; V036 UI sends target_fps.
    fetch_interval_ms: int | None = Field(default=None, ge=34, le=5000)
    settings: RemoteCameraSettingsRequest = Field(default_factory=RemoteCameraSettingsRequest)


def _live_mjpeg() -> Iterator[bytes]:
    """Browser relay remains MJPEG; ESP-to-PC transport is the V036 TCP JPEG stream."""
    last_frame_number = -1

    while True:
        if camera_frame_service.simulation_enabled:
            frame = camera_frame_service.latest_frame()
            if frame is None or frame.frame_number == last_frame_number:
                time.sleep(0.02)
                continue
        elif remote_camera_service.streaming_requested:
            frame = remote_camera_service.wait_for_new_frame(last_frame_number, timeout_seconds=1.0)
            if frame is None:
                continue
        else:
            # Legacy raw uploads remain compatible with the shared frame service.
            frame = camera_frame_service.latest_frame()
            if frame is None or frame.frame_number == last_frame_number:
                time.sleep(0.02)
                continue

        last_frame_number = frame.frame_number
        header = (
            MJPEG_BOUNDARY
            + f"Content-Type: {frame.content_type}\r\n".encode()
            + f"Content-Length: {len(frame.content)}\r\n".encode()
            + f"X-Camera-Source: {frame.source_id}\r\n".encode()
            + f"X-Frame-Number: {frame.frame_number}\r\n\r\n".encode()
        )
        yield header + frame.content + b"\r\n"


@router.get("/sources")
def list_camera_sources(request: Request) -> dict:
    data = {
        "sources": [
            {"id": "remote_esp32", "label": "ESP32-CAM by IP", "type": "tcp_jpeg_pull", "status": "ready"},
            {"id": "frame_receiver", "label": "Device frame receiver", "type": "http_upload", "status": "ready"},
            {"id": "simulation_camera", "label": "PC simulation camera", "type": "simulation", "status": "ready"},
            {"id": "webcam_0", "label": "Local webcam", "type": "webcam", "status": "placeholder"},
            {"id": "video_file", "label": "Traffic video file", "type": "file", "status": "placeholder"},
        ]
    }
    return ok(data, request_id=request.state.request_id)


@router.get("/status")
def camera_status(request: Request) -> dict:
    return ok(camera_frame_service.status(), request_id=request.state.request_id)


@router.get("/live.mjpeg")
def live_camera_mjpeg(request: Request) -> StreamingResponse:
    """Low-latency browser preview from the same PC frame pipeline used by inference/capture."""
    return StreamingResponse(
        _live_mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0, no-transform",
            "Pragma": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Request-ID": request.state.request_id,
        },
    )


@router.get("/remote/status")
def remote_camera_status(request: Request) -> dict:
    return ok(remote_camera_service.status(refresh_device=True), request_id=request.state.request_id)


@router.post("/remote/cameras")
def save_remote_camera_profile(payload: RemoteCameraProfileRequest, request: Request) -> dict:
    data = remote_camera_service.save_profile(
        host=payload.host,
        source_id=payload.source_id,
        target_fps=payload.target_fps,
        settings=payload.settings.model_dump(),
        select=True,
    )
    logger.info(
        "Remote ESP camera profile saved",
        extra={"request_id": request.state.request_id, "camera_host": payload.host, "source_id": payload.source_id},
    )
    return ok(data, request_id=request.state.request_id)


@router.post("/remote/select")
def select_remote_camera(payload: RemoteCameraSelectRequest, request: Request) -> dict:
    data = remote_camera_service.select(payload.source_id)
    logger.info(
        "Remote ESP camera selected",
        extra={"request_id": request.state.request_id, "source_id": payload.source_id},
    )
    return ok(data, request_id=request.state.request_id)


@router.delete("/remote/cameras/{source_id}")
def delete_remote_camera_profile(source_id: str, request: Request) -> dict:
    data = remote_camera_service.delete_profile(source_id)
    logger.info(
        "Remote ESP camera profile deleted",
        extra={"request_id": request.state.request_id, "source_id": source_id},
    )
    return ok(data, request_id=request.state.request_id)


@router.post("/remote/connect")
def connect_remote_camera(payload: RemoteCameraConnectRequest, request: Request) -> dict:
    data = remote_camera_service.connect(host=payload.host, source_id=payload.source_id)
    logger.info(
        "Remote ESP camera connected for control",
        extra={"request_id": request.state.request_id, "camera_host": data["host"], "source_id": data["source_id"]},
    )
    return ok(data, request_id=request.state.request_id)


@router.post("/remote/start")
def start_remote_camera(payload: RemoteCameraStartRequest, request: Request) -> dict:
    data = remote_camera_service.start_stream(
        settings=payload.settings.model_dump(),
        target_fps=payload.target_fps,
        fetch_interval_ms=payload.fetch_interval_ms,
    )
    logger.info(
        "Remote ESP low-latency TCP JPEG stream started",
        extra={
            "request_id": request.state.request_id,
            "camera_host": data["host"],
            "source_id": data["source_id"],
            "target_fps": data["target_fps"],
        },
    )
    return ok(data, request_id=request.state.request_id)


@router.post("/remote/stop")
def stop_remote_camera(request: Request) -> dict:
    data = remote_camera_service.stop_stream()
    logger.info("Remote ESP camera stream stopped", extra={"request_id": request.state.request_id})
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
    content = await request.body()
    frame = camera_frame_service.store_upload(
        source_id=source_id,
        content_type=request.headers.get("content-type", ""),
        content=content,
    )
    return ok(frame.metadata(), request_id=request.state.request_id)


@router.get("/frame")
def latest_camera_frame(request: Request) -> Response:
    frame = camera_frame_service.latest_frame()
    if frame is None:
        raise AppError(
            ErrorCode.CAMERA_NOT_CONNECTED,
            "No camera frame has arrived yet. Start an ESP stream, upload an image, or start simulation mode.",
            status_code=404,
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
    camera_frame_service.set_simulation(True)
    remote_camera_service.sync_after_simulation_change()
    return ok(camera_frame_service.status(), request_id=request.state.request_id)


@router.post("/simulation/stop")
def stop_camera_simulation(request: Request) -> dict:
    camera_frame_service.set_simulation(False)
    remote_camera_service.sync_after_simulation_change()
    # Return status after the manager has restored/cleared the selected physical
    # source, so the response cannot describe the pre-switch shared frame state.
    return ok(camera_frame_service.status(), request_id=request.state.request_id)


@router.post("/simulation/settings")
def update_camera_simulation_settings(
    payload: CameraSimulationSettingsRequest,
    request: Request,
) -> dict:
    data = camera_frame_service.configure_simulation(density=payload.density, paused=payload.paused)
    return ok(data, request_id=request.state.request_id)
