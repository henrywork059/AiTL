"""V0541: image uploads must decode fully before replacing the latest valid frame."""
from __future__ import annotations

import base64
import sys
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/pc-studio/backend"))

from app.core.error_codes import ErrorCode  # noqa: E402
from app.core.exceptions import AppError  # noqa: E402
from app.services.camera_frames import CameraFrameService, MAX_FRAME_PIXELS  # noqa: E402

ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
TRUNCATED_PNG = ONE_PIXEL_PNG[:24]  # Valid IHDR dimensions but no image data or CRC.
TRUNCATED_JPEG = bytes.fromhex("ffd8ffc00011080001000103011100021100031100")


def main() -> None:
    service = CameraFrameService()
    original = service.store_upload(source_id="integrity_camera", content_type="image/png", content=ONE_PIXEL_PNG)
    assert (original.width, original.height) == (1, 1)

    success, encoded_jpeg = cv2.imencode(".jpg", np.zeros((2, 3, 3), dtype=np.uint8))
    assert success
    jpeg = encoded_jpeg.tobytes()
    frame = service.store_upload(source_id="integrity_camera", content_type="image/jpeg", content=jpeg)
    assert (frame.width, frame.height) == (3, 2)
    assert service.latest_frame() is frame

    def rejects(content_type: str, content: bytes) -> None:
        before = service.latest_frame()
        counter = service._frame_counter
        try:
            service.store_upload(source_id="integrity_camera", content_type=content_type, content=content)
        except AppError as exc:
            assert exc.code == ErrorCode.CAMERA_FRAME_INVALID
            assert exc.status_code == 422
        else:
            raise AssertionError("Malformed camera frame was accepted")
        assert service.latest_frame() is before, "Rejected upload replaced the last valid frame"
        assert service._frame_counter == counter, "Rejected upload advanced the frame counter"

    rejects("image/png", TRUNCATED_PNG)
    rejects("image/jpeg", TRUNCATED_JPEG)
    rejects("image/jpeg", ONE_PIXEL_PNG)  # Declared MIME must match encoded image.
    rejects("image/png", jpeg)

    # Oversized pixel declarations must fail before decoding, even with a small body.
    huge_png = bytearray(TRUNCATED_PNG)
    huge_png[16:20] = (20000).to_bytes(4, "big")
    huge_png[20:24] = (20000).to_bytes(4, "big")
    assert 20000 * 20000 > MAX_FRAME_PIXELS
    with patch("app.services.camera_frames.cv2.imdecode", side_effect=AssertionError("Decoded oversized pixels")):
        rejects("image/png", bytes(huge_png))

    print("[PASS] fully decodable PNG/JPEG and matching MIME required")
    print("[PASS] truncated, mislabeled and over-pixel-limit frames cannot replace valid state")


if __name__ == "__main__":
    main()
