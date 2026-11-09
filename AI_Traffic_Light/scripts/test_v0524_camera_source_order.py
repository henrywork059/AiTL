"""Independent source-frame freshness, model resets and disconnected-camera behavior."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/pc-studio/backend"))
from app.services.multi_camera_inference import _is_new_source_frame  # noqa: E402


def main() -> None:
    cam_a = ("model", 0.5, 10, 1000)
    cam_b = ("model", 0.5, 2, 1100)
    assert _is_new_source_frame(None, cam_a)
    assert not _is_new_source_frame(cam_a, cam_a)
    assert not _is_new_source_frame(cam_a, ("model", 0.5, 11, 999))
    assert _is_new_source_frame(cam_a, ("model", 0.5, 1, 1200))  # Reconnect resets number
    assert _is_new_source_frame(cam_b, ("model", 0.5, 3, 1300))
    assert _is_new_source_frame(cam_a, ("new-model", 0.5, 10, 1000))
    assert _is_new_source_frame(cam_a, ("model", 0.7, 10, 1000))
    print("[PASS] source-specific ordering and reconnection freshness guards")


if __name__ == "__main__":
    main()
