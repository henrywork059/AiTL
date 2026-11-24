"""Explicit retirement must invalidate only the affected source and late AI."""
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
from threading import Event
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/pc-studio/backend"))

from app.services.camera_frames import CameraFrameService
from app.services import remote_camera_manager as rcm
from app.services import multi_camera_inference as mci
from app.services.remote_camera import _FramePacket
from test_remote_camera_multi import FakeSession, jpeg


def main():
    frames = CameraFrameService()
    with tempfile.TemporaryDirectory() as directory, patch.object(rcm, "camera_frame_service", frames):
        manager = rcm.RemoteCameraManager(
            registry_path=Path(directory) / "cameras.json", session_factory=FakeSession
        )
        now_ms = int(time.time() * 1000)
        manager._now_ms = lambda: now_ms
        settings = dict(rcm.DEFAULT_CAMERA_SETTINGS)
        for source, host in (("cam_a", "192.168.1.81"), ("cam_b", "192.168.1.82")):
            manager.save_profile(source_id=source, host=host)
            manager.connect(source_id=source, host=host)
            manager.start_stream(settings=settings)
        a, b = manager._sessions["cam_a"], manager._sessions["cam_b"]
        a.emit(1, jpeg(60))
        b.emit(1, jpeg(90))
        inputs = {frame.source_id: (frame, token) for frame, token in manager.inference_inputs()}
        frame_a, token_a = inputs["cam_a"]
        frame_b, token_b = inputs["cam_b"]
        assert manager.observation_is_current("cam_b", token_b, frame_b.received_at_ms)

        # Cache an AI result before retirement. API reads must check lifetime even
        # when the background worker has not yet run another iteration.
        ai = mci.MultiCameraInferenceService()
        ai._results["cam_b"] = {
            "source_id": "cam_b", "frame": {"timestamp_ms": frame_b.received_at_ms},
            "error": None, "model_id": "test",
            "diagnostics": {"source_timestamp_ms": frame_b.received_at_ms},
        }
        ai._tokens["cam_b"] = token_b
        manager.stop_stream()
        assert frames.latest_frame() is None
        assert [f.source_id for f in manager.frames_for_inference()] == ["cam_a"]
        assert not manager.observation_is_current("cam_b", token_b, frame_b.received_at_ms)
        assert manager.observation_is_current("cam_a", token_a, frame_a.received_at_ms)
        with patch.object(mci, "remote_camera_manager", manager):
            result = ai.result("cam_b")
            assert result["frame"] is None and not result["diagnostics"]["fresh"]
        b.emit(2, jpeg(91))
        assert frames.latest_frame() is None
        print("[PASS] stop invalidates selected image and AI, preserves neighbour and rejects late packet")

        manager.start_stream(settings=settings)
        assert frames.latest_frame() is None
        cancelled = Event()
        cancelled.set()
        b.frame_sink("cam_b", _FramePacket(3, 30, jpeg(92), worker_stop=cancelled))
        assert frames.latest_frame() is None
        b.emit(4, jpeg(93))
        new = frames.latest_frame()
        assert new is not None and new.source_id == "cam_b"
        assert not manager.observation_is_current("cam_b", token_b, frame_b.received_at_ms)
        print("[PASS] restart rejects old worker and accepts new packet")

        new_token = next(t for f, t in manager.inference_inputs() if f.source_id == "cam_b")
        b.emit(5, jpeg(94))
        assert manager.observation_is_current("cam_b", new_token, new.received_at_ms)
        frames.set_simulation(True)
        manager.sync_after_simulation_change()
        assert not manager.observation_is_current("cam_b", new_token, new.received_at_ms)
        frames.set_simulation(False)
        manager.sync_after_simulation_change()
        assert not manager.observation_is_current("cam_b", new_token, new.received_at_ms)
        print("[PASS] slow current inference survives newer frames but not simulation round trip")

        # Complete a prediction after the camera is stopped inside detect_frame.
        # Keep the other camera's result and forward only its current observation.
        runner = mci.MultiCameraInferenceService()
        published = []
        processed = []

        def detect_frame(frame, **kwargs):
            processed.append(frame.source_id)
            if frame.source_id == "cam_b":
                manager.stop_stream()
            return {"source_id": frame.source_id, "timestamp_ms": frame.received_at_ms,
                    "detections": []}

        runner._stop.wait = lambda timeout: runner._stop.set()
        with patch.object(mci, "remote_camera_manager", manager), patch.object(
            mci, "camera_frame_service", frames
        ), patch.object(mci, "inference_service", SimpleNamespace(
            status=lambda: {"active_model_id": "test"}, detect_frame=detect_frame
        )), patch.object(mci, "runtime_settings_service", SimpleNamespace(
            get=lambda: {"default_confidence": 0.5, "inference_interval_ms": 100}
        )), patch.object(mci, "crosswalk_signal_service", SimpleNamespace(
            ingest_camera_results=lambda snapshot, **kwargs: published.append(snapshot)
        )):
            runner._run()
        assert set(processed) == {"cam_a", "cam_b"}
        assert set(runner._results) == {"cam_a"}
        assert len(published) == 1 and set(published[0]) == {"cam_a"}
        print("[PASS] late inference is discarded and only current neighbour is forwarded")

        manager.start_stream(settings=settings)
        b.emit(6, jpeg(95))
        manager.disconnect()
        assert frames.latest_frame() is None
        assert [f.source_id for f in manager.frames_for_inference()] == ["cam_a"]
        manager.select("cam_a")
        assert frames.latest_frame() is frame_a
        manager.disconnect_all()
        assert frames.latest_frame() is None and manager.frames_for_inference() == []
        print("[PASS] disconnect and disconnect-all clear their source observations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
