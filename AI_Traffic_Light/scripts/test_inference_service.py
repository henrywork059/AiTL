"""Filesystem-isolated checks for trained-model discovery and live inference."""
from __future__ import annotations

import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pc-studio" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.error_codes import ErrorCode  # noqa: E402
from app.core.exceptions import AppError  # noqa: E402
from app.services.camera_frames import CameraFrame  # noqa: E402
from app.services.inference import InferenceService  # noqa: E402


class FakeTensor:
    def __init__(self, values: list[Any]) -> None:
        self._values = values

    def cpu(self) -> "FakeTensor":
        return self

    def tolist(self) -> list[Any]:
        return self._values


class FakeBoxes:
    xyxy = FakeTensor([[20.2, 30.7, 150.6, 180.3], [200.0, 60.0, 310.0, 190.0]])
    conf = FakeTensor([0.91, 0.63])
    cls = FakeTensor([0.0, 1.0])


class FakeResult:
    boxes = FakeBoxes()
    names = {0: "person", 1: "car"}


class FakeYoloModel:
    def __init__(self, model_path: str) -> None:
        self.model_path = model_path
        self.predict_calls = 0
        self.last_kwargs: dict[str, Any] = {}
        self.names = FakeResult.names

    def predict(self, **kwargs: Any) -> list[FakeResult]:
        self.predict_calls += 1
        self.last_kwargs = kwargs
        return [FakeResult()]


def make_frame(frame_number: int = 7) -> CameraFrame:
    image = np.zeros((240, 320, 3), dtype=np.uint8)
    cv2.rectangle(image, (20, 30), (150, 180), (255, 255, 255), thickness=-1)
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    return CameraFrame(
        content=encoded.tobytes(),
        content_type="image/png",
        source_id="simulation",
        width=320,
        height=240,
        received_at_ms=1234567890,
        frame_number=frame_number,
        origin="simulation",
    )


def main() -> int:
    with TemporaryDirectory(prefix="aitl-inference-test-") as temporary_directory:
        output_root = Path(temporary_directory) / "outputs" / "training"
        older = output_root / "train_old" / "weights" / "best.pt"
        latest = output_root / "train_latest" / "weights" / "best.pt"
        older.parent.mkdir(parents=True)
        latest.parent.mkdir(parents=True)
        older.write_bytes(b"old-test-weight")
        latest.write_bytes(b"latest-test-weight")
        os.utime(older, (100, 100))
        os.utime(latest, (200, 200))

        created_models: list[FakeYoloModel] = []

        def factory(model_path: str) -> FakeYoloModel:
            model = FakeYoloModel(model_path)
            created_models.append(model)
            return model

        service = InferenceService(output_root=output_root, yolo_factory=factory)
        discovered = service.discover_models()
        assert [item.model_id for item in discovered] == ["train_latest", "train_old"]

        status = service.load_latest()
        assert status["model_loaded"] is True
        assert status["active_model_id"] == "train_latest"
        assert status["active_is_latest"] is True
        assert created_models[0].model_path.endswith("train_latest/weights/best.pt") or created_models[0].model_path.endswith("train_latest\\weights\\best.pt")

        frame = make_frame()
        result = service.detect_frame(frame)
        assert result["source_id"] == "simulation"
        assert result["image_width"] == 320 and result["image_height"] == 240
        assert result["source_frame_number"] == frame.frame_number
        assert len(result["detections"]) == 2
        assert result["detections"][0]["class_name"] == "person"
        assert result["detections"][0]["box_xyxy"] == [20, 31, 151, 180]
        assert result["detections"][1]["class_name"] == "car"
        assert created_models[0].last_kwargs["conf"] == 0.10
        assert isinstance(created_models[0].last_kwargs["source"], np.ndarray)

        cached = service.detect_frame(frame)
        assert cached == result
        assert created_models[0].predict_calls == 1, "same frame should use cached detections"
        assert service.last_source_frame().content == frame.content
        assert service.source_frame(source_id="simulation", frame_number=frame.frame_number).content == frame.content
        assert service.status()["last_frame_number"] == frame.frame_number

        next_frame = make_frame(8)
        service.detect_frame(next_frame)
        assert service.source_frame(source_id="simulation", frame_number=7).content == frame.content
        assert service.source_frame(source_id="simulation", frame_number=8).content == next_frame.content

        service.unload()
        try:
            service.detect_frame(make_frame(9))
        except AppError as exc:
            assert exc.code == ErrorCode.MODEL_NOT_LOADED
        else:
            raise AssertionError("Inference ran after model unload")

        empty_service = InferenceService(output_root=Path(temporary_directory) / "empty", yolo_factory=factory)
        try:
            empty_service.load_latest()
        except AppError as exc:
            assert exc.code == ErrorCode.MODEL_VERSION_NOT_FOUND
        else:
            raise AssertionError("Missing trained model was accepted")

    print("[PASS] newest outputs/training/*/weights/best.pt is discovered and loaded")
    print("[PASS] trained-model boxes/classes/confidence use original camera coordinates")
    print("[PASS] repeated requests for the same frame use cached inference")
    print("[PASS] exact inferred source frame remains available for overlay alignment")
    print("[PASS] unloaded/missing models return stable project errors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
