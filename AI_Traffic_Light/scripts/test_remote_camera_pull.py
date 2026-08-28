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
    "AP/aAAgBAwEBPwF//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAgEBPwF//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/a"
    "AAgBAQAGPwJ//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPyF//9k="
)


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

    service = RemoteCameraService()
    service._fetcher = lambda host: RemoteCapture(JPEG_1X1, "image/jpeg", 200)
    result = service.connect(host="192.168.1.87", source_id="esp32_cam_test", fetch_interval_ms=100)
    assert result["configured"] is True
    assert result["worker_running"] is True
    assert result["host"] == "192.168.1.87"
    assert result["source_id"] == "esp32_cam_test"
    assert result["successful_fetches"] >= 1

    time.sleep(0.15)
    status = service.status()
    assert status["successful_fetches"] >= 1
    frame = camera_frame_service.latest_frame()
    assert frame is not None
    assert frame.source_id == "esp32_cam_test"
    assert frame.width == 1 and frame.height == 1
    print("[PASS] remote camera probe/worker feeds the existing CameraFrameService pipeline")

    camera_frame_service.set_simulation(True)
    before = service.status()["successful_fetches"]
    time.sleep(0.2)
    during = service.status()
    assert during["paused_for_simulation"] is True
    assert during["successful_fetches"] == before
    camera_frame_service.set_simulation(False)
    time.sleep(0.2)
    after = service.status()
    assert after["successful_fetches"] > before
    print("[PASS] simulation pauses remote ingestion and remote pull resumes afterward")

    disconnected = service.disconnect()
    assert disconnected["configured"] is False
    assert disconnected["worker_running"] is False
    service.stop()
    print("[PASS] remote camera disconnect/shutdown stops its background worker")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
