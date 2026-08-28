from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import threading
import time

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "pc-studio" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.camera_frames import camera_frame_service  # noqa: E402
from app.services.remote_camera import _FramePacket  # noqa: E402
from app.services.remote_camera_manager import (  # noqa: E402
    DEFAULT_CAMERA_SETTINGS,
    MAX_SWITCH_CACHE_AGE_MS,
    RemoteCameraManager,
    _CachedPacket,
)


def jpeg(label: int) -> bytes:
    canvas = np.full((32, 48, 3), label, dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", canvas)
    assert ok
    return encoded.tobytes()


class FakeSession:
    def __init__(self, *, frame_sink):
        self.frame_sink = frame_sink
        self.host: str | None = None
        self.source_id: str | None = None
        self.streaming_requested = False
        self.reachable = False
        self.target_fps = 15
        self.settings: dict | None = None
        self.frames = 0

    def connect(self, *, host: str, source_id: str) -> dict:
        self.host = host
        self.source_id = source_id
        self.reachable = True
        return self.status()

    def start_stream(self, *, settings: dict, target_fps: int, fetch_interval_ms=None) -> dict:
        del fetch_interval_ms
        self.settings = dict(settings)
        self.target_fps = target_fps
        self.streaming_requested = True
        return self.status()

    def stop_stream(self, *, best_effort: bool = False) -> dict:
        del best_effort
        self.streaming_requested = False
        return self.status()

    def disconnect(self) -> dict:
        self.streaming_requested = False
        self.reachable = False
        self.host = None
        return self.status()

    def emit(self, sequence: int, content: bytes) -> int:
        assert self.source_id is not None
        self.frames += 1
        return self.frame_sink(
            self.source_id,
            _FramePacket(sequence=sequence, source_uptime_ms=sequence * 10, content=content),
        )

    def status(self, *, refresh_device: bool = False) -> dict:
        del refresh_device
        return {
            "configured": self.host is not None,
            "device_reachable": self.reachable,
            "worker_running": self.streaming_requested,
            "streaming": self.streaming_requested,
            "stream_connected": self.streaming_requested,
            "paused_for_simulation": False,
            "transport": "tcp_jpeg" if self.streaming_requested else "idle",
            "stream_protocol": "aitl-tcp-jpeg-v1" if self.streaming_requested else None,
            "host": self.host,
            "source_id": self.source_id,
            "status_url": None,
            "capture_url": None,
            "stream_url": None,
            "target_fps": self.target_fps,
            "fetch_interval_ms": round(1000 / max(1, self.target_fps)),
            "measured_fps": float(self.target_fps) if self.streaming_requested else 0.0,
            "last_frame_interval_ms": None,
            "stream_reconnects": 0,
            "session_recoveries": 0,
            "consecutive_failures": 0,
            "reconnect_backoff_ms": 0,
            "stream_bytes_received": 0,
            "dropped_stale_frames": 0,
            "source_sequence_gaps": 0,
            "last_remote_sequence": None,
            "last_source_uptime_ms": None,
            "connected_at_ms": 1 if self.host else None,
            "stream_started_at_ms": 1 if self.streaming_requested else None,
            "last_stream_connected_at_ms": None,
            "last_recovery_at_ms": None,
            "last_probe_at_ms": None,
            "last_attempt_at_ms": None,
            "last_success_at_ms": 1 if self.frames else None,
            "last_http_status": None,
            "last_frame_number": None,
            "last_frame_bytes": 0,
            "successful_fetches": self.frames,
            "failed_fetches": 0,
            "last_error": None,
            "settings": dict(self.settings) if self.settings else None,
            "device": {},
            "control_sequence": [],
            "prototype_only": True,
        }


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        registry = Path(temporary) / "remote_cameras.json"
        manager = RemoteCameraManager(registry_path=registry, session_factory=FakeSession)
        settings_a = dict(DEFAULT_CAMERA_SETTINGS)
        settings_b = {**DEFAULT_CAMERA_SETTINGS, "brightness": 1, "jpeg_quality": 16}

        manager.save_profile(host="192.168.50.81", source_id="cam_a", settings=settings_a, target_fps=15)
        manager.save_profile(host="192.168.50.82", source_id="cam_b", settings=settings_b, target_fps=20)
        assert manager.status()["camera_count"] == 2

        manager.select("cam_a")
        manager.connect(host="192.168.50.81", source_id="cam_a")
        manager.start_stream(settings=settings_a, target_fps=15)
        session_a = manager._sessions["cam_a"]
        session_a.emit(1, jpeg(60))
        assert camera_frame_service.latest_frame().source_id == "cam_a"

        manager.select("cam_b")
        manager.connect(host="192.168.50.82", source_id="cam_b")
        manager.start_stream(settings=settings_b, target_fps=20)
        session_b = manager._sessions["cam_b"]
        session_b.emit(1, jpeg(180))
        assert camera_frame_service.latest_frame().source_id == "cam_b"

        # A keeps receiving in the background but must not replace selected B.
        session_a.emit(2, jpeg(80))
        assert camera_frame_service.latest_frame().source_id == "cam_b"

        # Force an in-flight A publication to overlap a switch to B. Selection and
        # shared-frame publication must serialize so A cannot overwrite B afterward.
        manager.select("cam_a")
        original_store = camera_frame_service.store_upload
        publish_entered = threading.Event()
        release_publish = threading.Event()

        def blocking_store(*, source_id: str, content_type: str, content: bytes):
            if source_id == "cam_a" and threading.current_thread().name == "race-cam-a":
                publish_entered.set()
                assert release_publish.wait(1.0)
            return original_store(source_id=source_id, content_type=content_type, content=content)

        camera_frame_service.store_upload = blocking_store  # type: ignore[method-assign]
        emitter = threading.Thread(target=lambda: session_a.emit(3, jpeg(90)), name="race-cam-a")
        selector = threading.Thread(target=lambda: manager.select("cam_b"), name="race-select-b")
        emitter.start()
        assert publish_entered.wait(1.0)
        selector.start()
        time.sleep(0.03)
        assert selector.is_alive(), "camera selection should wait for the in-flight publication boundary"
        release_publish.set()
        emitter.join(1.0)
        selector.join(1.0)
        camera_frame_service.store_upload = original_store  # type: ignore[method-assign]
        assert not emitter.is_alive() and not selector.is_alive()
        assert camera_frame_service.latest_frame().source_id == "cam_b"

        # Selecting A publishes its cached newest frame immediately.
        manager.select("cam_a")
        assert camera_frame_service.latest_frame().source_id == "cam_a"

        # At normal video rates, the promotion window scales to only a few
        # frame periods rather than accepting the full absolute 1.5 s cap.
        recent_b = manager._latest_packets["cam_b"]
        manager._latest_packets["cam_b"] = _CachedPacket(
            packet=recent_b.packet,
            received_at_ms=manager._now_ms() - 800,
        )
        manager.select("cam_b")
        assert camera_frame_service.latest_frame() is None
        session_b.emit(2, jpeg(190))
        assert camera_frame_service.latest_frame().source_id == "cam_b"
        manager.select("cam_a")

        # A stale cache must never be re-stamped as a fresh selected frame.
        stale_b = manager._latest_packets["cam_b"]
        manager._latest_packets["cam_b"] = _CachedPacket(
            packet=stale_b.packet,
            received_at_ms=manager._now_ms() - MAX_SWITCH_CACHE_AGE_MS - 1,
        )
        manager.select("cam_b")
        assert camera_frame_service.latest_frame() is None
        session_b.emit(3, jpeg(191))
        assert camera_frame_service.latest_frame().source_id == "cam_b"

        # Simulation owns the shared frame while active. On return to physical mode,
        # only a recent selected-camera cache may be restored.
        camera_frame_service.set_simulation(True)
        manager.sync_after_simulation_change()
        assert camera_frame_service.latest_frame().source_id == "simulation_camera"
        camera_frame_service.set_simulation(False)
        manager.sync_after_simulation_change()
        assert camera_frame_service.latest_frame().source_id == "cam_b"

        # Deleting an unrelated saved profile must not disturb the selected frame.
        manager.save_profile(host="192.168.50.90", source_id="cam_temp", settings=settings_a, target_fps=10, select=False)
        selected_before_delete = camera_frame_service.latest_frame().frame_number
        manager.delete_profile("cam_temp")
        selected_after_delete = camera_frame_service.latest_frame()
        assert selected_after_delete is not None
        assert selected_after_delete.source_id == "cam_b"
        assert selected_after_delete.frame_number == selected_before_delete

        # Changing the IP of the selected source invalidates its old-device cache.
        manager.save_profile(
            host="192.168.50.83",
            source_id="cam_b",
            settings=settings_b,
            target_fps=20,
        )
        assert camera_frame_service.latest_frame() is None
        assert "cam_b" not in manager._latest_packets
        manager.connect(host="192.168.50.83", source_id="cam_b")
        manager.start_stream(settings=settings_b, target_fps=20)
        replacement_session_b = manager._sessions["cam_b"]
        assert replacement_session_b is not session_b

        # A late frame from the retired old-IP worker must be rejected even after
        # the same source ID has been connected to a replacement ESP/session.
        session_b.emit(3, jpeg(199))
        assert camera_frame_service.latest_frame() is None
        replacement_session_b.emit(1, jpeg(200))
        assert camera_frame_service.latest_frame().source_id == "cam_b"

        manager.select("cam_a")

        # Stop only selected A. B remains independently streaming.
        manager.stop_stream()
        assert not session_a.streaming_requested
        assert replacement_session_b.streaming_requested

        # Legacy V033-V035 fetch_interval_ms callers must persist/report the
        # effective mapped FPS through the manager, not the default 15 FPS.
        compat_registry = Path(temporary) / "remote_cameras_compat.json"
        compat = RemoteCameraManager(registry_path=compat_registry, session_factory=FakeSession)
        compat.save_profile(host="192.168.50.91", source_id="cam_compat", settings=settings_a, target_fps=15)
        compat.connect(host="192.168.50.91", source_id="cam_compat")
        compat.start_stream(settings=settings_a, fetch_interval_ms=100)
        compat_status = compat.status()
        assert compat_status["target_fps"] == 10
        assert compat_status["cameras"][0]["target_fps"] == 10
        compat.stop()

        reloaded = RemoteCameraManager(registry_path=registry, session_factory=FakeSession)
        status = reloaded.status()
        assert status["camera_count"] == 2
        assert status["active_source_id"] == "cam_a"
        profiles = {item["source_id"]: item for item in status["cameras"]}
        assert profiles["cam_b"]["host"] == "192.168.50.83"
        assert profiles["cam_b"]["target_fps"] == 20
        assert profiles["cam_b"]["settings"]["brightness"] == 1

        # FastAPI shutdown hook equivalent must disconnect every session, not only selected.
        assert session_a.reachable
        assert replacement_session_b.reachable
        manager.stop()
        assert not session_a.reachable
        assert not replacement_session_b.reachable

    print("[PASS] multiple ESP profiles persist IP/FPS/OV2640 settings")
    print("[PASS] independent ESP streams can run simultaneously")
    print("[PASS] inactive and in-flight old-source frames cannot overwrite the selected PC Studio source")
    print("[PASS] selecting a running ESP switches immediately to its fresh cached/latest frame")
    print("[PASS] simulation transitions preserve one unambiguous selected physical source")
    print("[PASS] deleting an unrelated saved camera does not disturb the active frame")
    print("[PASS] stale caches and retired old-IP session frames are blocked during source switches")
    print("[PASS] legacy fetch_interval_ms callers persist/report their effective mapped FPS")
    print("[PASS] stopping one selected ESP leaves other streams running")
    print("[PASS] manager shutdown disconnects all ESP sessions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
