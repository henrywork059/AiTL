"""Per-camera diagnostics retain source provenance and suppress stale/model-switched frames."""
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/pc-studio/backend"))
from app.services.multi_camera_inference import MultiCameraInferenceService  # noqa: E402
from app.services.remote_camera_manager import remote_camera_manager  # noqa: E402


def main() -> None:
    service = MultiCameraInferenceService()
    now = int(time.time() * 1000)
    service._results["cam_a"] = {
        "source_id": "cam_a", "model_id": None, "error": None,
        "frame": {"source_id": "cam_a", "timestamp_ms": now - 150},
        "diagnostics": {"inference_latency_ms": 14.5,
                        "source_timestamp_ms": now - 150,
                        "source_frame_number": 4, "source_origin": "simulation"},
    }
    service._results["cam_b"] = {
        "source_id": "cam_b", "model_id": None, "error": None,
        "frame": {"source_id": "cam_b", "timestamp_ms": now - 6500},
        "diagnostics": {"inference_latency_ms": 30.0,
                        "source_timestamp_ms": now - 6500,
                        "source_frame_number": 3, "source_origin": "upload"},
    }
    # V0548 requires a source/mode retirement token for every cached result.
    # This test isolates presentation/age formatting; source retirement itself
    # is covered by the lifecycle regressions using the real camera manager.
    service._tokens["cam_a"] = ((True, 1), 0)
    service._tokens["cam_b"] = ((False, 1), 0)

    def current(source_id, token, timestamp):
        result = service._results.get(source_id, {})
        return (token == service._tokens.get(source_id)
                and token is not None
                and timestamp == result.get("diagnostics", {}).get("source_timestamp_ms"))

    with patch.object(remote_camera_manager, "observation_is_current", side_effect=current):
        fresh = service.result("cam_a")
        stale = service.result("cam_b")
        assert fresh["source_id"] == "cam_a" and fresh["diagnostics"]["fresh"] is True
        assert fresh["diagnostics"]["inference_latency_ms"] == 14.5
        assert fresh["diagnostics"]["frame_age_ms"] >= 150
        assert stale["frame"] is None and stale["error"] == "Frame is stale"
        assert stale["diagnostics"]["fresh"] is False
        assert stale["diagnostics"]["frame_age_ms"] >= 6500
        assert service.result("missing")["diagnostics"]["frame_age_ms"] is None

        # A retired result must remain unavailable even if its timestamp is fresh.
        service._tokens.pop("cam_a")
        unavailable = service.result("cam_a")
        assert unavailable["frame"] is None
        assert unavailable["error"] == "Camera observation unavailable"
        assert unavailable["diagnostics"]["fresh"] is False
    print("[PASS] per-source latency, age, model and stale observation diagnostics")


if __name__ == "__main__":
    main()
