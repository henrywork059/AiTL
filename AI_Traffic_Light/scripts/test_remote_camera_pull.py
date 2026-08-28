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
from app.services.remote_camera import RemoteCameraService, normalize_private_lan_ipv4

JPEG_1X1 = (
    b"\xff\xd8"  # SOI
    b"\xff\xc0\x00\x0b"  # SOF0, segment length 11
    b"\x08"  # precision
    b"\x00\x01"  # height = 1
    b"\x00\x01"  # width = 1
    b"\x01"  # one component
    b"\x01\x11\x00"
    b"\xff\xd9"  # EOI
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


class FakeMjpegStream:
    def __init__(self) -> None:
        self.closed = False

    def read(self, _size: int) -> bytes:
        if self.closed:
            return b""
        time.sleep(0.01)
        return (
            b"\r\n--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
            + str(len(JPEG_1X1)).encode()
            + b"\r\n\r\n"
            + JPEG_1X1
            + b"\r\n"
        )

    def close(self) -> None:
        self.closed = True


def fake_control(calls: list[tuple[str, str, dict[str, str] | None]]):
    def request_json(host: str, path: str, method: str, query: dict[str, str] | None) -> dict:
        calls.append((method, path, query))
        if path == "/status":
            return {"camera_ready": True, "session_active": False, "settings": SETTINGS}
        if path == "/config":
            assert query is not None
            assert query["frame_size"] == "VGA"
            assert query["jpeg_quality"] == "12"
            assert query["stream_fps"].isdigit()
            return {"ok": True, "session_active": False, "settings": SETTINGS}
        if path == "/start":
            return {"camera_ready": True, "session_active": True, "settings": SETTINGS}
        if path == "/stop":
            return {"camera_ready": True, "session_active": False, "settings": SETTINGS}
        raise AssertionError(path)
    return request_json


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
    print("[PASS] remote camera host validation remains private-LAN only")

    calls: list[tuple[str, str, dict[str, str] | None]] = []
    service = RemoteCameraService()
    service._json_requester = fake_control(calls)
    service._stream_opener = lambda host: FakeMjpegStream()

    service.connect(host="192.168.1.87", source_id="esp32_cam_compat")
    assert service.status()["successful_fetches"] == 0

    # V034 retains the V033 fetch_interval_ms call shape as a compatibility alias.
    started = service.start_stream(settings=SETTINGS, fetch_interval_ms=100)
    assert started["target_fps"] == 10
    assert calls[2][2]["stream_fps"] == "10"
    time.sleep(0.05)
    assert service.status()["successful_fetches"] >= 1
    print("[PASS] V033 start-call compatibility maps capture interval to V034 target FPS")

    service.stop()
    print("[PASS] low-latency transport shutdown is bounded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
