from __future__ import annotations

import base64
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "pc-studio" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.exceptions import AppError
from app.services.camera_frames import camera_frame_service
from app.services.remote_camera import RemoteCameraService, RemoteCapture, normalize_private_lan_ipv4

# Small 1x1 JPEG with valid SOF dimensions.
JPEG_1X1 = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////"
    "2wBDAf//////////////////////////////////////////////////////////////////////////////////////"
    "wgARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAf/xAAUEAEAAAAAAAAAAAAAAAAAAAAA"
    "/9oADAMBAAIQAxAAAAF//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABBQJ//8QAFBEBAAAAAAAAAAAAAAAAAAAA"
    "AP/aAAgBAwEBPwF//8QAFBEBAAAAAAAAAAAAAAAAAAAAAAP/aAAgBAgEBPwF//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/a"
    "AAgBAQAGPwJ//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPyF//9k="
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
    print("[PASS] remote camera host validation is restricted to literal RFC1918 IPv4")

    calls: list[tuple[str, str]] = []
    captures = 0
    service = RemoteCameraService()

    def request_json(host: str, path: str, method: str, query: dict[str, str] | None) -> dict:
        calls.append((method, path))
        if path == "/status":
            return {"camera_ready": True, "session_active": False, "settings": SETTINGS}
        if path == "/config":
            assert query is not None
            assert query["frame_size"] == "VGA"
            assert query["jpeg_quality"] == "12"
            return {"ok": True, "session_active": False, "settings": SETTINGS}
        if path == "/start":
            return {"camera_ready": True, "session_active": True, "settings": SETTINGS}
        if path == "/stop":
            return {"camera_ready": True, "session_active": False, "settings": SETTINGS}
        raise AssertionError(path)

    def fetch_capture(host: str) -> RemoteCapture:
        nonlocal captures
        captures += 1
        return RemoteCapture(JPEG_1X1, "image/jpeg", 200)

    service._json_requester = request_json
    service._fetcher = fetch_capture

    # V033 invariant: Connect is status/control only.
    result = service.connect(host="192.168.1.87", source_id="esp32_cam_test")
    assert result["configured"] is True
    assert result["worker_running"] is False
    assert result["streaming"] is False
    assert result["host"] == "192.168.1.87"
    assert result["source_id"] == "esp32_cam_test"
    assert captures == 0
    assert calls == [("GET", "/status")]
    print("[PASS] connect performs status/control only and requests zero images")

    # V033 starts the worker only after settings + /start.
    result = service.start_stream(settings=SETTINGS, fetch_interval_ms=100)
    assert result["worker_running"] is True
    assert result["streaming"] is True
    assert calls[1:4] == [("POST", "/stop"), ("POST", "/config"), ("POST", "/start")]

    time.sleep(0.15)
    status = service.status()
    assert status["successful_fetches"] >= 1
    assert captures >= 1
    frame = camera_frame_service.latest_frame()
    assert frame is not None
    assert frame.source_id == "esp32_cam_test"
    assert frame.width == 1 and frame.height == 1
    print("[PASS] active V033 session feeds the existing CameraFrameService pipeline")

    camera_frame_service.set_simulation(True)
    before = captures
    time.sleep(0.2)
    during = service.status()
    assert during["paused_for_simulation"] is True
    assert captures == before

    camera_frame_service.set_simulation(False)
    time.sleep(0.2)
    after = service.status()
    assert captures > before
    assert after["successful_fetches"] >= status["successful_fetches"]
    print("[PASS] simulation pauses remote image requests and capture resumes afterward")

    stopped = service.stop_stream()
    captured_at_stop = captures
    time.sleep(0.15)
    assert stopped["streaming"] is False
    assert stopped["worker_running"] is False
    assert captures == captured_at_stop
    print("[PASS] stop_stream ends the image worker and keeps the ESP connection available")

    disconnected = service.disconnect()
    assert disconnected["configured"] is False
    assert disconnected["worker_running"] is False
    service.stop()
    print("[PASS] disconnect/shutdown clears the remote camera safely")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
