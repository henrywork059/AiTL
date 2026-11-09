"""Per-camera diagnostics retain source provenance and suppress stale/model-switched frames."""
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/pc-studio/backend"))
from app.services.multi_camera_inference import MultiCameraInferenceService  # noqa: E402


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
    fresh = service.result("cam_a")
    stale = service.result("cam_b")
    assert fresh["source_id"] == "cam_a" and fresh["diagnostics"]["fresh"] is True
    assert fresh["diagnostics"]["inference_latency_ms"] == 14.5
    assert fresh["diagnostics"]["frame_age_ms"] >= 150
    assert stale["frame"] is None and stale["error"] == "Frame is stale"
    assert stale["diagnostics"]["fresh"] is False
    assert stale["diagnostics"]["frame_age_ms"] >= 6500
    assert service.result("missing")["diagnostics"]["frame_age_ms"] is None
    print("[PASS] per-source latency, age, model and stale observation diagnostics")


if __name__ == "__main__":
    main()
