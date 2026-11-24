from __future__ import annotations

from io import BytesIO
from pathlib import Path
import sys
from threading import Event, RLock
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "pc-studio" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services import remote_camera


def main() -> int:
    packet = remote_camera._FramePacket(
        sequence=1, source_uptime_ms=10, content=b"\xff\xd8\xff\xd9"
    )
    for mode in ("stop", "simulation", "normal", "eof", "stop_eof", "simulation_eof"):
        service = remote_camera.RemoteCameraService.__new__(remote_camera.RemoteCameraService)
        service._lock = RLock()
        service._stream_bytes_received = 0
        service._store_packet = Mock()
        stop = Event()
        frames = SimpleNamespace(simulation_enabled=False)
        calls = 0

        def read_packet(stream):
            nonlocal calls
            calls += 1
            if mode.startswith("stop"):
                stop.set()
            elif mode.startswith("simulation"):
                frames.simulation_enabled = True
            if mode.endswith("eof") or calls > 1:
                return None
            return packet

        with patch.object(remote_camera, "camera_frame_service", frames), patch.object(
            remote_camera, "_read_frame_packet", read_packet
        ):
            outcome = service._consume_tcp_stream(
                stream=BytesIO(), source_id="esp32_test", stop_event=stop
            )

        expected = (
            "stopped" if mode.startswith("stop")
            else "paused_for_simulation" if mode.startswith("simulation")
            else "stream_ended"
        )
        assert outcome == expected, (mode, outcome)
        if mode == "normal":
            service._store_packet.assert_called_once_with(source_id="esp32_test", packet=packet)
            assert service._stream_bytes_received == remote_camera.FRAME_HEADER.size + len(packet.content)
        else:
            service._store_packet.assert_not_called()
            assert service._stream_bytes_received == 0
        print(f"[PASS] receive-loop boundary: {mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
