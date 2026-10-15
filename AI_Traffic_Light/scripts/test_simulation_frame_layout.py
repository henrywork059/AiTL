"""Focused layout checks for camera-only simulation without annotations or lamps."""
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

    # Empty sidewalk retains the scene background: no dark metadata banner.
    assert np.array_equal(image[40, 40], np.array([72, 79, 84], dtype=np.uint8))
    # The old signal housing (upper right) is gone.
    assert float(image[240, 1095].mean()) > 40

    # Only car and pedestrian actors; signal logic remains separate from rendering.
    assert all(vehicle.vehicle_type == "car" for vehicle in service._vehicles)
    renderer = (BACKEND_ROOT / "app" / "services" / "camera_frames.py").read_text(encoding="utf-8")
    frame_render = renderer.split("def _refresh_simulation_locked(", 1)[1].split("encoded_ok, encoded =", 1)[0]
    assert "cv2.putText(" not in frame_render
    assert "_draw_signal_heads(" not in frame_render
    print("[PASS] camera simulation contains cars/pedestrians without metadata text or traffic lamps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
