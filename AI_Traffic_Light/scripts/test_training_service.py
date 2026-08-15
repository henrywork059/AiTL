"""Dependency-free checks for training convergence history and early stopping orchestration."""
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
        self.last_train_kwargs: dict[str, Any] = {}

    def add_callback(self, event: str, callback: Any) -> None:
        self.callbacks[event] = callback

    def train(self, **kwargs: Any) -> None:
        self.last_train_kwargs = kwargs
        train_callback = self.callbacks.get("on_train_epoch_end")
        fit_callback = self.callbacks.get("on_fit_epoch_end")
        fitness_values = [0.20, 0.42, 0.41, 0.40, 0.39, 0.38]
        best = None
        stale = 0
        for epoch in range(kwargs["epochs"]):
            fitness = fitness_values[min(epoch, len(fitness_values) - 1)]
            if best is None or fitness > best:
                best = fitness
                stale = 0
            else:
                stale += 1
            trainer = SimpleNamespace(
                epoch=epoch,
                fitness=fitness,
                metrics={
                    "metrics/mAP50-95(B)": fitness,
                    "metrics/mAP50(B)": min(1.0, fitness + 0.2),
                    "val/box_loss": 1.0 / (epoch + 1),
                    "val/cls_loss": 0.5 / (epoch + 1),
                },
                tloss=SimpleNamespace(),
                label_loss_items=lambda _loss, prefix="train": {
                    f"{prefix}/box_loss": 1.2 / (epoch + 1),
                    f"{prefix}/cls_loss": 0.6 / (epoch + 1),
                },
            )
            if train_callback:
                train_callback(trainer)
            if fit_callback:
                fit_callback(trainer)
            if stale >= kwargs["patience"]:
                break
        if fit_callback:
            # Ultralytics may invoke on_fit_epoch_end again during final best-model
            # evaluation with no fitness value. The real epoch point must survive.
            fit_callback(SimpleNamespace(
                epoch=epoch,
                fitness=None,
                metrics={"metrics/mAP50-95(B)": 0.99},
                tloss=SimpleNamespace(),
                label_loss_items=lambda _loss, prefix="train": {},
            ))
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
        fake_model = FakeYoloModel()
        service = TrainingService(
            dataset_root=dataset_root,
            output_root=temporary_root / "outputs" / "training",
            yolo_factory=lambda _model_name: fake_model,
        )

        started = service.start(
            dataset_yaml="yolo/data.yaml",
            base_model="yolo26n.pt",
            epochs=8,
            image_size=640,
            batch=2,
            device="cpu",
            patience=2,
        )
        assert started["status"] in {"running", "early_stopped"}
        deadline = time.monotonic() + 3
        status = service.status()
        while status["status"] == "running" and time.monotonic() < deadline:
            time.sleep(0.02)
            status = service.status()
        assert status["status"] == "early_stopped", status
        assert status["progress"] == 100
        assert status["completed_epochs"] == 4
        assert len(status["history"]) == 4
        assert status["history"][1]["fitness"] == 0.42
        assert status["history"][-1]["fitness"] == 0.40
        assert status["early_stopping"]["best_epoch"] == 2
        assert status["early_stopping"]["stopped_early"] is True
        assert status["best_model_path"].endswith("/weights/best.pt")
        assert fake_model.last_train_kwargs["patience"] == 2

        try:
            service.start(
                dataset_yaml="../outside.yaml",
                base_model="yolo26n.pt",
                epochs=1,
                image_size=640,
                batch=1,
                device="cpu",
                patience=2,
            )
        except AppError as exc:
            assert exc.code == ErrorCode.TRAINING_CONFIG_INVALID
        else:
            raise AssertionError("Dataset path traversal was accepted")

    print("[PASS] per-epoch validation/convergence history is recorded")
    print("[PASS] configured patience is forwarded to the trainer")
    print("[PASS] early-stopped runs are detected and keep best.pt metadata")
    print("[PASS] dataset path traversal is rejected with a stable error code")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
