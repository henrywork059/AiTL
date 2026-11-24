from __future__ import annotations

from pathlib import Path
import sys
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "pc-studio" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services import remote_camera


def check(service, frames, mode):
    stop = service._stop_event
    stream = Mock()
    replacement = Mock()
    service._host = '192.168.1.87'
    service._source_id = 'esp32_test'
    service._streaming_requested = True
    service._active_stream = None
    service._stream_connected = False
    service._device_reachable = False
    service._last_stream_connected_at_ms = None
    service._last_error = 'prior error'
    service._stream_reconnects = 0
    service._record_stream_failure = Mock()
    service._recover_esp_session_if_needed = Mock()
    service._reconnect_backoff_seconds = Mock(return_value=0)
    consumed = []
    calls = 0

    def opener(host):
        nonlocal calls
        calls += 1
        if mode == 'stop':
            stop.set()
            service._streaming_requested = False
        elif mode == 'restart':
            stop.set()
            service._stop_event = Event()
            service._active_stream = replacement
            service._stream_connected = True
            service._device_reachable = True
            service._last_stream_connected_at_ms = 123
            service._last_error = 'replacement status'
        elif mode == 'simulation':
            frames.simulation_enabled = True
        return stream

    def consume(**kw):
        consumed.append(kw['stream'])
        assert service._active_stream is stream
        assert service._stream_connected is True
        if mode == 'reconnect' and calls == 1:
            return 'stream_ended'
        stop.set()
        return 'stopped'

    service._stream_opener = opener
    service._consume_tcp_stream = consume

    # End the simulation-wait loop deterministically without sleeps.
    def wait(timeout=None):
        if mode == 'simulation':
            stop.set()
        return stop.is_set()

    stop.wait = wait
    service._run(stop)
    if mode in ('stop', 'restart', 'simulation'):
        assert not consumed, (mode, 'cancelled socket entered receiver')
        assert calls == 1
        stream.close.assert_called_once()
        service._record_stream_failure.assert_not_called()
        service._recover_esp_session_if_needed.assert_not_called()
        if mode == 'restart':
            assert service._active_stream is replacement and service._stream_connected
            assert service._last_stream_connected_at_ms == 123
            assert service._last_error == 'replacement status'
            replacement.close.assert_not_called()
        else:
            assert service._active_stream is None and not service._stream_connected
            assert not service._device_reachable
            assert service._last_stream_connected_at_ms is None
            assert service._last_error == 'prior error'
    else:
        expected = 2 if mode == 'reconnect' else 1
        assert len(consumed) == calls == expected
        assert stream.close.call_count == expected
        assert service._active_stream is None and not service._stream_connected
        assert service._device_reachable and service._last_error is None
        assert service._record_stream_failure.call_count == expected - 1
        assert service._recover_esp_session_if_needed.call_count == expected - 1
        assert service._stream_reconnects == expected - 1


def main() -> int:
    for mode in ('stop', 'restart', 'simulation', 'normal', 'reconnect'):
        service = remote_camera.RemoteCameraService()
        frames = SimpleNamespace(simulation_enabled=False)
        with patch.object(remote_camera, 'camera_frame_service', frames):
            check(service, frames, mode)
        print(f'[PASS] socket-open boundary: {mode}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
