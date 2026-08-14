from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import importlib.util
import os
from pathlib import Path
from threading import Lock
import time
from typing import Any, Callable

import cv2
import numpy as np

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.core.logging_config import get_logger
from app.services.camera_frames import CameraFrame
from app.services.model_registry import ModelRegistryService

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "outputs" / "training"
MODEL_CONFIDENCE_MIN = 0.01
DEFAULT_MODEL_CONFIDENCE = 0.10
YoloFactory = Callable[[str], Any]


@dataclass(frozen=True)
class TrainedModelSummary:
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


class InferenceService:
    """Load local trained YOLO weights and run detection on camera frames."""

    def __init__(
        self,
        *,
        output_root: Path | None = None,
        yolo_factory: YoloFactory | None = None,
        model_registry: ModelRegistryService | None = None,
    ) -> None:
        configured_output_root = os.environ.get("AITL_TRAINING_OUTPUT_DIR")
        self._output_root = Path(configured_output_root) if configured_output_root else (output_root or DEFAULT_OUTPUT_ROOT)
        self._output_root = self._output_root.expanduser().resolve()
        self._yolo_factory = yolo_factory
        self._registry = model_registry or ModelRegistryService(output_root=self._output_root)
        self._state_lock = Lock()
        self._inference_lock = Lock()
        self._model: Any | None = None
        self._active_model_path: Path | None = None
        self._active_model_id: str | None = None
        self._loaded_at_ms: int | None = None
        self._last_latency_ms: float | None = None
        self._last_frame_number: int | None = None
        self._last_detection_key: tuple[str, int, float] | None = None
        self._last_detection_frame: dict[str, Any] | None = None
        self._last_source_frame: CameraFrame | None = None
        self._source_frame_cache: dict[tuple[str, int], CameraFrame] = {}
        self._last_error: str | None = None

    def status(self) -> dict[str, Any]:
        with self._state_lock:
            active_path = self._active_model_path
            active_id = self._active_model_id
            state = {
                "model_loaded": self._model is not None,
                "active_model_id": active_id,
                "active_model_path": self._display_model_path(active_path) if active_path else None,
                "loaded_at_ms": self._loaded_at_ms,
                "last_latency_ms": self._last_latency_ms,
                "last_frame_number": self._last_frame_number,
                "error": self._last_error,
            }
        registry_status = self._registry.status(active_model_id=active_id)
        models = registry_status["models"]
        latest_model_path = models[0]["model_path"] if models else None
        default_model_id = registry_status.get("default_model_id")
        default_model_path = next((item["model_path"] for item in models if item["model_id"] == default_model_id), None)
        state.update(
            {
                "backend": "ultralytics_yolo",
                "backend_available": self._backend_available(),
                "available_model_count": registry_status["total"],
                "latest_model_path": latest_model_path,
                "default_model_id": default_model_id,
                "default_model_path": default_model_path,
                "active_is_latest": bool(active_path and latest_model_path and self._display_model_path(active_path) == latest_model_path),
                "confidence_floor": MODEL_CONFIDENCE_MIN,
                "default_confidence": DEFAULT_MODEL_CONFIDENCE,
                "models": models,
            }
        )
        return state

    def discover_models(self) -> list[TrainedModelSummary]:
        models = self._registry.status(active_model_id=self._active_model_id).get("models", [])
        return [TrainedModelSummary(**item) for item in models]

    def load_latest(self) -> dict[str, Any]:
        models = self.discover_models()
        if not models:
            raise AppError(
                ErrorCode.MODEL_VERSION_NOT_FOUND,
                "No trained best.pt model was found under outputs/training.",
                status_code=404,
                details={"expected_pattern": "outputs/training/<run_id>/weights/best.pt"},
            )
        return self.load_model(models[0].model_id)

    def load_selected(self, model_id: str) -> dict[str, Any]:
        return self.load_model(model_id)

    def load_default_or_latest(self) -> dict[str, Any]:
        default_model_id = self._registry.default_model_id()
        if default_model_id:
            try:
                return self.load_model(default_model_id)
            except AppError as exc:
                if exc.code != ErrorCode.MODEL_VERSION_NOT_FOUND:
                    raise
        return self.load_latest()

    def load_model(self, model_id: str) -> dict[str, Any]:
        if not self._backend_available():
            raise AppError(
                ErrorCode.MODEL_NOT_LOADED,
                "Ultralytics is not installed. Install requirements-training.txt before loading a trained model.",
                status_code=503,
            )
        model_path = self._registry.path_for_model(model_id)
        display_path = self._display_model_path(model_path)
        try:
            with self._inference_lock:
                factory = self._yolo_factory or self._import_yolo
                model = factory(str(model_path))
        except Exception as exc:
            logger.exception(
                "Trained model load failed",
                extra={"error_code": ErrorCode.INFERENCE_FAILED.value, "model_id": model_id},
            )
            with self._state_lock:
                self._last_error = str(exc)[:500]
            raise AppError(
                ErrorCode.INFERENCE_FAILED,
                "Failed to load the selected trained YOLO model.",
                status_code=500,
                details={"model_id": model_id, "model_path": display_path},
            ) from exc

        with self._state_lock:
            self._model = model
            self._active_model_path = model_path
            self._active_model_id = model_id
            self._loaded_at_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            self._last_latency_ms = None
            self._last_frame_number = None
            self._last_detection_key = None
            self._last_detection_frame = None
            self._last_source_frame = None
            self._source_frame_cache.clear()
            self._last_error = None

        logger.info("Inference model loaded", extra={"model_id": model_id, "model_path": display_path})
        return self.status()

    def unload(self) -> dict[str, Any]:
        with self._inference_lock:
            with self._state_lock:
                active_model_id = self._active_model_id
                self._model = None
                self._active_model_path = None
                self._active_model_id = None
                self._loaded_at_ms = None
                self._last_latency_ms = None
                self._last_frame_number = None
                self._last_detection_key = None
                self._last_detection_frame = None
                self._last_source_frame = None
                self._source_frame_cache.clear()
                self._last_error = None
        logger.info("Inference model unloaded", extra={"model_id": active_model_id})
        return self.status()

    def set_default_model(self, model_id: str) -> dict[str, Any]:
        return self._registry.set_default_model(model_id)

    def delete_model(self, model_id: str) -> dict[str, Any]:
        with self._state_lock:
            active_model_id = self._active_model_id
        if active_model_id == model_id:
            self.unload()
        return self._registry.delete_model(model_id)

    def detect_frame(self, frame: CameraFrame | None, *, confidence_threshold: float | None = None) -> dict[str, Any]:
        if frame is None:
            raise AppError(
                ErrorCode.INFERENCE_SOURCE_MISSING,
                "No camera frame is available for inference. Upload a frame or start simulation mode.",
                status_code=409,
            )

        effective_confidence = round(max(MODEL_CONFIDENCE_MIN, min(1.0, confidence_threshold or DEFAULT_MODEL_CONFIDENCE)), 4)
        detection_key = (frame.source_id, frame.frame_number, effective_confidence)
        with self._state_lock:
            if self._model is None:
                raise AppError(
                    ErrorCode.MODEL_NOT_LOADED,
                    "No trained model is loaded. Load a trained model first.",
                    status_code=409,
                )
            if self._last_detection_key == detection_key and self._last_detection_frame is not None:
                return dict(self._last_detection_frame)

        with self._inference_lock:
            with self._state_lock:
                model = self._model
                if model is None:
                    raise AppError(
                        ErrorCode.MODEL_NOT_LOADED,
                        "The inference model was unloaded before detection could start.",
                        status_code=409,
                    )
                if self._last_detection_key == detection_key and self._last_detection_frame is not None:
                    return dict(self._last_detection_frame)

            image_array = np.frombuffer(frame.content, dtype=np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            if image is None:
                raise AppError(
                    ErrorCode.INFERENCE_SOURCE_MISSING,
                    "The current camera frame could not be decoded for inference.",
                    status_code=422,
                    details={"content_type": frame.content_type},
                )

            started = time.perf_counter()
            try:
                results = model.predict(source=image, conf=effective_confidence, verbose=False)
                detection_frame = self._convert_results(frame, results, model)
            except AppError:
                raise
            except Exception as exc:
                logger.exception(
                    "Live frame inference failed",
                    extra={"error_code": ErrorCode.INFERENCE_FAILED.value, "frame_number": frame.frame_number},
                )
                with self._state_lock:
                    self._last_error = str(exc)[:500]
                raise AppError(
                    ErrorCode.INFERENCE_FAILED,
                    "YOLO inference failed for the current camera frame.",
                    status_code=500,
                    details={"frame_number": frame.frame_number},
                ) from exc
            latency_ms = round((time.perf_counter() - started) * 1000, 2)

            with self._state_lock:
                self._last_latency_ms = latency_ms
                self._last_frame_number = frame.frame_number
                self._last_detection_key = detection_key
                self._last_detection_frame = detection_frame
                self._last_source_frame = frame
                self._source_frame_cache[(frame.source_id, frame.frame_number)] = frame
                while len(self._source_frame_cache) > 8:
                    oldest_key = next(iter(self._source_frame_cache))
                    self._source_frame_cache.pop(oldest_key, None)
                self._last_error = None

        logger.info(
            "Live frame inference completed",
            extra={
                "model_id": self._active_model_id,
                "frame_number": frame.frame_number,
                "detection_count": len(detection_frame["detections"]),
                "latency_ms": latency_ms,
                "confidence": effective_confidence,
            },
        )
        return dict(detection_frame)

    def source_frame(self, *, source_id: str | None = None, frame_number: int | None = None) -> CameraFrame:
        if (source_id is None) != (frame_number is None):
            raise AppError(
                ErrorCode.INVALID_REQUEST,
                "source_id and frame_number must be supplied together when requesting an exact inferred frame.",
                status_code=422,
            )
        with self._state_lock:
            if source_id is not None and frame_number is not None:
                frame = self._source_frame_cache.get((source_id, frame_number))
            else:
                frame = self._last_source_frame
        if frame is None:
            raise AppError(
                ErrorCode.INFERENCE_SOURCE_MISSING,
                "The requested inferred source frame is no longer available.",
                status_code=404,
                details={"source_id": source_id, "frame_number": frame_number},
            )
        return frame

    def last_source_frame(self) -> CameraFrame:
        return self.source_frame()

    @staticmethod
    def _convert_results(frame: CameraFrame, results: Any, model: Any) -> dict[str, Any]:
        if not results:
            raise AppError(
                ErrorCode.INFERENCE_RESULT_INVALID,
                "The inference backend returned no result object.",
                status_code=500,
            )
        result = results[0]
        boxes = getattr(result, "boxes", None)
        names = getattr(result, "names", getattr(model, "names", {}))
        detections: list[dict[str, Any]] = []

        if boxes is not None:
            try:
                xyxy_values = boxes.xyxy.cpu().tolist()
                confidence_values = boxes.conf.cpu().tolist()
                class_values = boxes.cls.cpu().tolist()
            except Exception as exc:
                raise AppError(
                    ErrorCode.INFERENCE_RESULT_INVALID,
                    "The inference backend returned an unsupported detection result shape.",
                    status_code=500,
                ) from exc

            for index, (xyxy, confidence, class_value) in enumerate(
                zip(xyxy_values, confidence_values, class_values, strict=False)
            ):
                if len(xyxy) != 4:
                    continue
                class_id = int(class_value)
                x1 = max(0, min(frame.width, int(round(float(xyxy[0])))))
                y1 = max(0, min(frame.height, int(round(float(xyxy[1])))))
                x2 = max(0, min(frame.width, int(round(float(xyxy[2])))))
                y2 = max(0, min(frame.height, int(round(float(xyxy[3])))))
                if x2 <= x1 or y2 <= y1:
                    continue
                detections.append(
                    {
                        "id": f"live-{frame.frame_number}-{index}",
                        "class_id": class_id,
                        "class_name": InferenceService._class_name(names, class_id),
                        "confidence": max(0.0, min(1.0, float(confidence))),
                        "box_xyxy": [x1, y1, x2, y2],
                    }
                )

        return {
            "frame_id": f"camera-{frame.source_id}-{frame.frame_number}",
            "source_id": frame.source_id,
            "image_width": frame.width,
            "image_height": frame.height,
            "timestamp_ms": frame.received_at_ms,
            "source_frame_number": frame.frame_number,
            "detections": detections,
        }

    @staticmethod
    def _class_name(names: Any, class_id: int) -> str:
        if isinstance(names, dict):
            return str(names.get(class_id, f"class_{class_id}"))
        if isinstance(names, (list, tuple)) and 0 <= class_id < len(names):
            return str(names[class_id])
        return f"class_{class_id}"

    def _backend_available(self) -> bool:
        return self._yolo_factory is not None or importlib.util.find_spec("ultralytics") is not None

    def _display_model_path(self, path: Path) -> str:
        try:
            relative = path.relative_to(self._output_root).as_posix()
        except ValueError:
            return "outputs/training/<external>"
        return f"outputs/training/{relative}"

    @staticmethod
    def _import_yolo(model_path: str) -> Any:
        from ultralytics import YOLO

        return YOLO(model_path)


inference_service = InferenceService()
