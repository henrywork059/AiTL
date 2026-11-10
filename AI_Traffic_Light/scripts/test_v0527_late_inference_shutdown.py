"""An inference that completes after worker stop must not revive data or virtual observations."""
from contextlib import ExitStack
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/pc-studio/backend"))
import app.services.multi_camera_inference as module  # noqa: E402


class BlockingInference:
    def __init__(self) -> None:
        self.started = Event()
        self.release = Event()

    def status(self) -> dict:
        return {"active_model_id": "model"}

    def detect_frame(self, frame, *, confidence_threshold: float) -> dict:
        self.started.set()
        assert self.release.wait(timeout=10), "Timed out waiting to release model inference"
        return {"source_id": frame.source_id, "timestamp_ms": frame.received_at_ms, "detections": []}


def main() -> None:
    inference = BlockingInference()
    frame = SimpleNamespace(
        source_id="camera_a", frame_number=1, received_at_ms=1234567, origin="simulation",
    )
    published: list[dict] = []
    service = module.MultiCameraInferenceService()
    with ExitStack() as patches:
        patches.enter_context(patch.object(module, "inference_service", inference))
        patches.enter_context(patch.object(
            module, "runtime_settings_service",
            SimpleNamespace(get=lambda: {"default_confidence": 0.5, "inference_interval_ms": 100}),
        ))
        patches.enter_context(patch.object(
            module, "remote_camera_manager",
            SimpleNamespace(frames_for_inference=lambda: [frame]),
        ))
        patches.enter_context(patch.object(
            module, "camera_frame_service",
            SimpleNamespace(simulation_enabled=True, simulation_paused=False),
        ))
        patches.enter_context(patch.object(
            module, "crosswalk_signal_service",
            SimpleNamespace(ingest_camera_results=lambda snapshot, **kwargs: published.append(snapshot)),
        ))
        service.start()
        try:
            assert inference.started.wait(timeout=3), "Inference worker did not reach blocked model"
            service.stop()  # Its bounded join must expire before the model is released.
            worker = service._thread
            assert worker is not None and worker.is_alive()
            assert service._results == {} and service._keys == {}
            inference.release.set()
            worker.join(timeout=3)
            assert not worker.is_alive(), "Inference worker failed to exit after model was released"
            assert service._results == {} and service._keys == {}, "Late inference revived the stopped cache"
            assert not published, "Late inference published stale Crosswalk observations"
        finally:
            inference.release.set()
            service.stop()

    print("[PASS] late inference never repopulates stopped cache or publishes stale observations")


if __name__ == "__main__":
    main()
