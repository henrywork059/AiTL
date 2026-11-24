"""Integration regression: derived capabilities do not alter legacy camera profiles."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "pc-studio" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.remote_camera_manager import RemoteCameraManager, DEFAULT_CAMERA_SETTINGS  # noqa: E402


class FakeSession:
    calls = 0

    def __init__(self, *, frame_sink):
        self.frame_sink = frame_sink
        self.host = None
        self.source_id = None
        self.streaming_requested = False
        self.stream_connected = False
        self.error = None

    def connect(self, *, host, source_id):
        self.host = host
        self.source_id = source_id
        FakeSession.calls += 1
        return self.status()

    def cancel_pending_frames(self):
        self.streaming_requested = False
        self.stream_connected = False

    def start_stream(self, *, settings, target_fps, fetch_interval_ms=None):
        del settings, target_fps, fetch_interval_ms
        self.streaming_requested = True
        self.stream_connected = True
        FakeSession.calls += 1
        return self.status()

    def stop_stream(self, *, best_effort=False):
        del best_effort
        self.streaming_requested = False
        self.stream_connected = False
        return self.status()

    def disconnect(self):
        self.host = None
        self.streaming_requested = False
        self.stream_connected = False
        return self.status()

    def status(self, *, refresh_device=False):
        del refresh_device
        return {
            "configured": self.host is not None,
            "device_reachable": self.host is not None,
            "streaming": self.streaming_requested,
            "stream_connected": self.stream_connected,
            "paused_for_simulation": False,
            "last_error": self.error,
        }


def test_legacy_load_and_roundtrip() -> None:
    with TemporaryDirectory() as temporary:
        registry = Path(temporary) / "remote_cameras.json"
        legacy = {
            "schema_version": 1,
            "active_source_id": "cam_a",
            "cameras": [
                {"source_id": "cam_a", "host": "192.168.50.81",
                 "target_fps": 15, "settings": {"frame_size": "QVGA", "jpeg_quality": 24}, "last_used_ms": 100},
                {"source_id": "cam_b", "kind": "esp32", "host": "192.168.50.82",
                 "target_fps": 20, "settings": {"frame_size": "VGA", "jpeg_quality": 19}, "last_used_ms": 80},
                {"source_id": "simulation_camera", "kind": "simulation", "host": "",
                 "target_fps": 2, "settings": {}, "last_used_ms": 20},
            ],
        }
        registry.write_text(json.dumps(legacy), encoding="utf-8")
        before = registry.read_bytes()
        FakeSession.calls = 0
        manager = RemoteCameraManager(registry_path=registry, session_factory=FakeSession)
        current = manager.status()
        assert current["camera_count"] == 3
        assert current["active_source_id"] == "cam_a"
        assert current["device_contract"]["source_id"] == "cam_a"
        assert FakeSession.calls == 0
        assert manager._sessions == {}, "Status projection must not create sessions"
        assert registry.read_bytes() == before, "Capability discovery must not persist or migrate profiles"
        cameras = {item["source_id"]: item for item in current["cameras"]}
        for source in ("cam_a", "cam_b"):
            cap = cameras[source]["device_contract"]
            assert cap["source_id"] == source
            assert cap["health"]["state"] == "not_connected"
            assert cap["capabilities"]["camera_input"]["available"] is False
            assert cap["physical_output_allowed"] is False
            assert all(cap["capabilities"][kind]["support"] == "unavailable"
                       for kind in ("lighting_output", "speaker_output"))
        simulation = cameras["simulation_camera"]["device_contract"]
        assert simulation["device_type"] == "simulation_camera"
        assert simulation["capabilities"]["camera_input"]["support"] == "simulation-only"
        assert simulation["capabilities"]["camera_input"]["available"] is False

        manager.connect(host="192.168.50.81", source_id="cam_a")
        connected = manager.status()
        assert connected["device_contract"]["health"]["state"] == "connected"
        manager.start_stream(settings=DEFAULT_CAMERA_SETTINGS, target_fps=15)
        waiting = manager.status()["device_contract"]
        assert waiting["health"]["state"] == "waiting_for_frame"
        assert waiting["capabilities"]["camera_input"]["available"] is False
        # Original source timestamp is owned by the camera manager cache, not
        # synthesized by the capability projection or selected-frame replay.
        with manager._lock:
            manager._latest_frames["cam_a"] = SimpleNamespace(received_at_ms=manager._now_ms())
        streaming = manager.status()["device_contract"]
        assert streaming["health"]["state"] == "streaming"
        assert streaming["health"]["frame_fresh"] is True
        assert streaming["capabilities"]["camera_input"]["available"] is True
        manager.select("cam_b")
        selected = manager.status()
        assert selected["device_contract"]["source_id"] == "cam_b"
        assert selected["device_contract"]["health"]["state"] == "not_connected"
        assert next(x for x in selected["cameras"] if x["source_id"] == "cam_a")["device_contract"]["health"]["state"] == "streaming"

        saved = json.loads(registry.read_text(encoding="utf-8"))
        assert saved["schema_version"] == 1
        assert set(saved) == {"schema_version", "active_source_id", "cameras"}
        assert saved["active_source_id"] == "cam_b"
        assert all("device_contract" not in x and "capabilities" not in x and "health" not in x
                   for x in saved["cameras"])
        assert {item["source_id"]: item["target_fps"] for item in saved["cameras"]} == {
            "cam_a": 15, "cam_b": 20, "simulation_camera": 2,
        }
        reloaded = RemoteCameraManager(registry_path=registry, session_factory=FakeSession)
        second = reloaded.status()
        assert second["device_contract"]["source_id"] == "cam_b"
        assert second["device_contract"]["health"]["state"] == "not_connected"
        assert {p["source_id"]: p["settings"]["jpeg_quality"] for p in second["cameras"]}["cam_b"] == 19
        assert not reloaded._sessions
        manager.stop()


def main() -> int:
    test_legacy_load_and_roundtrip()
    print("[PASS] V0554 legacy V1 profiles, capability-health projection, source independence and no commands on discovery")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
