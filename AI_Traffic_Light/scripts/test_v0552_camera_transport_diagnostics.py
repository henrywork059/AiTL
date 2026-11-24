from __future__ import annotations

from io import BytesIO
from pathlib import Path
import sys
from threading import Event
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "pc-studio" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services import remote_camera as rc

JPEG = bytes.fromhex("ffd8") + b"payload" + bytes.fromhex("ffd9")


def packet(sequence: int, uptime: int) -> rc._FramePacket:
    return rc._FramePacket(sequence=sequence, source_uptime_ms=uptime, content=JPEG)


def recording():
    seen = []
    service = rc.RemoteCameraService(frame_sink=lambda source, frame: (seen.append((source, frame.sequence)) or len(seen)))
    service._host = "192.168.1.87"
    service._source_id = "camera_a"
    service._streaming_requested = True
    service._stream_connected = True
    return service, seen


def test_packets():
    service, seen = recording()
    data = b"".join(rc._encode_frame_packet(JPEG, sequence=n, source_uptime_ms=t)
                    for n, t in [(1, 100), (1, 100), (3, 300), (2, 20), (4, 100)])
    stream = BytesIO(data)
    with patch.object(rc.time, "time", side_effect=[10.0, 10.1, 10.2, 10.3]), patch.object(
        rc.time, "monotonic", side_effect=[1.0, 1.1, 1.2, 1.3]
    ):
        assert service._consume_tcp_stream(stream=stream, source_id="camera_a", stop_event=service._stop_event) == "stream_ended"
    assert seen == [("camera_a", 1), ("camera_a", 3), ("camera_a", 2), ("camera_a", 4)]
    assert service._repeated_source_frames == 1
    assert service._source_sequence_gaps == 2  # 1 -> 3 misses 2; reset 2 -> 4 misses 3
    assert service._source_sequence_resets == 1
    assert service._successful_fetches == 4
    assert abs(service._last_frame_interval_ms - 100.0) < 0.001
    assert abs(service._measured_fps - 10.0) < 0.001


def test_clock_and_stale():
    service, _ = recording()
    with patch.object(rc.time, "time", side_effect=[100.0, 50.0]), patch.object(
        rc.time, "monotonic", side_effect=[10.0, 10.1]
    ):
        service._record_frame(packet(1, 20), 1)
        service._record_frame(packet(2, 40), 2)
    assert abs(service._last_frame_interval_ms - 100.0) < 0.001
    assert abs(service._measured_fps - 10.0) < 0.001
    with patch.object(rc.time, "time", return_value=60.0):
        status = service.status()
    assert status["frame_age_ms"] == 10000 and status["frame_stale"]
    assert status["measured_fps"] == 0
    service._stream_connected = False
    with patch.object(rc.time, "time", return_value=50.1):
        status = service.status()
    assert status["frame_stale"] and status["measured_fps"] == 0


def test_retirement():
    service, seen = recording()
    retired = service._stop_event
    service._stop_event = Event()
    service._record_frame(packet(999, 999), 1, stop_event=retired)
    assert service._successful_fetches == 0
    assert service._last_remote_sequence is None
    assert seen == []
    # Independent physical camera instances cannot share transport counters.
    second, _ = recording()
    second._record_frame(packet(4, 100), 1)
    assert second._successful_fetches == 1
    assert service._successful_fetches == 0


def main():
    test_packets()
    test_clock_and_stale()
    test_retirement()
    print("[PASS] V0552 diagnostics: duplicates, gaps, reset, clocks, stale/retired and independent camera")


if __name__ == "__main__":
    main()
