from __future__ import annotations

from io import BytesIO
from pathlib import Path
import sys
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "pc-studio" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services import remote_camera as rc

HOST = "192.168.1.87"


def failure():
    return rc.AppError(rc.ErrorCode.CAMERA_NOT_CONNECTED, "old error", status_code=502)


def fresh():
    service = rc.RemoteCameraService()
    service._host = HOST
    service._settings = {"jpeg_quality": 12}
    service._streaming_requested = True
    service._settings_query = Mock(return_value={"jpeg_quality": "12"})
    return service


def retire(service):
    service._stop_event.set()
    service._stop_event = Event()
    service._thread = Mock()
    service._active_stream = Mock()
    service._stream_connected = True
    service._device_reachable = True
    service._device_status = {"replacement": True}
    service._settings = {"jpeg_quality": 20}
    service._last_error = "replacement marker"
    service._failed_fetches = 7
    service._consecutive_failures = 3
    service._stream_reconnects = 4
    service._session_recoveries = 5
    service._current_backoff_ms = 123
    service._successful_fetches = 8
    return service._active_stream


def assert_replacement(service, replacement):
    assert service._active_stream is replacement
    replacement.close.assert_not_called()
    assert service._stream_connected and service._device_reachable
    assert service._device_status == {"replacement": True}
    assert service._settings == {"jpeg_quality": 20}
    assert service._last_error == "replacement marker"
    assert (service._failed_fetches, service._consecutive_failures) == (7, 3)
    assert (service._stream_reconnects, service._session_recoveries) == (4, 5)
    assert service._current_backoff_ms == 123
    assert service._successful_fetches == 8


def late_transport(mode):
    service = fresh()
    stop = service._stop_event
    stream = Mock()
    replacement = None

    def late():
        nonlocal replacement
        replacement = retire(service)
        if mode == "oserror":
            raise OSError("retired")
        if mode == "eof":
            return "stream_ended"
        raise failure()

    def opener(host):
        return late() if mode in {"open", "oserror"} else stream

    service._stream_opener = opener
    service._consume_tcp_stream = lambda **kw: late()
    service._request_control = Mock()
    service._run(stop)
    assert_replacement(service, replacement)
    service._request_control.assert_not_called()
    if mode in {"read", "eof"}:
        stream.close.assert_called_once()


def late_join():
    service = fresh()
    stream = Mock()
    thread = Mock()
    service._thread = thread
    service._active_stream = stream
    service._stream_connected = True
    replacement = None

    def join(timeout):
        nonlocal replacement
        assert timeout == 2.5
        replacement = retire(service)

    thread.join.side_effect = join
    service._stop_worker()
    thread.join.assert_called_once_with(timeout=2.5)
    stream.close.assert_called_once()
    assert_replacement(service, replacement)


def recovery(mode):
    service = fresh()
    stop = service._stop_event
    replacement = None
    calls = []
    opened = 0

    def opener(host):
        nonlocal opened
        opened += 1
        if opened == 1:
            raise failure()
        return Mock()

    def control(host, path, method, query):
        nonlocal replacement
        calls.append(path)
        if path == mode or (mode == "status_error" and path == "/status"):
            replacement = retire(service)
            if mode == "status_error":
                raise failure()
        return {
            "protocol": rc.CAMERA_PROTOCOL,
            "stream_protocol": rc.FRAME_PROTOCOL,
            "camera_ready": True,
            "session_active": path == "/start",
            "settings": {"jpeg_quality": 12},
        }

    def consume(**kw):
        stop.set()
        return "stopped"

    service._stream_opener = opener
    service._request_control = control
    service._consume_tcp_stream = consume
    stop.wait = lambda timeout=None: stop.is_set()
    service._run(stop)

    if mode == "normal":
        assert calls == ["/status", "/config", "/start"]
        assert opened == 2 and service._session_recoveries == 1
        assert service._stream_reconnects == 1
        assert service._device_reachable and service._last_error is None
    else:
        expected = {
            "/status": ["/status"],
            "/config": ["/status", "/config"],
            "/start": ["/status", "/config", "/start"],
            "status_error": ["/status"],
        }
        assert calls == expected[mode], calls
        assert opened == 1
        assert_replacement(service, replacement)


def late_sink():
    service = fresh()
    stop = service._stop_event
    replacement = None

    def sink(source_id, packet):
        nonlocal replacement
        replacement = retire(service)
        return 42

    service._frame_sink = sink
    packet = rc._FramePacket(sequence=1, source_uptime_ms=10, content=b"\xff\xd8\xff\xd9")
    with patch.object(rc, "_read_frame_packet", return_value=packet):
        assert service._consume_tcp_stream(
            stream=BytesIO(), source_id="esp32_test", stop_event=stop
        ) == "stopped"
    assert_replacement(service, replacement)
    assert service._last_frame_number is None


def main():
    cases = [(f"late {mode}", lambda mode=mode: late_transport(mode))
             for mode in ("open", "oserror", "read", "eof")]
    cases.append(("late join", late_join))
    cases.extend((f"recovery {mode}", lambda mode=mode: recovery(mode))
                 for mode in ("/status", "/config", "/start", "status_error", "normal"))
    cases.append(("late frame sink", late_sink))
    with patch.object(rc, "camera_frame_service", SimpleNamespace(simulation_enabled=False)):
        for name, check in cases:
            check()
            print(f"[PASS] {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
