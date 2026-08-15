"""Hardware-free checks for the signal-aware PC camera simulation service."""
from __future__ import annotations

import base64
import sys
import time
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pc-studio" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.error_codes import ErrorCode  # noqa: E402
from app.core.exceptions import AppError  # noqa: E402
from app.services.camera_frames import (  # noqa: E402
    EASTBOUND_STOP_LINE,
    TOP_PEDESTRIAN_WAIT_Y,
    CameraFrameService,
)

ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def decode_png(content: bytes) -> np.ndarray:
    image = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert image is not None
    return image


def main() -> int:
    service = CameraFrameService()
    service._simulation_seed = 12345
    assert service.status()["frame_available"] is False

    simulation = service.set_simulation(True)
    assert simulation["mode"] == "simulation"
    assert simulation["frame_available"] is True
    assert simulation["simulation_density"] == "normal"
    assert simulation["simulation_signal_phase"] == "vehicle_green"
    assert simulation["simulation_signal_vehicle_go"] is True
    assert simulation["simulation_signal_pedestrian_walk"] is False

    simulated_frame = service.latest_frame()
    assert simulated_frame is not None
    assert simulated_frame.content_type == "image/png"
    assert simulated_frame.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert (simulated_frame.width, simulated_frame.height) == (1280, 720)
    image = decode_png(simulated_frame.content)
    stripe_region = image[297:320, 538:742]
    assert float(np.percentile(stripe_region.mean(axis=2), 75)) > 190

    # A vehicle approaching the stop line must queue when vehicle traffic is not green.
    with service._lock:
        vehicle = next(item for item in service._vehicles if item.direction > 0)
        vehicle.x = EASTBOUND_STOP_LINE - vehicle.width - 90
        service._simulation_clock_s = 12.2  # vehicle yellow
        before = vehicle.x
        service._advance_simulation_locked(2.0)
        assert vehicle.x > before
        assert vehicle.x + vehicle.width <= EASTBOUND_STOP_LINE - 7
        stopped_x = vehicle.x
        service._advance_simulation_locked(0.5)
        assert abs(vehicle.x - stopped_x) < 0.001

        # Green releases the queued vehicle through the crossing.
        service._simulation_clock_s = 0.2
        service._advance_simulation_locked(0.5)
        assert vehicle.x > stopped_x

    # A pedestrian approaches the curb but does not enter the road during vehicle green.
    with service._lock:
        pedestrian = next(item for item in service._pedestrians if item.direction > 0)
        pedestrian.y = float(TOP_PEDESTRIAN_WAIT_Y)
        service._simulation_clock_s = 2.0
        service._advance_simulation_locked(1.0)
        assert abs(pedestrian.y - TOP_PEDESTRIAN_WAIT_Y) < 0.001

        # WALK releases pedestrians across the zebra crossing.
        service._simulation_clock_s = 18.1
        service._advance_simulation_locked(0.75)
        assert pedestrian.y > TOP_PEDESTRIAN_WAIT_Y

        # During pedestrian WALK, a fresh vehicle remains behind its stop line.
        vehicle = next(item for item in service._vehicles if item.direction > 0)
        vehicle.x = EASTBOUND_STOP_LINE - vehicle.width - 60
        service._advance_simulation_locked(1.0)
        assert vehicle.x + vehicle.width <= EASTBOUND_STOP_LINE - 7

    # Signal cycle exposes yellow, all-red, WALK and pedestrian-clear phases.
    with service._lock:
        checks = [
            (12.1, "vehicle_yellow"),
            (15.2, "all_red"),
            (18.2, "pedestrian_green"),
            (26.2, "pedestrian_flashing"),
            (32.2, "all_red"),
        ]
        for clock_s, expected in checks:
            service._simulation_clock_s = clock_s
            assert service._simulation_signal_state_locked()["phase"] == expected

    service.configure_simulation(density="busy")
    busy_status = service.status()
    assert busy_status["simulation_density"] == "busy"
    assert len(service._vehicles) == 12
    assert len(service._pedestrians) == 11

    paused = service.configure_simulation(paused=True)
    assert paused["simulation_paused"] is True
    assert paused["streaming"] is False
    frozen = service.latest_frame()
    assert frozen is not None
    frozen_number = frozen.frame_number
    frozen_content = frozen.content
    frozen_phase = service.status()["simulation_signal_phase"]
    time.sleep(0.55)
    still_frozen = service.latest_frame()
    assert still_frozen is not None
    assert still_frozen.frame_number == frozen_number
    assert still_frozen.content == frozen_content
    assert service.status()["simulation_signal_phase"] == frozen_phase

    resumed = service.configure_simulation(paused=False)
    assert resumed["simulation_paused"] is False
    assert resumed["streaming"] is True
    time.sleep(0.55)
    moving = service.latest_frame()
    assert moving is not None
    assert moving.frame_number > frozen_number

    try:
        service.configure_simulation(density="extreme")
    except AppError as exc:
        assert exc.code == ErrorCode.INVALID_REQUEST
    else:
        raise AssertionError("Invalid simulation density was accepted")

    service.set_simulation(False)
    assert service.status()["frame_available"] is False
    assert service.status()["simulation_signal_phase"] is None
    try:
        service.configure_simulation(paused=True)
    except AppError as exc:
        assert exc.code == ErrorCode.CAMERA_STREAM_NOT_STARTED
    else:
        raise AssertionError("Simulation paused while simulation mode was stopped")

    uploaded = service.store_upload(source_id="test_camera", content_type="image/png", content=ONE_PIXEL_PNG)
    assert (uploaded.width, uploaded.height) == (1, 1)
    assert service.status()["active_source_id"] == "test_camera"

    try:
        service.store_upload(source_id="test_camera", content_type="text/plain", content=b"bad")
    except AppError as exc:
        assert exc.code == ErrorCode.CAMERA_FRAME_TYPE_UNSUPPORTED
    else:
        raise AssertionError("Unsupported camera content type was accepted")

    print("[PASS] camera receiver accepts PNG frames")
    print("[PASS] signal-aware simulation renders the road, crosswalk, stop lines, and signal state")
    print("[PASS] vehicles queue at the stop line and resume only on vehicle green")
    print("[PASS] pedestrians wait at the curb and enter the crossing only on WALK")
    print("[PASS] yellow/all-red/WALK/CLEAR signal cycle is deterministic")
    print("[PASS] density and pause/resume preserve stateful simulation behavior")
    print("[PASS] invalid upload/settings inputs retain stable errors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
