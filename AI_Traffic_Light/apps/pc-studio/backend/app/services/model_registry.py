from __future__ import annotations

from dataclasses import asdict, dataclass
import os
from pathlib import Path
import shutil
from threading import RLock
from typing import Any

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.core.json_store import read_json, write_json_atomic
from app.core.logging_config import get_logger

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "outputs" / "training"
MODEL_GLOB = "*/weights/best.pt"
REGISTRY_FILENAME = ".aitl_model_registry.json"


@dataclass(frozen=True)
class ModelRecord:
    model_id: str
    model_path: str
    modified_at_ms: int
    size_bytes: int
    run_path: str
    is_latest: bool = False
    is_default: bool = False
    is_active: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ModelRegistryService:
    """Discover, persist selection metadata, and delete local trained models."""

    def __init__(self, *, output_root: Path | None = None) -> None:
        configured_output_root = os.environ.get("AITL_TRAINING_OUTPUT_DIR")
        self._output_root = Path(configured_output_root) if configured_output_root else (output_root or DEFAULT_OUTPUT_ROOT)
        self._output_root = self._output_root.expanduser().resolve()
        self._registry_path = self._output_root / REGISTRY_FILENAME
        self._lock = RLock()

    def status(self, *, active_model_id: str | None = None) -> dict[str, Any]:
        with self._lock:
            default_model_id = self.default_model_id()
            models = self.discover_models(default_model_id=default_model_id, active_model_id=active_model_id)
            return {
                "default_model_id": default_model_id,
                "active_model_id": active_model_id,
                "total": len(models),
                "models": [item.to_dict() for item in models],
            }

    def discover_models(
        self,
        *,
        default_model_id: str | None = None,
        active_model_id: str | None = None,
    ) -> list[ModelRecord]:
        with self._lock:
            if not self._output_root.exists():
                return []
            models: list[ModelRecord] = []
            for path in self._output_root.glob(MODEL_GLOB):
                if not path.is_file():
                    continue
                try:
                    stat = path.stat()
                    relative = path.relative_to(self._output_root).as_posix()
                    run_dir = path.parents[1]
                    run_relative = run_dir.relative_to(self._output_root).as_posix()
                    model_id = run_dir.name
                except OSError:
                    continue
                models.append(
                    ModelRecord(
                        model_id=model_id,
                        model_path=f"outputs/training/{relative}",
                        modified_at_ms=int(stat.st_mtime * 1000),
                        size_bytes=stat.st_size,
                        run_path=f"outputs/training/{run_relative}",
                        is_default=model_id == default_model_id,
                        is_active=model_id == active_model_id,
                    )
                )
            models.sort(key=lambda item: (item.modified_at_ms, item.model_id), reverse=True)
            if models:
                latest_id = models[0].model_id
                models = [
                    ModelRecord(**{**item.to_dict(), "is_latest": item.model_id == latest_id})
                    for item in models
                ]
            return models

    def default_model_id(self) -> str | None:
        with self._lock:
            payload = self._read_registry_payload()
            value = payload.get("default_model_id")
            return value if isinstance(value, str) and value else None

    def set_default_model(self, model_id: str) -> dict[str, Any]:
        with self._lock:
            self.path_for_model(model_id)
            self._write_registry_payload({"default_model_id": model_id})
            logger.info("Default inference model set", extra={"model_id": model_id})
            return self.status(active_model_id=None)

    def clear_default_model(self) -> None:
        with self._lock:
            self._write_registry_payload({"default_model_id": None})

    def path_for_model(self, model_id: str) -> Path:
        with self._lock:
            path = (self._output_root / model_id / "weights" / "best.pt").resolve()
            if not path.is_relative_to(self._output_root) or not path.is_file():
                raise AppError(
                    ErrorCode.MODEL_VERSION_NOT_FOUND,
                    "The requested trained model was not found under outputs/training.",
                    status_code=404,
                    details={"model_id": model_id},
                )
            return path

    def delete_model(self, model_id: str) -> dict[str, Any]:
        with self._lock:
            model_path = self.path_for_model(model_id)
            run_dir = model_path.parents[1]
            try:
                shutil.rmtree(run_dir)
            except OSError as exc:
                raise AppError(
                    ErrorCode.MODEL_DELETE_FAILED,
                    "Failed to delete the selected trained model directory.",
                    status_code=500,
                    details={"model_id": model_id},
                ) from exc
            if self.default_model_id() == model_id:
                self.clear_default_model()
            logger.info("Trained model directory deleted", extra={"model_id": model_id, "run_dir": str(run_dir)})
            return self.status(active_model_id=None)

    def _read_registry_payload(self) -> dict[str, Any]:
        if not self._registry_path.is_file():
            return {}
        try:
            payload = read_json(self._registry_path)
        except (OSError, ValueError) as exc:
            raise AppError(
                ErrorCode.MODEL_REGISTRY_READ_FAILED,
                "Failed to read the model registry metadata file.",
                status_code=500,
            ) from exc
        return payload if isinstance(payload, dict) else {}

    def _write_registry_payload(self, payload: dict[str, Any]) -> None:
        try:
            write_json_atomic(self._registry_path, payload)
        except (OSError, TypeError, ValueError) as exc:
            raise AppError(
                ErrorCode.SETTINGS_WRITE_FAILED,
                "Failed to update the model registry metadata file.",
                status_code=500,
            ) from exc


model_registry_service = ModelRegistryService()
