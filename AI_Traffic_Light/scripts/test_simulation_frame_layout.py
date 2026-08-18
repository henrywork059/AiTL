"""Focused layout checks for the signal-aware simulation frame."""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pc-studio" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.camera_frames import CameraFrameService  # noqa: E402


def _decode_png(png_bytes: bytes) -> np.ndarray:
    frame = cv2.imdecode(np.frombuffer(png_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise AssertionError("Simulation frame did not decode as PNG")
    return frame


def main() -> int:
    service = CameraFrameService()
    service.set_simulation(True)
    frame = service.latest_frame()
    assert frame is not None
    image = _decode_png(frame.content)

    # The compact metadata panel still exists in the top-left corner.
    assert int(image[40, 40].mean()) < 40
    # The resized panel should no longer extend deep into the upper-left scene.
    assert int(image[90, 620].mean()) > 45
    assert int(image[150, 120].mean()) > 45

    # The traffic signal housing remains visible.
    assert int(image[240, 1095].mean()) < 40
    # The pedestrian signal should be smaller, leaving the far-right lane visible.
    assert int(image[300, 1250].mean()) > 45

    print("[PASS] simulation metadata panel stays compact and leaves more scene visible")
    print("[PASS] pedestrian signal housing is reduced and no longer dominates the right lane")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
