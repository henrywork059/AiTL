from __future__ import annotations

from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "pc-studio" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.exceptions import AppError
from app.services.remote_camera import (
    CAMERA_PROTOCOL,
    FRAME_PROTOCOL,
    RemoteCameraService,
    _encode_frame_packet,
    normalize_private_lan_ipv4,
)

JPEG_1X1 = b"\xff\xd8\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xd9"

SETTINGS = {
    "frame_size": "VGA", "jpeg_quality": 14, "brightness": 0, "contrast": 0,
    "saturation": 0, "special_effect": 0, "awb": True, "awb_gain": True,
    "wb_mode": 0, "aec": True, "aec2": False, "ae_level": 0,
    "aec_value": 300, "agc": True, "agc_gain": 0, "gainceiling": 0,
    "bpc": False, "wpc": True, "raw_gma": True, "lenc": True,
    "hmirror": False, "vflip": False, "dcw": True, "colorbar": False,
}


def status(active: bool) -> dict:
    return {
        "protocol": CAMERA_PROTOCOL,
        "stream_protocol": FRAME_PROTOCOL,
        "camera_ready": True,
        "session_active": active,
        "settings": SETTINGS,
    }


class RepeatingStream:
    def __init__(self) -> None:
        self.pending = bytearray()
        self.sequence = 0
        self.closed = False

    def read(self, size: int) -> bytes:
        if self.closed:
            return b""
        if not self.pending:
            self.sequence += 1
            self.pending.extend(_encode_frame_packet(JPEG_1X1, sequence=self.sequence))
            time.sleep(0.01)
        take = min(size, len(self.pending))
        result = bytes(self.pending[:take])
        del self.pending[:take]
        return result

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
    print("[PASS] remote camera host validation remains private-LAN IPv4 only")

    calls: list[tuple[str, str, dict[str, str] | None]] = []
    service = RemoteCameraService()

    def request_json(host: str, path: str, method: str, query: dict[str, str] | None) -> dict:
        calls.append((method, path, query))
        if path == "/status": return status(False)
        if path == "/config": return status(False)
        if path == "/start": return status(True)
        if path == "/stop": return status(False)
        raise AssertionError(path)

    service._json_requester = request_json
    service._stream_opener = lambda host: RepeatingStream()

    service.connect(host="192.168.1.87", source_id="esp32_cam_compat")
    assert service.status()["successful_fetches"] == 0

    # Older V033-V035 API callers using fetch_interval_ms remain accepted.
    started = service.start_stream(settings=SETTINGS, fetch_interval_ms=100)
    assert started["target_fps"] == 10
    assert calls[2][2]["stream_fps"] == "10"

    deadline = time.time() + 0.5
    while time.time() < deadline and service.status()["successful_fetches"] < 1:
        time.sleep(0.02)
    assert service.status()["successful_fetches"] >= 1
    print("[PASS] legacy start-call interval still maps to V036 target FPS")

    service.stop()
    assert service.status()["worker_running"] is False
    print("[PASS] V036 TCP transport shutdown remains bounded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
