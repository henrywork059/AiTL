"""Shared observation contract through actual camera producer and cache paths."""
from pathlib import Path
import sys
import tempfile
from dataclasses import FrozenInstanceError
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/pc-studio/backend"))
from app.services.camera_frames import CameraFrameService
from app.services import remote_camera_manager as rcm
from app.services.observation_identity import ObservationIdentity
from test_remote_camera_multi import FakeSession, jpeg


def main():
    frames = CameraFrameService()
    now = [10000]
    with tempfile.TemporaryDirectory() as directory, patch.object(rcm, "camera_frame_service", frames):
        manager = rcm.RemoteCameraManager(
            registry_path=Path(directory) / "cameras.json", session_factory=FakeSession
        )
        manager._now_ms = lambda: now[0]
        settings = dict(rcm.DEFAULT_CAMERA_SETTINGS)
        for source, host in (("cam_a", "192.168.1.81"), ("cam_b", "192.168.1.82")):
            manager.save_profile(source_id=source, host=host)
            manager.connect(source_id=source, host=host)
            manager.start_stream(settings=settings, target_fps=15)
        a, b = manager._sessions["cam_a"], manager._sessions["cam_b"]
        a.emit(1, jpeg(60))
        b.emit(1, jpeg(90))
        physical, token = next((f, t) for f, t in manager.inference_inputs() if f.source_id == "cam_a")
        identity = physical.observation
        assert isinstance(identity, ObservationIdentity)
        assert identity.provenance == "esp32_stream"
        assert identity.session_generation == manager._session_generations["cam_a"]
        assert identity.source_epoch == manager._observation_epochs.get("cam_a", 0)
        assert identity.frame_key == ("cam_a", physical.frame_number, 10000)
        assert (identity.width, identity.height) == (physical.width, physical.height)
        assert set(physical.metadata()) == {
            "source_id", "content_type", "width", "height", "received_at_ms",
            "frame_number", "size_bytes", "origin",
        }
        try:
            identity.received_at_ms = 10001
        except FrozenInstanceError:
            pass
        else:
            raise AssertionError("Observation identity must be immutable")
        now[0] = 10050
        manager.select("cam_a")
        assert frames.latest_frame() is physical
        assert frames.latest_frame().observation == identity
        assert manager.observation_is_current("cam_a", token, 10000)
        assert manager.wait_for_new_frame(physical.frame_number, 0) is None
        print("[PASS] ESP provenance, original coordinates, metadata and cache identity")
        a.emit(2, jpeg(61))
        new = frames.latest_frame()
        assert new.observation.frame_key != identity.frame_key
        manager.stop_stream()
        assert frames.latest_frame() is None
        assert not manager.observation_is_current("cam_a", token, 10000)
        print("[PASS] distinct frame and retired source guard")
        frames.set_simulation(True)
        frames.configure_simulation(paused=True)
        sim = frames.simulation_frame_for("simulation_camera")
        mirror = frames.simulation_frame_for("simulation_camera_b")
        assert sim.observation.provenance == "simulation"
        assert sim.observation.mode_generation == frames.observation_mode_token[1]
        assert mirror.observation.mode_generation == sim.observation.mode_generation
        assert mirror.received_at_ms == sim.received_at_ms
        assert mirror.frame_number == sim.frame_number
        assert mirror.observation.frame_key != sim.observation.frame_key
        assert frames.simulation_frame_for("simulation_camera") is sim
        old_mode=frames.observation_mode_token
        frames.configure_simulation(density="busy")
        assert frames.observation_mode_token != old_mode
        assert frames.simulation_frame_for("simulation_camera").observation.mode_generation != sim.observation.mode_generation
        assert not manager.observation_is_current("simulation_camera", (old_mode,0),sim.received_at_ms)
        frames.set_simulation(False)
        assert frames.simulation_frame_for("simulation_camera") is None
        assert not manager.observation_is_current("cam_a", token, 10000)
        print("[PASS] synthetic mirrored source identity and mode retirement")
        uploaded = frames.store_upload(source_id="receiver", content_type="image/jpeg", content=jpeg(3))
        assert uploaded.observation.provenance == "external_upload"
        assert uploaded.observation.session_generation is None
        assert uploaded.observation.mode_generation == frames.observation_mode_token[1]
        assert uploaded.origin == "upload"
        print("[PASS] ordinary upload remains unverified external provenance")
        manager.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
