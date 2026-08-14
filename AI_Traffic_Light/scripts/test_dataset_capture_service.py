"""Filesystem-isolated checks for persistent receiver and simulation capture."""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pc-studio" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.camera_frames import CameraFrameService  # noqa: E402
from app.services.dataset_capture import DatasetCaptureService  # noqa: E402

ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def main() -> int:
    with TemporaryDirectory(prefix="aitl-capture-test-") as temporary_directory:
        dataset_root = Path(temporary_directory) / "datasets"
        camera = CameraFrameService()
        capture = DatasetCaptureService(dataset_root=dataset_root)

        uploaded = camera.store_upload(
            source_id="test_receiver",
            content_type="image/png",
            content=ONE_PIXEL_PNG,
        )
        receiver_record = capture.capture_frame(
            uploaded,
            session_id="receiver_test",
            quality_tag="useful",
            note="receiver unit test",
        )
        receiver_image = dataset_root / receiver_record.image_path
        receiver_metadata = dataset_root / receiver_record.metadata_path
        assert receiver_image.read_bytes() == ONE_PIXEL_PNG
        assert json.loads(receiver_metadata.read_text(encoding="utf-8"))["origin"] == "upload"

        camera.set_simulation(True)
        simulated = camera.latest_frame()
        assert simulated is not None and simulated.content_type == "image/png"
        simulation_record = capture.capture_frame(simulated, session_id="simulation_test")
        assert (dataset_root / simulation_record.image_path).read_bytes().startswith(b"\x89PNG")
        assert json.loads((dataset_root / simulation_record.metadata_path).read_text(encoding="utf-8"))["origin"] == "simulation"

        status = capture.status()
        assert status["frame_count"] == 2
        assert status["metadata_count"] == 2
        assert status["session_count"] == 2

    print("[PASS] receiver frame persists with paired JSON metadata")
    print("[PASS] simulation frame persists as PNG")
    print("[PASS] capture counts survive filesystem scanning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
