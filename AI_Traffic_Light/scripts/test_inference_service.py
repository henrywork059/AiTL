"""Filesystem-isolated checks for trained-model discovery, selection, and live inference."""
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
from app.services.model_registry import ModelRegistryService  # noqa: E402


class FakeTensor:
    def __init__(self, values: list[Any]) -> None:
        self._values = values

    def cpu(self) -> "FakeTensor":
        return self

    def tolist(self) -> list[Any]:
        return self._values


class FakeBoxes:
    xyxy = FakeTensor([[20.2, 30.7, 150.6, 180.3], [200.0, 60.0, 310.0, 190.0]])
    conf = FakeTensor([0.91, 0.03])
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

        registry = ModelRegistryService(output_root=output_root)
        registry.set_default_model("train_old")

        created_models: list[FakeYoloModel] = []

        def factory(model_path: str) -> FakeYoloModel:
            model = FakeYoloModel(model_path)
            created_models.append(model)
            return model

        service = InferenceService(output_root=output_root, yolo_factory=factory, model_registry=registry)
        discovered = service.discover_models()
        assert [item.model_id for item in discovered] == ["train_latest", "train_old"]
        assert discovered[0].is_latest is True
        assert discovered[1].is_default is True

        status = service.load_selected("train_old")
        assert status["model_loaded"] is True
        assert status["active_model_id"] == "train_old"
        assert created_models[0].model_path.endswith("train_old/weights/best.pt") or created_models[0].model_path.endswith("train_old\\weights\\best.pt")

        frame = make_frame()
        result = service.detect_frame(frame, confidence_threshold=0.03)
        assert result["source_id"] == "simulation"
        assert result["image_width"] == 320 and result["image_height"] == 240
        assert result["source_frame_number"] == frame.frame_number
        assert len(result["detections"]) == 2
        assert result["detections"][0]["class_name"] == "person"
        assert result["detections"][0]["box_xyxy"] == [20, 31, 151, 180]
        assert created_models[0].last_kwargs["conf"] == 0.03
        assert isinstance(created_models[0].last_kwargs["source"], np.ndarray)

        cached = service.detect_frame(frame, confidence_threshold=0.03)
        assert cached == result
        assert created_models[0].predict_calls == 1, "same frame and confidence should use cached detections"

        changed_conf = service.detect_frame(frame, confidence_threshold=0.5)
        assert changed_conf == result
        assert created_models[0].predict_calls == 2, "different confidence should trigger a new inference call"

        service.unload()
        try:
            service.detect_frame(make_frame(9))
        except AppError as exc:
            assert exc.code == ErrorCode.MODEL_NOT_LOADED
        else:
            raise AssertionError("Inference ran after model unload")

        service.load_default_or_latest()
        assert service.status()["active_model_id"] == "train_old"

        empty_service = InferenceService(output_root=Path(temporary_directory) / "empty", yolo_factory=factory)
        try:
            empty_service.load_latest()
        except AppError as exc:
            assert exc.code == ErrorCode.MODEL_VERSION_NOT_FOUND
        else:
            raise AssertionError("Missing trained model was accepted")

    print("[PASS] selected and default models can be discovered and loaded")
    print("[PASS] confidence is forwarded to the backend model predict call")
    print("[PASS] repeated requests for the same frame and confidence use cached inference")
    print("[PASS] unloaded/missing models return stable project errors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
