from __future__ import annotations

import base64
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "pc-studio" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.camera_frames import camera_frame_service
from app.services.remote_camera import RemoteCameraService, RemoteCapture, normalize_private_lan_ipv4

JPEG_1X1 = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////"
    "2wBDAf//////////////////////////////////////////////////////////////////////////////////////"
    "wgARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAf/xAAUEAEAAAAAAAAAAAAAAAAAAAAA"
    "/9oADAMBAAIQAxAAAAF//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABBQJ//8QAFBEBAAAAAAAAAAAAAAAAAAAA"
    "AP/aAAgBAwEBPwF//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAgEBPwF//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/a"
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


def main() -> int:
    assert normalize_private_lan_ipv4("192.168.68.57") == "192.168.68.57"

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
            assert query["awb"] == "1"
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

    connected = service.connect(host="192.168.68.57", source_id="esp32_cam_test")
    assert connected["configured"] is True
    assert connected["streaming"] is False
    assert captures == 0, "Connect must not request an image"
    assert calls == [("GET", "/status")]
    print("[PASS] Connect performs status/control only; zero image requests")

    started = service.start_stream(settings=SETTINGS, fetch_interval_ms=100)
    assert started["streaming"] is True
    assert calls[1:4] == [("POST", "/stop"), ("POST", "/config"), ("POST", "/start")]
    time.sleep(0.18)
    assert captures >= 1
    frame = camera_frame_service.latest_frame()
    assert frame is not None and frame.source_id == "esp32_cam_test"
    print("[PASS] Settings -> start ordering precedes /capture polling")

    before = captures
    camera_frame_service.set_simulation(True)
    time.sleep(0.2)
    assert captures == before
    camera_frame_service.set_simulation(False)
    time.sleep(0.2)
    assert captures > before
    print("[PASS] Simulation pauses/resumes PC image requests")

    stopped = service.stop_stream()
    after_stop = captures
    time.sleep(0.15)
    assert stopped["streaming"] is False
    assert captures == after_stop
    assert calls[-1] == ("POST", "/stop")
    print("[PASS] Stop ends capture requests and returns session to idle")

    service.disconnect()
    assert service.status()["configured"] is False
    print("[PASS] Disconnect clears the configured ESP")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
