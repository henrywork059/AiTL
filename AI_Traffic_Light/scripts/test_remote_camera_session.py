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

    # Parser latency guard: when multiple complete JPEGs arrive in one read,
    # V034 deliberately stores only the newest one instead of replaying backlog.
    class BurstStream:
        def __init__(self) -> None:
            self.sent = False
        def read(self, _size: int) -> bytes:
            if self.sent:
                return b""
            self.sent = True
            part = b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + JPEG_1X1 + b"\r\n"
            return part + part
        def close(self) -> None:
            pass

    parser_service = RemoteCameraService()
    parser_outcome = parser_service._consume_mjpeg_stream(
        stream=BurstStream(),
        source_id="esp32_cam_burst",
        stop_event=threading.Event(),
    )
    parser_status = parser_service.status()
    assert parser_outcome == "stream_ended"
    assert parser_status["successful_fetches"] == 1
    assert parser_status["dropped_stale_frames"] == 1
    print("[PASS] MJPEG parser discards older complete frames when a read contains backlog")

    calls: list[tuple[str, str, dict[str, str] | None]] = []
    opened_streams = 0
    service = RemoteCameraService()
    service._json_requester = fake_control(calls)

    def open_stream(host: str):
        nonlocal opened_streams
        opened_streams += 1
        return FakeMjpegStream()

    service._stream_opener = open_stream

    connected = service.connect(host="192.168.68.57", source_id="esp32_cam_test")
    assert connected["configured"] is True
    assert connected["streaming"] is False
    assert opened_streams == 0
    assert [item[:2] for item in calls] == [("GET", "/status")]
    print("[PASS] V034 Connect remains status/control only with zero image transfer")

    started = service.start_stream(settings=SETTINGS, target_fps=15)
    assert started["streaming"] is True
    assert started["transport"] == "mjpeg"
    assert started["target_fps"] == 15
    assert [item[:2] for item in calls[1:4]] == [
        ("POST", "/stop"),
        ("POST", "/config"),
        ("POST", "/start"),
    ]
    assert calls[2][2]["stream_fps"] == "15"

    time.sleep(0.12)
    status = service.status()
    assert opened_streams >= 1
    assert status["successful_fetches"] >= 2
    assert status["measured_fps"] > 0
    frame = camera_frame_service.latest_frame()
    assert frame is not None and frame.source_id == "esp32_cam_test"
    print("[PASS] one persistent MJPEG worker continuously feeds CameraFrameService")

    camera_frame_service.set_simulation(True)
    before = service.status()["successful_fetches"]
    time.sleep(0.08)
    during = service.status()
    assert during["paused_for_simulation"] is True
    # Allow at most one already-read frame at the transition boundary.
    assert during["successful_fetches"] <= before + 1

    camera_frame_service.set_simulation(False)
    time.sleep(0.08)
    after = service.status()
    assert after["successful_fetches"] > during["successful_fetches"]
    print("[PASS] simulation pauses image transport and V034 reopens MJPEG afterward")

    stopped = service.stop_stream()
    count_at_stop = stopped["successful_fetches"]
    time.sleep(0.05)
    assert service.status()["successful_fetches"] == count_at_stop
    assert stopped["worker_running"] is False
    assert stopped["streaming"] is False
    print("[PASS] Stop Stream closes the active MJPEG reader immediately")

    service.disconnect()
    assert service.status()["configured"] is False
    print("[PASS] Disconnect clears V034 remote state safely")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
