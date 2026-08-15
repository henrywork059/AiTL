"""Hardware-free service/API checks for V020 capture deletion."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import ModuleType
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pc-studio" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))


def _training_status_stub() -> dict[str, Any]:
    return {
        "ready": False,
        "stale": True,
        "dataset_yaml": "yolo/data.yaml",
        "labeled_frame_count": 0,
        "eligible_frame_count": 0,
        "excluded_bad_count": 0,
        "label_box_count": 0,
        "train_count": 0,
        "val_count": 0,
        "generated_at_ms": None,
        "classes": [],
        "message": "Test stub: managed dataset requires rebuild.",
    }


def main() -> int:
    with TemporaryDirectory(prefix="aitl-v020-delete-") as temporary_directory:
        dataset_root = Path(temporary_directory) / "datasets"
        os.environ["AITL_DATASET_DIR"] = str(dataset_root)

        # The delete route only needs training_dataset_status() after the destructive action.
        # Stub the large labeling service so this focused test remains fast and independent of
        # existing user datasets while still exercising the real V020 dataset router.
        labeling_module = ModuleType("app.services.dataset_labeling")

        class LabelingStub:
            def training_dataset_status(self) -> dict[str, Any]:
                return _training_status_stub()

        labeling_module.dataset_labeling_service = LabelingStub()  # type: ignore[attr-defined]
        sys.modules["app.services.dataset_labeling"] = labeling_module

        from fastapi import FastAPI, Request  # noqa: E402
        from fastapi.testclient import TestClient  # noqa: E402
        from app.core.exceptions import AppError, app_error_handler  # noqa: E402
        from app.routes.dataset import router as dataset_router  # noqa: E402
        from app.services.camera_frames import CameraFrame  # noqa: E402
        from app.services.dataset_capture import dataset_capture_service  # noqa: E402

        app = FastAPI()

        @app.middleware("http")
        async def add_request_id(request: Request, call_next: Any):
            request.state.request_id = request.headers.get("X-Request-ID", "test-request")
            response = await call_next(request)
            response.headers["X-Request-ID"] = request.state.request_id
            return response

        app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
        app.include_router(dataset_router, prefix="/api/dataset")

        frame = CameraFrame(
            content=b"synthetic-png-bytes",
            content_type="image/png",
            source_id="delete_test",
            width=1280,
            height=720,
            received_at_ms=123456,
            frame_number=7,
            origin="simulation",
        )
        record = dataset_capture_service.capture_frame(frame, session_id="delete_test")
        image_path = dataset_root / record.image_path
        metadata_path = dataset_root / record.metadata_path
        label_path = dataset_root / "captures" / record.session_id / "labels" / f"{record.capture_id}.json"
        label_path.parent.mkdir(parents=True, exist_ok=True)
        label_path.write_text(
            json.dumps(
                {
                    "capture_id": record.capture_id,
                    "session_id": record.session_id,
                    "image_path": record.image_path,
                    "width": record.width,
                    "height": record.height,
                    "reviewed": True,
                    "updated_at_ms": 123456,
                    "labels": [],
                }
            ),
            encoding="utf-8",
        )
        assert image_path.is_file() and metadata_path.is_file() and label_path.is_file()

        client = TestClient(app)
        response = client.delete(
            f"/api/dataset/captures/{record.capture_id}",
            headers={"X-Request-ID": "req_capture_delete"},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["ok"] is True
        assert payload["meta"]["request_id"] == "req_capture_delete"
        assert payload["data"]["capture_id"] == record.capture_id
        assert payload["data"]["deleted"] is True
        assert payload["data"]["training_dataset"]["stale"] is True
        assert response.headers.get("x-request-id") == "req_capture_delete"
        assert not image_path.exists()
        assert not metadata_path.exists()
        assert not label_path.exists()
        assert dataset_capture_service.status()["last_capture"] is None

        missing = client.delete(f"/api/dataset/captures/{record.capture_id}")
        assert missing.status_code == 404
        assert missing.json()["error"]["code"] == "ATL-DATASET-003"

    print("[PASS] capture deletion removes image, metadata, and saved manual labels")
    print("[PASS] delete API preserves standard envelopes and request IDs")
    print("[PASS] delete response reports managed-dataset rebuild status")
    print("[PASS] repeated deletion returns stable ATL-DATASET-003")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
