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
    # Multipart parser must tolerate arbitrary TCP chunk boundaries.
    parser = _MjpegParser(boundary=b"frame")
    payload = mjpeg_part() + mjpeg_part()
    cut_points = [3, 17, 41, 79, len(payload)]
    cursor = 0
    parsed: list[bytes] = []
    for cut in cut_points:
        parsed.extend(parser.feed(payload[cursor:cut]))
        cursor = cut
    assert parsed == [JPEG_1X1, JPEG_1X1]
    print("[PASS] Content-Length MJPEG parser handles split headers/bodies and exact frame boundaries")

    # If two frames arrive together, service keeps newest only.
    class BurstStream:
        boundary = b"frame"
        def __init__(self) -> None:
            self.sent = False
        def read(self, _size: int) -> bytes:
            if self.sent:
                return b""
            self.sent = True
            return mjpeg_part() + mjpeg_part()
        def close(self) -> None:
            pass

    parser_service = RemoteCameraService()
    outcome = parser_service._consume_mjpeg_stream(
        stream=BurstStream(),
        source_id="esp32_cam_burst",
        stop_event=threading.Event(),
    )
    parser_status = parser_service.status()
    assert outcome == "stream_ended"
    assert parser_status["successful_fetches"] == 1
    assert parser_status["dropped_stale_frames"] == 1
    print("[PASS] newest-frame policy drops complete backlog frames instead of replaying latency")

    calls: list[tuple[str, str, dict[str, str] | None]] = []
    status_calls = 0
    opened_streams = 0
    service = RemoteCameraService()

    def request_json(host: str, path: str, method: str, query: dict[str, str] | None) -> dict:
        nonlocal status_calls
        calls.append((method, path, query))
        if path == "/status":
            status_calls += 1
            # Connect and the first recovery probe both see an idle session.
            return {
                "protocol": "aitl-camera-v035",
                "camera_ready": True,
                "session_active": False,
                "stream_client_active": False,
                "settings": SETTINGS,
            }
        if path == "/config":
            assert query is not None
            assert query["stream_fps"] == "15"
            return {"ok": True, "session_active": False, "settings": SETTINGS}
        if path == "/start":
            return {"camera_ready": True, "session_active": True, "settings": SETTINGS}
        if path == "/stop":
            return {"camera_ready": True, "session_active": False, "settings": SETTINGS}
        raise AssertionError(path)

    def open_stream(host: str):
        nonlocal opened_streams
        opened_streams += 1
        if opened_streams == 1:
            # Simulate a connection that produces a frame then drops.
            return RepeatingMjpegStream(end_after_frames=1)
        return RepeatingMjpegStream()

    service._json_requester = request_json
    service._stream_opener = open_stream

    connected = service.connect(host="192.168.68.57", source_id="esp32_cam_test")
    assert connected["configured"] is True
    assert connected["streaming"] is False
    assert opened_streams == 0
    assert [item[:2] for item in calls] == [("GET", "/status")]
    print("[PASS] Connect remains control-only with zero image transfer")

    started = service.start_stream(settings=SETTINGS, target_fps=15)
    assert started["streaming"] is True
    assert started["stream_connected"] is False or started["worker_running"] is True
    assert [item[:2] for item in calls[1:4]] == [
        ("POST", "/stop"),
        ("POST", "/config"),
        ("POST", "/start"),
    ]

    first = service.wait_for_new_frame(-1, timeout_seconds=0.5)
    assert first is not None and first.source_id == "esp32_cam_test"
    print("[PASS] browser relay can block on an event and wake immediately for a new physical frame")

    # First fake stream drops. V035 should probe status, see lost session,
    # reapply config/start, then reopen the MJPEG stream automatically.
    deadline = time.time() + 1.5
    recovered = None
    while time.time() < deadline:
        recovered = service.status()
        if recovered["session_recoveries"] >= 1 and recovered["stream_connected"]:
            break
        time.sleep(0.03)

    assert recovered is not None
    assert recovered["session_recoveries"] >= 1
    assert recovered["stream_reconnects"] >= 1
    assert opened_streams >= 2
    assert status_calls >= 2
    print("[PASS] dropped/rebooted ESP session is automatically re-armed and MJPEG reconnects")

    camera_frame_service.set_simulation(True)
    before = service.status()["successful_fetches"]
    time.sleep(0.08)
    during = service.status()
    assert during["paused_for_simulation"] is True
    assert during["successful_fetches"] <= before + 1

    camera_frame_service.set_simulation(False)
    deadline = time.time() + 0.8
    after = service.status()
    while time.time() < deadline and after["successful_fetches"] <= during["successful_fetches"]:
        time.sleep(0.03)
        after = service.status()
    assert after["successful_fetches"] > during["successful_fetches"]
    print("[PASS] simulation suspends physical transport and it resumes afterward")

    stopped = service.stop_stream()
    count_at_stop = stopped["successful_fetches"]
    time.sleep(0.05)
    assert service.status()["successful_fetches"] == count_at_stop
    assert stopped["worker_running"] is False
    assert stopped["stream_connected"] is False
    print("[PASS] Stop Stream closes the active reader with bounded shutdown")

    service.disconnect()
    assert service.status()["configured"] is False
    print("[PASS] Disconnect clears V035 remote state safely")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
