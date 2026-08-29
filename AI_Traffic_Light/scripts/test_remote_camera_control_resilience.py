from __future__ import annotations

from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "pc-studio" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.services.remote_camera import (
    CAMERA_PROTOCOL,
    CONTROL_RETRY_ATTEMPTS,
    FRAME_PROTOCOL,
    RemoteCameraService,
)


def device_status(*, session_active: bool = False) -> dict:
    return {
        "protocol": CAMERA_PROTOCOL,
        "stream_protocol": FRAME_PROTOCOL,
        "camera_ready": True,
        "session_active": session_active,
        "settings": {},
    }


def transient_error() -> AppError:
    return AppError(
        ErrorCode.CAMERA_NOT_CONNECTED,
        "temporary ESP control timeout",
        status_code=502,
        details={"host": "192.168.68.54", "path": "/status", "reason": "timed out"},
    )


def main() -> int:
    # Physical R6 testing showed that the ESP can remain associated while a tiny
    # /status request occasionally times out around -72 to -74 dBm. Connect must
    # retry a fresh HTTP connection instead of exposing the first timeout as 502.
    service = RemoteCameraService()
    attempts = 0

    def flaky_requester(host: str, path: str, method: str, query: dict[str, str] | None) -> dict:
        nonlocal attempts
        if path == "/status":
            attempts += 1
            if attempts < CONTROL_RETRY_ATTEMPTS:
                raise transient_error()
            return device_status()
        if path == "/stop":
            return device_status()
        raise AssertionError(path)

    service._json_requester = flaky_requester
    connected = service.connect(host="192.168.68.54", source_id="esp32_cam_retry")
    assert connected["configured"] is True
    assert connected["device_reachable"] is True
    assert attempts == CONTROL_RETRY_ATTEMPTS
    service.disconnect()
    print("[PASS] transient ESP control timeouts are retried before Connect returns 502")

    # A real HTTP/protocol response must not be hidden behind retries. Only
    # transport-level failures with a reason field are retryable.
    deterministic = RemoteCameraService()
    deterministic_attempts = 0

    def http_failure(host: str, path: str, method: str, query: dict[str, str] | None) -> dict:
        nonlocal deterministic_attempts
        deterministic_attempts += 1
        raise AppError(
            ErrorCode.CAMERA_NOT_CONNECTED,
            "ESP returned HTTP 503",
            status_code=502,
            details={"host": host, "path": path, "http_status": 503},
        )

    deterministic._json_requester = http_failure
    try:
        deterministic.connect(host="192.168.68.54", source_id="esp32_cam_http_error")
    except AppError:
        pass
    else:
        raise AssertionError("deterministic HTTP failure should propagate")
    assert deterministic_attempts == 1
    print("[PASS] deterministic ESP HTTP/protocol errors are not blindly retried")

    # Frontend /remote/status polling and button actions are handled by separate
    # FastAPI threads. They must never issue overlapping requests to the ESP's
    # single-threaded WebServer.
    serialized = RemoteCameraService()
    state_lock = threading.Lock()
    active = 0
    max_active = 0
    calls = 0

    def slow_requester(host: str, path: str, method: str, query: dict[str, str] | None) -> dict:
        nonlocal active, max_active, calls
        with state_lock:
            active += 1
            calls += 1
            max_active = max(max_active, active)
        try:
            time.sleep(0.05)
            return device_status()
        finally:
            with state_lock:
                active -= 1

    serialized._json_requester = slow_requester
    threads = [
        threading.Thread(
            target=serialized._request_control,
            args=("192.168.68.54", "/status", "GET", None),
        )
        for _ in range(4)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=2.0)
        assert not thread.is_alive()

    assert calls == 4
    assert max_active == 1
    print("[PASS] concurrent PC status/button control traffic is serialized per ESP session")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
