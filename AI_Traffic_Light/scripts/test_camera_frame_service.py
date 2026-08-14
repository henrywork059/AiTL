"""Hardware-free checks for the 0_1_2 PC camera frame service."""
from __future__ import annotations

import base64
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pc-studio" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.error_codes import ErrorCode  # noqa: E402
from app.core.exceptions import AppError  # noqa: E402
from app.services.camera_frames import CameraFrameService  # noqa: E402

ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def main() -> int:
    service = CameraFrameService()
    assert service.status()["frame_available"] is False

    simulation = service.set_simulation(True)
    assert simulation["mode"] == "simulation"
    assert simulation["frame_available"] is True
    simulated_frame = service.latest_frame()
    assert simulated_frame is not None
    assert simulated_frame.content_type == "image/png"
    assert simulated_frame.content.startswith(b"\x89PNG\r\n\x1a\n")

    service.set_simulation(False)
    assert service.status()["frame_available"] is False

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
    print("[PASS] simulation produces capturable PNG frames")
    print("[PASS] invalid upload types return stable camera errors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
