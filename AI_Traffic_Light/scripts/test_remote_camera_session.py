from __future__ import annotations

from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "pc-studio" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.camera_frames import camera_frame_service
from app.services.remote_camera import (
    CAMERA_PROTOCOL,
    FRAME_PROTOCOL,
    RemoteCameraService,
    _encode_frame_packet,
    _read_frame_packet,
)

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
    "jpeg_quality": 14,
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


def device_status(*, session_active: bool) -> dict:
    return {
        "protocol": CAMERA_PROTOCOL,
        "stream_protocol": FRAME_PROTOCOL,
        "camera_ready": True,
        "session_active": session_active,
        "stream_client_active": False,
        "settings": SETTINGS,
    }


class ChunkedFrameStream:
    def __init__(self, packets: bytes, *, chunk_size: int = 3) -> None:
        self.buffer = bytearray(packets)
        self.chunk_size = chunk_size
        self.closed = False

    def read(self, size: int) -> bytes:
        if self.closed or not self.buffer:
            return b""
        count = min(size, self.chunk_size, len(self.buffer))
        result = bytes(self.buffer[:count])
        del self.buffer[:count]
        return result

    def close(self) -> None:
        self.closed = True


class RepeatingTcpStream:
    def __init__(self, *, end_after_frames: int | None = None) -> None:
        self.closed = False
        self.frames = 0
        self.end_after_frames = end_after_frames
        self.pending = bytearray()

    def read(self, size: int) -> bytes:
        if self.closed:
            return b""
        if not self.pending:
            if self.end_after_frames is not None and self.frames >= self.end_after_frames:
                return b""
            self.frames += 1
            time.sleep(0.01)
            self.pending.extend(
                _encode_frame_packet(
                    JPEG_1X1,
                    sequence=self.frames,
                    source_uptime_ms=self.frames * 10,
                )
            )
        count = min(size, len(self.pending))
        result = bytes(self.pending[:count])
        del self.pending[:count]
        return result

    def close(self) -> None:
        self.closed = True


def main() -> int:
    # Fixed binary framing must survive arbitrary TCP fragmentation.
    stream = ChunkedFrameStream(
        _encode_frame_packet(JPEG_1X1, sequence=7, source_uptime_ms=1234),
        chunk_size=2,
    )
    packet = _read_frame_packet(stream)
    assert packet is not None
    assert packet.content == JPEG_1X1
    assert packet.sequence == 7
    assert packet.source_uptime_ms == 1234
    print("[PASS] V036 length-prefixed JPEG framing handles arbitrary TCP segmentation")

    calls: list[tuple[str, str, dict[str, str] | None]] = []
    status_calls = 0
    opened_streams = 0
    service = RemoteCameraService()

    def request_json(host: str, path: str, method: str, query: dict[str, str] | None) -> dict:
        nonlocal status_calls
        calls.append((method, path, query))
        if path == "/status":
            status_calls += 1
            # Initial Connect and first recovery probe both see idle.
            return device_status(session_active=False)
        if path == "/config":
            assert query is not None
            assert query["stream_fps"] == "15"
            return device_status(session_active=False)
        if path == "/start":
            return device_status(session_active=True)
        if path == "/stop":
            return device_status(session_active=False)
        raise AssertionError(path)

    def open_stream(host: str):
        nonlocal opened_streams
        opened_streams += 1
        if opened_streams == 1:
            return RepeatingTcpStream(end_after_frames=1)
        return RepeatingTcpStream()

    service._json_requester = request_json
    service._stream_opener = open_stream

    connected = service.connect(host="192.168.68.57", source_id="esp32_cam_test")
    assert connected["configured"] is True
    assert connected["streaming"] is False
    assert opened_streams == 0
    assert [item[:2] for item in calls] == [("GET", "/status")]
    print("[PASS] Connect remains control-only with zero image transfer")

    started = service.start_stream(settings=SETTINGS, target_fps=15)
    assert started["transport"] == "tcp_jpeg"
    assert started["streaming"] is True
    assert [item[:2] for item in calls[1:4]] == [
        ("POST", "/stop"),
        ("POST", "/config"),
        ("POST", "/start"),
    ]

    first = service.wait_for_new_frame(-1, timeout_seconds=0.5)
    assert first is not None and first.source_id == "esp32_cam_test"
    print("[PASS] browser relay still wakes immediately from the shared PC frame slot")

    # First fake stream ends. V036 probes status, sees lost session, re-arms it,
    # and reconnects the raw TCP frame socket automatically.
    deadline = time.time() + 1.5
    recovered = None
    while time.time() < deadline:
        recovered = service.status()
        if recovered["session_recoveries"] >= 1 and recovered["stream_connected"] and opened_streams >= 2:
            break
        time.sleep(0.03)

    assert recovered is not None
    assert recovered["session_recoveries"] >= 1
    assert recovered["stream_reconnects"] >= 1
    assert opened_streams >= 2
    assert status_calls >= 2
    print("[PASS] dropped/rebooted V036 ESP session is automatically re-armed and reconnected")

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
    print("[PASS] simulation suspends physical transport and resumes afterward")

    stopped = service.stop_stream()
    count_at_stop = stopped["successful_fetches"]
    time.sleep(0.05)
    assert service.status()["successful_fetches"] == count_at_stop
    assert stopped["worker_running"] is False
    assert stopped["stream_connected"] is False
    print("[PASS] Stop Stream closes the active TCP reader with bounded shutdown")

    service.disconnect()
    assert service.status()["configured"] is False
    print("[PASS] Disconnect clears V036 remote state safely")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
