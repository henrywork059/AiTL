from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import os
from pathlib import Path
import re
from threading import Lock, Thread
from typing import Any, Callable
from uuid import uuid4

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.core.logging_config import get_logger
from app.services.dataset_labeling import DatasetLabelingService

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_DATASET_ROOT = PROJECT_ROOT / "datasets"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "outputs" / "training"
MODEL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,80}\.(?:pt|yaml|yml)$")
DEVICE_PATTERN = re.compile(r"^(?:cpu|mps|[0-9](?:,[0-9])*)$")
YoloFactory = Callable[[str], Any]
MANAGED_DATASET_YAML = "yolo/data.yaml"


def _number(value: Any) -> float | None:
    """Convert common scalar/tensor values to a JSON-safe float."""
    if value is None:
        return None
    try:
        if hasattr(value, "item"):
            value = value.item()
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric != numeric or numeric in {float("inf"), float("-inf")}:
        return None
    return round(numeric, 6)


def _loss_total(values: dict[str, Any], prefix: str) -> float | None:
    losses = [
        numeric
        for key, value in values.items()
        if key.startswith(prefix) and "loss" in key and (numeric := _number(value)) is not None
    ]
    return round(sum(losses), 6) if losses else None


class TrainingService:
    """Run one optional Ultralytics YOLO training job outside request handling."""

    def __init__(
        self,
        *,
        dataset_root: Path | None = None,
        output_root: Path | None = None,
        yolo_factory: YoloFactory | None = None,
    ) -> None:
        configured_dataset_root = os.environ.get("AITL_DATASET_DIR")
        configured_output_root = os.environ.get("AITL_TRAINING_OUTPUT_DIR")
        self._dataset_root = Path(configured_dataset_root) if configured_dataset_root else (dataset_root or DEFAULT_DATASET_ROOT)
        self._output_root = Path(configured_output_root) if configured_output_root else (output_root or DEFAULT_OUTPUT_ROOT)
        self._dataset_root = self._dataset_root.expanduser().resolve()
        self._output_root = self._output_root.expanduser().resolve()
        self._yolo_factory = yolo_factory
        self._lock = Lock()
        self._state: dict[str, Any] = self._idle_state()

    @staticmethod
    def _idle_state() -> dict[str, Any]:
        return {
            "active_run_id": None,
            "progress": 0,
            "status": "idle",
            "message": "No training run has started.",
            "started_at_ms": None,
            "finished_at_ms": None,
            "config": None,
            "output_path": None,
            "best_model_path": None,
            "error": None,
            "history": [],
            "completed_epochs": 0,
            "early_stopping": {
                "enabled": True,
                "patience": 5,
                "epochs_without_improvement": 0,
                "best_epoch": None,
                "best_fitness": None,
                "converged": False,
                "stopped_early": False,
            },
        }

    def status(self) -> dict:
        with self._lock:
            state = dict(self._state)
            state["history"] = [dict(point) for point in self._state.get("history", [])]
            state["early_stopping"] = dict(self._state.get("early_stopping", {}))
        state.update(
            {
                "training_available": self._training_available(),
                "backend": "ultralytics_yolo_optional",
                "dataset_root": "datasets",
                "requires_labeled_dataset": True,
                "install_command": "pip install -r requirements-training.txt",
            }
        )
        return state

    def start(
        self,
        *,
        dataset_yaml: str,
        base_model: str,
        epochs: int,
        image_size: int,
        batch: int,
        device: str,
        patience: int,
    ) -> dict:
        normalized_dataset_yaml = dataset_yaml.replace("\\", "/")
        dataset_path = self._resolve_dataset_path(dataset_yaml)
        managed_manifest = self._dataset_root / "yolo" / "manifest.json"
        if normalized_dataset_yaml == MANAGED_DATASET_YAML and managed_manifest.is_file():
            managed_status = DatasetLabelingService(dataset_root=self._dataset_root).training_dataset_status()
            if not managed_status["ready"]:
                raise AppError(
                    ErrorCode.DATASET_TRAINING_NOT_READY,
                    managed_status["message"],
                    status_code=409,
                    details={
                        "dataset_yaml": MANAGED_DATASET_YAML,
                        "stale": managed_status["stale"],
                        "eligible_frame_count": managed_status["eligible_frame_count"],
                    },
                )
        if not self._training_available():
            raise AppError(
                ErrorCode.TRAINING_NOT_READY,
                "Ultralytics is not installed. Install requirements-training.txt before starting a real training run.",
                status_code=503,
            )
        self._validate_dataset_yaml(dataset_path, dataset_yaml)
        self._validate_config(
            base_model=base_model,
            epochs=epochs,
            image_size=image_size,
            batch=batch,
            device=device,
            patience=patience,
        )
        run_id = f"train_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid4().hex[:8]}"
        config = {
            "dataset_yaml": dataset_path.relative_to(self._dataset_root).as_posix(),
            "base_model": base_model,
            "epochs": epochs,
            "image_size": image_size,
            "batch": batch,
            "device": device,
            "patience": patience,
        }

        with self._lock:
            if self._state["status"] == "running":
                raise AppError(
                    ErrorCode.TRAINING_NOT_READY,
                    "A training run is already active.",
                    status_code=409,
                    details={"active_run_id": self._state["active_run_id"]},
                )
            self._state = {
                "active_run_id": run_id,
                "progress": 0,
                "status": "running",
                "message": "Training process is starting with automatic early stopping enabled.",
                "started_at_ms": int(datetime.now(timezone.utc).timestamp() * 1000),
                "finished_at_ms": None,
                "config": config,
                "output_path": f"outputs/training/{run_id}",
                "best_model_path": None,
                "error": None,
                "history": [],
                "completed_epochs": 0,
                "early_stopping": {
                    "enabled": True,
                    "patience": patience,
                    "epochs_without_improvement": 0,
                    "best_epoch": None,
                    "best_fitness": None,
                    "converged": False,
                    "stopped_early": False,
                },
            }

        Thread(
            target=self._run_training,
            kwargs={"run_id": run_id, "dataset_path": dataset_path, **config},
            daemon=True,
            name=f"aitl-{run_id}",
        ).start()
        logger.info(
            "YOLO training run queued",
            extra={"run_id": run_id, "dataset_yaml": config["dataset_yaml"], "patience": patience},
        )
        return self.status()

    def _run_training(
        self,
        *,
        run_id: str,
        dataset_path: Path,
        dataset_yaml: str,
        base_model: str,
        epochs: int,
        image_size: int,
        batch: int,
        device: str,
        patience: int,
    ) -> None:
        del dataset_yaml
        convergence = {"best_fitness": None, "best_epoch": None, "without_improvement": 0}
        try:
            factory = self._yolo_factory or self._import_yolo
            model = factory(base_model)

            def update_epoch(trainer: Any) -> None:
                epoch = int(getattr(trainer, "epoch", 0)) + 1
                progress = min(99, round(epoch / epochs * 100))
                with self._lock:
                    if self._state["active_run_id"] == run_id:
                        self._state["progress"] = progress
                        self._state["completed_epochs"] = max(self._state.get("completed_epochs", 0), epoch)
                        self._state["message"] = f"Training epoch {epoch} of {epochs}."

            def update_fit_epoch(trainer: Any) -> None:
                epoch = int(getattr(trainer, "epoch", 0)) + 1
                metrics = dict(getattr(trainer, "metrics", {}) or {})
                train_metrics: dict[str, Any] = {}
                label_loss_items = getattr(trainer, "label_loss_items", None)
                if callable(label_loss_items):
                    try:
                        train_metrics = dict(label_loss_items(getattr(trainer, "tloss", None), prefix="train") or {})
                    except Exception:  # metrics are diagnostic and must never break the training run
                        train_metrics = {}

                fitness = _number(getattr(trainer, "fitness", None))
                if fitness is None:
                    fitness = _number(metrics.get("fitness"))
                if fitness is None:
                    # Ultralytics also invokes on_fit_epoch_end during final best-model
                    # evaluation, where per-epoch fitness may be absent. Do not overwrite
                    # the real epoch history point with that final evaluation callback.
                    with self._lock:
                        if any(item.get("epoch") == epoch for item in self._state.get("history", [])):
                            return
                map50_95 = _number(metrics.get("metrics/mAP50-95(B)"))
                map50 = _number(metrics.get("metrics/mAP50(B)"))
                train_loss = _loss_total(train_metrics, "train/")
                val_loss = _loss_total(metrics, "val/")

                previous_best = convergence["best_fitness"]
                if fitness is not None and (previous_best is None or fitness > float(previous_best) + 1e-12):
                    convergence["best_fitness"] = fitness
                    convergence["best_epoch"] = epoch
                    convergence["without_improvement"] = 0
                elif fitness is not None:
                    convergence["without_improvement"] = int(convergence["without_improvement"]) + 1

                point = {
                    "epoch": epoch,
                    "fitness": fitness,
                    "best_fitness": convergence["best_fitness"],
                    "map50_95": map50_95,
                    "map50": map50,
                    "train_loss": train_loss,
                    "val_loss": val_loss,
                }
                with self._lock:
                    if self._state["active_run_id"] != run_id:
                        return
                    history = [item for item in self._state.get("history", []) if item.get("epoch") != epoch]
                    history.append(point)
                    history.sort(key=lambda item: item["epoch"])
                    self._state["history"] = history
                    self._state["completed_epochs"] = max(self._state.get("completed_epochs", 0), epoch)
                    self._state["early_stopping"] = {
                        "enabled": True,
                        "patience": patience,
                        "epochs_without_improvement": convergence["without_improvement"],
                        "best_epoch": convergence["best_epoch"],
                        "best_fitness": convergence["best_fitness"],
                        "converged": int(convergence["without_improvement"]) >= patience,
                        "stopped_early": False,
                    }

            if hasattr(model, "add_callback"):
                model.add_callback("on_train_epoch_end", update_epoch)
                model.add_callback("on_fit_epoch_end", update_fit_epoch)

            self._output_root.mkdir(parents=True, exist_ok=True)
            model.train(
                data=str(dataset_path),
                epochs=epochs,
                imgsz=image_size,
                batch=batch,
                device=device,
                patience=patience,
                project=str(self._output_root),
                name=run_id,
                exist_ok=False,
                plots=True,
            )
            best_model = self._output_root / run_id / "weights" / "best.pt"
            with self._lock:
                completed_epochs = int(self._state.get("completed_epochs", 0))
                stopped_early = completed_epochs > 0 and completed_epochs < epochs
                early = dict(self._state.get("early_stopping", {}))
                early["stopped_early"] = stopped_early
                early["converged"] = bool(stopped_early or early.get("converged"))
                self._state.update(
                    {
                        "progress": 100,
                        "status": "early_stopped" if stopped_early else "completed",
                        "message": (
                            f"Training stopped early after convergence at epoch {completed_epochs} of {epochs}."
                            if stopped_early
                            else "Training completed the requested epochs."
                        ),
                        "finished_at_ms": int(datetime.now(timezone.utc).timestamp() * 1000),
                        "best_model_path": f"outputs/training/{run_id}/weights/best.pt" if best_model.exists() else None,
                        "early_stopping": early,
                    }
                )
            logger.info(
                "YOLO training run finished",
                extra={"run_id": run_id, "completed_epochs": completed_epochs, "stopped_early": stopped_early},
            )
        except Exception as exc:  # Ultralytics exposes several backend-specific exception types.
            logger.exception(
                "YOLO training run failed",
                extra={"run_id": run_id, "error_code": ErrorCode.TRAINING_RUN_FAILED.value},
            )
            with self._lock:
                self._state.update(
                    {
                        "status": "failed",
                        "message": "Training failed. Check the backend log and dataset configuration.",
                        "finished_at_ms": int(datetime.now(timezone.utc).timestamp() * 1000),
                        "error": str(exc)[:500],
                    }
                )

    def _resolve_dataset_path(self, dataset_yaml: str) -> Path:
        requested = Path(dataset_yaml)
        if requested.is_absolute() or requested.suffix.lower() not in {".yaml", ".yml"}:
            raise AppError(
                ErrorCode.TRAINING_CONFIG_INVALID,
                "dataset_yaml must be a relative .yaml or .yml path inside the datasets folder.",
                status_code=422,
            )
        resolved = (self._dataset_root / requested).resolve()
        if not resolved.is_relative_to(self._dataset_root):
            raise AppError(
                ErrorCode.TRAINING_CONFIG_INVALID,
                "The YOLO dataset configuration must stay inside the datasets folder.",
                status_code=422,
                details={"dataset_yaml": dataset_yaml},
            )
        return resolved

    @staticmethod
    def _validate_dataset_yaml(resolved: Path, dataset_yaml: str) -> None:
        if not resolved.is_file():
            raise AppError(
                ErrorCode.TRAINING_CONFIG_INVALID,
                "The labeled YOLO dataset configuration was not found inside the datasets folder.",
                status_code=422,
                details={"dataset_yaml": dataset_yaml},
            )
        try:
            config_text = resolved.read_text(encoding="utf-8")
        except OSError as exc:
            raise AppError(
                ErrorCode.DATASET_READ_FAILED,
                "Failed to read the YOLO dataset configuration.",
                status_code=500,
            ) from exc
        required_keys = ("train", "val")
        missing = [key for key in required_keys if re.search(rf"(?m)^\s*{key}\s*:", config_text) is None]
        has_classes = re.search(r"(?m)^\s*(?:names|nc)\s*:", config_text) is not None
        if missing or not has_classes:
            raise AppError(
                ErrorCode.TRAINING_CONFIG_INVALID,
                "The YOLO dataset YAML must define train, val, and names or nc.",
                status_code=422,
                details={"missing_keys": missing + ([] if has_classes else ["names_or_nc"])},
            )

    @staticmethod
    def _validate_config(
        *, base_model: str, epochs: int, image_size: int, batch: int, device: str, patience: int
    ) -> None:
        if not MODEL_NAME_PATTERN.fullmatch(base_model):
            raise AppError(
                ErrorCode.TRAINING_CONFIG_INVALID,
                "base_model must be a local model filename or an Ultralytics model name ending in .pt or .yaml.",
                status_code=422,
            )
        if (
            not 1 <= epochs <= 300
            or not 64 <= image_size <= 2048
            or not 1 <= batch <= 128
            or not 1 <= patience <= 100
        ):
            raise AppError(
                ErrorCode.TRAINING_CONFIG_INVALID,
                "Training values are outside the supported prototype limits.",
                status_code=422,
            )
        if not DEVICE_PATTERN.fullmatch(device):
            raise AppError(
                ErrorCode.TRAINING_CONFIG_INVALID,
                "device must be cpu, mps, or a comma-separated numeric accelerator index.",
                status_code=422,
            )

    def _training_available(self) -> bool:
        return self._yolo_factory is not None or importlib.util.find_spec("ultralytics") is not None

    @staticmethod
    def _import_yolo(model_name: str) -> Any:
        from ultralytics import YOLO

        return YOLO(model_name)


training_service = TrainingService()
