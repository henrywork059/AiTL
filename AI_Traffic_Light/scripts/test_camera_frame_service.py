"""Hardware-free checks for the V016 PC camera frame service."""
from __future__ import annotations

import base64
import sys
import time
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pc-studio" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.error_codes import ErrorCode  # noqa: E402
from app.core.exceptions import AppError  # noqa: E402
from app.services.camera_frames import CameraFrameService  # noqa: E402

ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def decode_png(content: bytes) -> np.ndarray:
    image = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert image is not None
    return image


def color_center(image: np.ndarray, bgr: tuple[int, int, int]) -> tuple[float, float]:
    mask = np.all(image == np.array(bgr, dtype=np.uint8), axis=2)
    ys, xs = np.where(mask)
    assert len(xs) > 0, f"Expected synthetic color {bgr} was not present"
    return float(xs.mean()), float(ys.mean())


def main() -> int:
    service = CameraFrameService()
    service._simulation_seed = 12345  # Deterministic synthetic-scene test only.
    assert service.status()["frame_available"] is False

    simulation = service.set_simulation(True)
    assert simulation["mode"] == "simulation"
    assert simulation["frame_available"] is True
    assert simulation["simulation_density"] == "normal"
    assert simulation["simulation_paused"] is False
    simulated_frame = service.latest_frame()
    assert simulated_frame is not None
    assert simulated_frame.content_type == "image/png"
    assert simulated_frame.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert (simulated_frame.width, simulated_frame.height) == (1280, 720)

    image = decode_png(simulated_frame.content)
    # The V016 zebra crossing is a vertical travel corridor with horizontal white bars.
    assert int(image[210, 640].mean()) > 200
    assert int(image[240, 640].mean()) < 130
    assert int(image[210, 500].mean()) < 160

    service.configure_simulation(density="busy")
    assert service.status()["simulation_density"] == "busy"

    # Freeze one frame and confirm repeated reads do not advance it.
    paused = service.configure_simulation(paused=True)
    assert paused["simulation_paused"] is True
    assert paused["streaming"] is False
    frozen = service.latest_frame()
    assert frozen is not None
    frozen_number = frozen.frame_number
    frozen_content = frozen.content
    time.sleep(0.55)
    still_frozen = service.latest_frame()
    assert still_frozen is not None
    assert still_frozen.frame_number == frozen_number
    assert still_frozen.content == frozen_content

    resumed = service.configure_simulation(paused=False)
    assert resumed["simulation_paused"] is False
    assert resumed["streaming"] is True
    time.sleep(0.55)
    moving = service.latest_frame()
    assert moving is not None
    assert moving.frame_number > frozen_number

    # Deterministic direction check: first car moves horizontally and first pedestrian moves downward.
    direction_service = CameraFrameService()
    direction_service._simulation_seed = 12345
    with patch("app.services.camera_frames.time.time", return_value=1000.0):
        direction_service.set_simulation(True)
        frame_a = direction_service.latest_frame()
    with patch("app.services.camera_frames.time.time", return_value=1000.5):
        frame_b = direction_service.latest_frame()
    assert frame_a is not None and frame_b is not None
    image_a = decode_png(frame_a.content)
    image_b = decode_png(frame_b.content)
    car_a = color_center(image_a, (66, 135, 245))
    car_b = color_center(image_b, (66, 135, 245))
    person_a = color_center(image_a, (196, 111, 255))
    person_b = color_center(image_b, (196, 111, 255))
    assert car_b[0] > car_a[0]
    assert abs(car_b[1] - car_a[1]) < 1.0
    assert abs(person_b[0] - person_a[0]) < 1.0
    assert person_b[1] > person_a[1]

    try:
        service.configure_simulation(density="extreme")
    except AppError as exc:
        assert exc.code == ErrorCode.INVALID_REQUEST
    else:
        raise AssertionError("Invalid simulation density was accepted")

    service.set_simulation(False)
    assert service.status()["frame_available"] is False
    try:
        service.configure_simulation(paused=True)
    except AppError as exc:
        assert exc.code == ErrorCode.CAMERA_STREAM_NOT_STARTED
    else:
        raise AssertionError("Simulation paused while simulation mode was stopped")

    uploaded = service.store_upload(
        source_id="test_camera",
        content_type="image/png",
        content=ONE_PIXEL_PNG,
    )
    assert (uploaded.width, uploaded.height) == (1, 1)
    assert service.status()["active_source_id"] == "test_camera"

    try:
        service.store_upload(source_id="test_camera", content_type="text/plain", content=b"bad")
    except AppError as exc:
        assert exc.code == ErrorCode.CAMERA_FRAME_TYPE_UNSUPPORTED
    else:
        raise AssertionError("Unsupported camera content type was accepted")

    print("[PASS] camera receiver accepts PNG frames")
    print("[PASS] simulation uses a vertical crossing with horizontal zebra bars")
    print("[PASS] vehicles move horizontally and pedestrians move top-to-bottom")
    print("[PASS] light/normal/busy density setting is validated")
    print("[PASS] simulation pause/resume freezes and restarts frame progression")
    print("[PASS] invalid upload types return stable camera errors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
