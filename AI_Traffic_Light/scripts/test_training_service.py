"""Dependency-free checks for the optional real YOLO training orchestration."""
from __future__ import annotations

from pathlib import Path
import sys
import time
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pc-studio" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.error_codes import ErrorCode  # noqa: E402
from app.core.exceptions import AppError  # noqa: E402
from app.services.training import TrainingService  # noqa: E402


class FakeYoloModel:
    def __init__(self) -> None:
        self.callbacks: dict[str, Any] = {}

    def add_callback(self, event: str, callback: Any) -> None:
        self.callbacks[event] = callback

    def train(self, **kwargs: Any) -> None:
        callback = self.callbacks.get("on_train_epoch_end")
        for epoch in range(kwargs["epochs"]):
            if callback:
                callback(SimpleNamespace(epoch=epoch))
        weights = Path(kwargs["project"]) / kwargs["name"] / "weights"
        weights.mkdir(parents=True, exist_ok=True)
        (weights / "best.pt").write_bytes(b"fake-test-weight")


def main() -> int:
    with TemporaryDirectory(prefix="aitl-training-test-") as temporary_directory:
        temporary_root = Path(temporary_directory)
        dataset_root = temporary_root / "datasets"
        dataset_yaml = dataset_root / "yolo" / "data.yaml"
        dataset_yaml.parent.mkdir(parents=True)
        dataset_yaml.write_text("train: images/train\nval: images/val\nnames: [person, car]\n", encoding="utf-8")
        service = TrainingService(
            dataset_root=dataset_root,
            output_root=temporary_root / "outputs" / "training",
            yolo_factory=lambda _model_name: FakeYoloModel(),
        )

        started = service.start(
            dataset_yaml="yolo/data.yaml",
            base_model="yolo26n.pt",
            epochs=2,
            image_size=640,
            batch=2,
            device="cpu",
        )
        assert started["status"] in {"running", "completed"}
        deadline = time.monotonic() + 3
        status = service.status()
        while status["status"] == "running" and time.monotonic() < deadline:
            time.sleep(0.02)
            status = service.status()
        assert status["status"] == "completed", status
        assert status["progress"] == 100
        assert status["best_model_path"].endswith("/weights/best.pt")

        try:
            service.start(
                dataset_yaml="../outside.yaml",
                base_model="yolo26n.pt",
                epochs=1,
                image_size=640,
                batch=1,
                device="cpu",
            )
        except AppError as exc:
            assert exc.code == ErrorCode.TRAINING_CONFIG_INVALID
        else:
            raise AssertionError("Dataset path traversal was accepted")

    print("[PASS] labeled YOLO dataset config is validated")
    print("[PASS] training runs outside the API request and reports completion")
    print("[PASS] dataset path traversal is rejected with a stable error code")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
