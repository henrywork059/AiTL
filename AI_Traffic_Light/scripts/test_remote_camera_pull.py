from __future__ import annotations

from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "pc-studio" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.exceptions import AppError
from app.services.camera_frames import camera_frame_service
from app.services.remote_camera import RemoteCameraService, _MjpegParser, normalize_private_lan_ipv4

JPEG_1X1 = (
    b"\xff\xd8"
    b"\xff\xc0\x00\x0b"
    b"\x08"
    b"\x00\x01"
    b"\x00\x01"
    b"\x01"
    b"\x01\x11\x00"
    b"\xff\xd9"
)

SETTINGS = {
    "frame_size": "VGA",
    "jpeg_quality": 12,
    "brightness": 0,
    "contrast": 0,
    "saturation": 0,
    "special_effect": 0,
    "awb": True,
    "awb_gain": True,
    "wb_mode": 0,
    "aec": True,
    "aec2": False,
    "ae_level": 0,
    "aec_value": 300,
    "agc": True,
    "agc_gain": 0,
    "gainceiling": 0,
    "bpc": False,
    "wpc": True,
    "raw_gma": True,
    "lenc": True,
    "hmirror": False,
    "vflip": False,
    "dcw": True,
    "colorbar": False,
}


def mjpeg_part(frame: bytes = JPEG_1X1) -> bytes:
    return (
        b"\r\n--frame\r\n"
        b"Content-Type: image/jpeg\r\n"
        b"Content-Length: " + str(len(frame)).encode() + b"\r\n"
        b"X-AiTL-Sequence: 1\r\n\r\n"
        + frame
        + b"\r\n"
    )


class RepeatingMjpegStream:
    boundary = b"frame"

    def __init__(self, *, end_after_frames: int | None = None) -> None:
        self.closed = False
        self.frames = 0
        self.end_after_frames = end_after_frames

    def read(self, _size: int) -> bytes:
        if self.closed:
            return b""
        if self.end_after_frames is not None and self.frames >= self.end_after_frames:
            return b""
        self.frames += 1
        time.sleep(0.01)
        return mjpeg_part()

    def close(self) -> None:
        self.closed = True


def expect_app_error(fn, code: str) -> None:
    try:
        fn()
    except AppError as exc:
        assert exc.code.value == code, (exc.code.value, code)
    else:
        raise AssertionError(f"Expected AppError {code}")


def main() -> int:
    assert normalize_private_lan_ipv4("192.168.1.87") == "192.168.1.87"
    assert normalize_private_lan_ipv4("10.20.30.40") == "10.20.30.40"
    assert normalize_private_lan_ipv4("172.16.5.2") == "172.16.5.2"
    expect_app_error(lambda: normalize_private_lan_ipv4("8.8.8.8"), "ATL-CAMERA-003")
    expect_app_error(lambda: normalize_private_lan_ipv4("example.com"), "ATL-CAMERA-003")
    print("[PASS] remote camera host validation remains literal private-LAN IPv4 only")

    calls: list[tuple[str, str, dict[str, str] | None]] = []
    service = RemoteCameraService()

    def request_json(host: str, path: str, method: str, query: dict[str, str] | None) -> dict:
        calls.append((method, path, query))
        if path == "/status":
            return {"camera_ready": True, "session_active": True, "settings": SETTINGS}
        if path == "/config":
            assert query is not None
            return {"ok": True, "session_active": False, "settings": SETTINGS}
        if path == "/start":
            return {"camera_ready": True, "session_active": True, "settings": SETTINGS}
        if path == "/stop":
            return {"camera_ready": True, "session_active": False, "settings": SETTINGS}
        raise AssertionError(path)

    service._json_requester = request_json
    service._stream_opener = lambda host: RepeatingMjpegStream()

    service.connect(host="192.168.1.87", source_id="esp32_cam_compat")
    assert service.status()["successful_fetches"] == 0

    # V033/V034 callers using fetch_interval_ms remain accepted.
    started = service.start_stream(settings=SETTINGS, fetch_interval_ms=100)
    assert started["target_fps"] == 10
    assert calls[2][2]["stream_fps"] == "10"

    deadline = time.time() + 0.5
    while time.time() < deadline and service.status()["successful_fetches"] < 1:
        time.sleep(0.02)
    assert service.status()["successful_fetches"] >= 1
    print("[PASS] older start-call shape maps interval to V035 target FPS")

    service.stop()
    assert service.status()["worker_running"] is False
    print("[PASS] resilient transport shutdown remains bounded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
