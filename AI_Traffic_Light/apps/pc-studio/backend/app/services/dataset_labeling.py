from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
from threading import Lock
from typing import Any
from uuid import uuid4

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.core.logging_config import get_logger

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_DATASET_ROOT = PROJECT_ROOT / "datasets"
DEFAULT_CLASS_SCHEMA = PROJECT_ROOT / "packages" / "schema" / "classes.default.json"
CAPTURE_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,160}$")
SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".svg"}
MAX_LABELS_PER_FRAME = 500


class DatasetLabelingService:
    """Review captured frames, persist manual boxes, and build a managed YOLO dataset."""

    def __init__(
        self,
        *,
        dataset_root: Path | None = None,
        class_schema_path: Path | None = None,
    ) -> None:
        configured_root = os.environ.get("AITL_DATASET_DIR")
        self._dataset_root = Path(configured_root) if configured_root else (dataset_root or DEFAULT_DATASET_ROOT)
        self._dataset_root = self._dataset_root.expanduser().resolve()
        self._capture_root = self._dataset_root / "captures"
        self._managed_yolo_root = self._dataset_root / "yolo"
        self._class_schema_path = (class_schema_path or DEFAULT_CLASS_SCHEMA).expanduser().resolve()
        self._lock = Lock()

    @property
    def dataset_root(self) -> Path:
        return self._dataset_root

    def classes(self) -> list[dict[str, Any]]:
        try:
            payload = json.loads(self._class_schema_path.read_text(encoding="utf-8"))
            classes = payload.get("classes")
        except (OSError, json.JSONDecodeError) as exc:
            logger.exception(
                "Dataset class schema could not be read",
                extra={"error_code": ErrorCode.DATASET_READ_FAILED.value},
            )
            raise AppError(
                ErrorCode.DATASET_READ_FAILED,
                "Failed to read the shared dataset class schema.",
                status_code=500,
            ) from exc
        if not isinstance(classes, list) or not classes:
            raise AppError(
                ErrorCode.DATASET_READ_FAILED,
                "The shared dataset class schema is empty or invalid.",
                status_code=500,
            )
        normalized: list[dict[str, Any]] = []
        for expected_id, item in enumerate(classes):
            if not isinstance(item, dict) or item.get("id") != expected_id or not isinstance(item.get("name"), str):
                raise AppError(
                    ErrorCode.DATASET_READ_FAILED,
                    "Dataset class IDs must be contiguous and start at zero.",
                    status_code=500,
                )
            normalized.append(
                {
                    "id": expected_id,
                    "name": item["name"],
                    "category": str(item.get("category", "object")),
                }
            )
        return normalized

    def list_captures(self, *, limit: int = 200, session_id: str | None = None) -> dict[str, Any]:
        if not 1 <= limit <= 1000:
            raise AppError(
                ErrorCode.INVALID_REQUEST,
                "limit must be between 1 and 1000.",
                status_code=422,
            )
        if session_id is not None and not SESSION_ID_PATTERN.fullmatch(session_id):
            raise AppError(
                ErrorCode.INVALID_REQUEST,
                "session_id must contain 1-64 letters, numbers, dots, dashes, or underscores.",
                status_code=422,
            )

        records: list[dict[str, Any]] = []
        if self._capture_root.exists():
            metadata_glob = f"{session_id}/metadata/*.json" if session_id else "*/metadata/*.json"
            for metadata_path in self._capture_root.glob(metadata_glob):
                try:
                    record = self._read_json(metadata_path)
                    capture_id = str(record["capture_id"])
                    label_path = self._label_path(record)
                    labels = self._read_label_document(label_path) if label_path.is_file() else None
                    records.append(
                        {
                            **record,
                            "labeled": labels is not None,
                            "label_count": len(labels.get("labels", [])) if labels else 0,
                            "image_url": f"/api/dataset/captures/{capture_id}/image",
                        }
                    )
                except (KeyError, TypeError, ValueError, json.JSONDecodeError, OSError):
                    logger.warning("Skipping unreadable capture metadata", extra={"path": str(metadata_path)})

        records.sort(key=lambda item: (int(item.get("captured_at_ms", 0)), str(item.get("capture_id", ""))), reverse=True)
        total = len(records)
        return {"captures": records[:limit], "total": total, "classes": self.classes()}

    def get_capture_image(self, capture_id: str) -> tuple[Path, str]:
        record = self._find_capture(capture_id)
        image_path = self._safe_dataset_path(str(record.get("image_path", "")))
        if not image_path.is_file() or image_path.suffix.lower() not in IMAGE_SUFFIXES:
            raise AppError(
                ErrorCode.DATASET_ITEM_NOT_FOUND,
                "The captured image was not found.",
                status_code=404,
                details={"capture_id": capture_id},
            )
        return image_path, str(record.get("content_type", "application/octet-stream"))

    def get_labels(self, capture_id: str) -> dict[str, Any]:
        record = self._find_capture(capture_id)
        label_path = self._label_path(record)
        if label_path.is_file():
            try:
                return self._read_label_document(label_path)
            except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
                raise AppError(
                    ErrorCode.DATASET_READ_FAILED,
                    "Failed to read saved labels for this capture.",
                    status_code=500,
                    details={"capture_id": capture_id},
                ) from exc
        return self._empty_label_document(record)

    def save_labels(self, capture_id: str, labels: list[dict[str, Any]]) -> dict[str, Any]:
        record = self._find_capture(capture_id)
        class_map = {item["id"]: item for item in self.classes()}
        width = int(record.get("width", 0))
        height = int(record.get("height", 0))
        if width <= 0 or height <= 0:
            raise AppError(
                ErrorCode.DATASET_LABEL_INVALID,
                "The capture resolution is invalid, so bounding boxes cannot be saved.",
                status_code=422,
                details={"capture_id": capture_id},
            )
        if len(labels) > MAX_LABELS_PER_FRAME:
            raise AppError(
                ErrorCode.DATASET_LABEL_INVALID,
                f"A frame cannot contain more than {MAX_LABELS_PER_FRAME} labels.",
                status_code=422,
            )

        normalized_labels: list[dict[str, Any]] = []
        for index, label in enumerate(labels):
            class_id = label.get("class_id")
            box = label.get("box_xyxy")
            if class_id not in class_map:
                raise AppError(
                    ErrorCode.DATASET_LABEL_INVALID,
                    "A label uses a class ID that is not in the shared class schema.",
                    status_code=422,
                    details={"index": index, "class_id": class_id},
                )
            if not isinstance(box, (list, tuple)) or len(box) != 4:
                raise AppError(
                    ErrorCode.DATASET_LABEL_INVALID,
                    "Each bounding box must contain x1, y1, x2, and y2.",
                    status_code=422,
                    details={"index": index},
                )
            try:
                x1, y1, x2, y2 = (float(value) for value in box)
            except (TypeError, ValueError) as exc:
                raise AppError(
                    ErrorCode.DATASET_LABEL_INVALID,
                    "Bounding-box coordinates must be numeric.",
                    status_code=422,
                    details={"index": index},
                ) from exc
            if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
                raise AppError(
                    ErrorCode.DATASET_LABEL_INVALID,
                    "Bounding boxes must stay inside the captured image and have positive area.",
                    status_code=422,
                    details={"index": index, "box_xyxy": [x1, y1, x2, y2], "width": width, "height": height},
                )
            class_info = class_map[int(class_id)]
            normalized_labels.append(
                {
                    "class_id": int(class_id),
                    "class_name": class_info["name"],
                    "box_xyxy": [x1, y1, x2, y2],
                }
            )

        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        document = {
            "capture_id": capture_id,
            "session_id": record["session_id"],
            "image_path": record["image_path"],
            "width": width,
            "height": height,
            "reviewed": True,
            "updated_at_ms": now_ms,
            "labels": normalized_labels,
        }
        label_path = self._label_path(record)
        with self._lock:
            try:
                self._atomic_write_json(label_path, document)
            except OSError as exc:
                logger.exception(
                    "Dataset label write failed",
                    extra={"error_code": ErrorCode.DATASET_WRITE_FAILED.value, "capture_id": capture_id},
                )
                raise AppError(
                    ErrorCode.DATASET_WRITE_FAILED,
                    "Failed to save labels for the captured frame.",
                    status_code=500,
                    details={"capture_id": capture_id},
                ) from exc

        logger.info(
            "Dataset labels saved",
            extra={"capture_id": capture_id, "label_count": len(normalized_labels)},
        )
        return document

    def training_dataset_status(self) -> dict[str, Any]:
        items = self._labeled_items()
        eligible = [item for item in items if item["record"].get("quality_tag") != "bad"]
        excluded_bad_count = len(items) - len(eligible)
        box_count = sum(len(item["labels"].get("labels", [])) for item in eligible)
        signature = self._source_signature(eligible)
        manifest_path = self._managed_yolo_root / "manifest.json"
        data_yaml_path = self._managed_yolo_root / "data.yaml"
        manifest: dict[str, Any] | None = None
        if manifest_path.is_file():
            try:
                manifest = self._read_json(manifest_path)
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                manifest = None

        generated = bool(manifest and data_yaml_path.is_file())
        stale = generated and manifest.get("source_signature") != signature
        ready = generated and not stale and len(eligible) >= 2
        return {
            "ready": ready,
            "stale": stale,
            "dataset_yaml": "yolo/data.yaml",
            "labeled_frame_count": len(items),
            "eligible_frame_count": len(eligible),
            "excluded_bad_count": excluded_bad_count,
            "label_box_count": box_count,
            "train_count": int(manifest.get("train_count", 0)) if manifest else 0,
            "val_count": int(manifest.get("val_count", 0)) if manifest else 0,
            "generated_at_ms": manifest.get("generated_at_ms") if manifest else None,
            "classes": self.classes(),
            "message": self._training_status_message(
                generated=generated,
                stale=stale,
                eligible_count=len(eligible),
            ),
        }

    def build_training_dataset(self, *, validation_fraction: float = 0.2) -> dict[str, Any]:
        if not 0 < validation_fraction < 0.5:
            raise AppError(
                ErrorCode.INVALID_REQUEST,
                "validation_fraction must be greater than 0 and less than 0.5.",
                status_code=422,
            )
        items = [item for item in self._labeled_items() if item["record"].get("quality_tag") != "bad"]
        if len(items) < 2:
            raise AppError(
                ErrorCode.DATASET_TRAINING_NOT_READY,
                "At least two reviewed, non-bad captured frames are required to create distinct train and validation splits.",
                status_code=409,
                details={"eligible_frame_count": len(items)},
            )

        ordered = sorted(
            items,
            key=lambda item: hashlib.sha256(str(item["record"]["capture_id"]).encode("utf-8")).hexdigest(),
        )
        val_count = max(1, round(len(ordered) * validation_fraction))
        val_count = min(len(ordered) - 1, val_count)
        val_ids = {str(item["record"]["capture_id"]) for item in ordered[:val_count]}
        classes = self.classes()
        source_signature = self._source_signature(items)
        generated_at_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        build_root = self._dataset_root / f".yolo-build-{uuid4().hex}"
        backup_root = self._dataset_root / f".yolo-backup-{uuid4().hex}"

        with self._lock:
            try:
                for split in ("train", "val"):
                    (build_root / "images" / split).mkdir(parents=True, exist_ok=False)
                    (build_root / "labels" / split).mkdir(parents=True, exist_ok=False)

                split_records: dict[str, list[str]] = {"train": [], "val": []}
                for item in items:
                    record = item["record"]
                    label_document = item["labels"]
                    capture_id = str(record["capture_id"])
                    split = "val" if capture_id in val_ids else "train"
                    source_image = self._safe_dataset_path(str(record["image_path"]))
                    if not source_image.is_file():
                        raise AppError(
                            ErrorCode.DATASET_ITEM_NOT_FOUND,
                            "A labeled captured image is missing and the training dataset cannot be built.",
                            status_code=409,
                            details={"capture_id": capture_id},
                        )
                    destination_image = build_root / "images" / split / f"{capture_id}{source_image.suffix.lower()}"
                    destination_label = build_root / "labels" / split / f"{capture_id}.txt"
                    shutil.copy2(source_image, destination_image)
                    yolo_lines = self._to_yolo_lines(label_document)
                    destination_label.write_text("\n".join(yolo_lines) + ("\n" if yolo_lines else ""), encoding="utf-8")
                    split_records[split].append(capture_id)

                yaml_text = self._dataset_yaml(classes)
                (build_root / "data.yaml").write_text(yaml_text, encoding="utf-8")
                manifest = {
                    "format": "aitl-managed-yolo-v1",
                    "generated_at_ms": generated_at_ms,
                    "source_signature": source_signature,
                    "validation_fraction": validation_fraction,
                    "train_count": len(split_records["train"]),
                    "val_count": len(split_records["val"]),
                    "eligible_frame_count": len(items),
                    "label_box_count": sum(len(item["labels"].get("labels", [])) for item in items),
                    "train_capture_ids": sorted(split_records["train"]),
                    "val_capture_ids": sorted(split_records["val"]),
                    "classes": classes,
                    "dataset_yaml": "yolo/data.yaml",
                }
                (build_root / "manifest.json").write_text(
                    json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )

                if self._managed_yolo_root.exists():
                    os.replace(self._managed_yolo_root, backup_root)
                os.replace(build_root, self._managed_yolo_root)
                if backup_root.exists():
                    shutil.rmtree(backup_root, ignore_errors=True)
            except AppError:
                if build_root.exists():
                    shutil.rmtree(build_root, ignore_errors=True)
                if backup_root.exists() and not self._managed_yolo_root.exists():
                    os.replace(backup_root, self._managed_yolo_root)
                raise
            except (OSError, ValueError, TypeError) as exc:
                if build_root.exists():
                    shutil.rmtree(build_root, ignore_errors=True)
                if backup_root.exists() and not self._managed_yolo_root.exists():
                    try:
                        os.replace(backup_root, self._managed_yolo_root)
                    except OSError:
                        logger.exception("Failed to restore previous managed YOLO dataset")
                logger.exception(
                    "Managed YOLO dataset build failed",
                    extra={"error_code": ErrorCode.DATASET_BUILD_FAILED.value},
                )
                raise AppError(
                    ErrorCode.DATASET_BUILD_FAILED,
                    "Failed to build the managed YOLO training dataset.",
                    status_code=500,
                ) from exc

        logger.info(
            "Managed YOLO training dataset built",
            extra={"train_count": len(items) - val_count, "val_count": val_count},
        )
        return self.training_dataset_status()

    def _labeled_items(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        if not self._capture_root.exists():
            return items
        for metadata_path in self._capture_root.glob("*/metadata/*.json"):
            try:
                record = self._read_json(metadata_path)
                label_path = self._label_path(record)
                if not label_path.is_file():
                    continue
                labels = self._read_label_document(label_path)
                items.append({"record": record, "labels": labels})
            except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError):
                logger.warning("Skipping invalid labeled capture", extra={"path": str(metadata_path)})
        items.sort(key=lambda item: str(item["record"].get("capture_id", "")))
        return items

    def _find_capture(self, capture_id: str) -> dict[str, Any]:
        if not CAPTURE_ID_PATTERN.fullmatch(capture_id):
            raise AppError(
                ErrorCode.INVALID_REQUEST,
                "capture_id contains unsupported characters.",
                status_code=422,
            )
        matches = list(self._capture_root.glob(f"*/metadata/{capture_id}.json"))
        if not matches:
            raise AppError(
                ErrorCode.DATASET_ITEM_NOT_FOUND,
                "The requested captured frame was not found.",
                status_code=404,
                details={"capture_id": capture_id},
            )
        if len(matches) > 1:
            raise AppError(
                ErrorCode.DATASET_READ_FAILED,
                "Duplicate capture IDs were found in the dataset.",
                status_code=500,
                details={"capture_id": capture_id},
            )
        try:
            record = self._read_json(matches[0])
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise AppError(
                ErrorCode.DATASET_READ_FAILED,
                "Failed to read capture metadata.",
                status_code=500,
                details={"capture_id": capture_id},
            ) from exc
        if str(record.get("capture_id")) != capture_id:
            raise AppError(
                ErrorCode.DATASET_READ_FAILED,
                "Capture metadata does not match the requested capture ID.",
                status_code=500,
                details={"capture_id": capture_id},
            )
        return record

    def _label_path(self, record: dict[str, Any]) -> Path:
        session_id = str(record.get("session_id", ""))
        capture_id = str(record.get("capture_id", ""))
        if not SESSION_ID_PATTERN.fullmatch(session_id) or not CAPTURE_ID_PATTERN.fullmatch(capture_id):
            raise ValueError("Invalid capture metadata identifiers")
        return self._capture_root / session_id / "labels" / f"{capture_id}.json"

    def _safe_dataset_path(self, relative_path: str) -> Path:
        requested = Path(relative_path)
        if requested.is_absolute():
            raise AppError(
                ErrorCode.DATASET_READ_FAILED,
                "Dataset metadata contains an invalid absolute path.",
                status_code=500,
            )
        resolved = (self._dataset_root / requested).resolve()
        if not resolved.is_relative_to(self._dataset_root):
            raise AppError(
                ErrorCode.DATASET_READ_FAILED,
                "Dataset metadata contains a path outside the dataset root.",
                status_code=500,
            )
        return resolved

    @staticmethod
    def _empty_label_document(record: dict[str, Any]) -> dict[str, Any]:
        return {
            "capture_id": record["capture_id"],
            "session_id": record["session_id"],
            "image_path": record["image_path"],
            "width": int(record["width"]),
            "height": int(record["height"]),
            "reviewed": False,
            "updated_at_ms": None,
            "labels": [],
        }

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise TypeError("Expected JSON object")
        return payload

    @classmethod
    def _read_label_document(cls, path: Path) -> dict[str, Any]:
        payload = cls._read_json(path)
        if payload.get("reviewed") is not True or not isinstance(payload.get("labels"), list):
            raise ValueError("Invalid label document")
        return payload

    @staticmethod
    def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        try:
            with temporary_path.open("x", encoding="utf-8", newline="\n") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, path)
        finally:
            temporary_path.unlink(missing_ok=True)

    @staticmethod
    def _source_signature(items: list[dict[str, Any]]) -> str:
        digest = hashlib.sha256()
        for item in sorted(items, key=lambda current: str(current["record"]["capture_id"])):
            record = item["record"]
            labels = item["labels"]
            normalized = {
                "capture_id": record["capture_id"],
                "image_path": record["image_path"],
                "quality_tag": record.get("quality_tag"),
                "width": record.get("width"),
                "height": record.get("height"),
                "labels": labels.get("labels", []),
            }
            digest.update(json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        return digest.hexdigest()

    @staticmethod
    def _to_yolo_lines(label_document: dict[str, Any]) -> list[str]:
        width = float(label_document["width"])
        height = float(label_document["height"])
        lines: list[str] = []
        for label in label_document.get("labels", []):
            x1, y1, x2, y2 = (float(value) for value in label["box_xyxy"])
            x_center = ((x1 + x2) / 2) / width
            y_center = ((y1 + y2) / 2) / height
            box_width = (x2 - x1) / width
            box_height = (y2 - y1) / height
            lines.append(
                f"{int(label['class_id'])} {x_center:.6f} {y_center:.6f} {box_width:.6f} {box_height:.6f}"
            )
        return lines

    def _dataset_yaml(self, classes: list[dict[str, Any]]) -> str:
        final_path = json.dumps(self._managed_yolo_root.as_posix())
        lines = [
            f"path: {final_path}",
            "train: images/train",
            "val: images/val",
            "names:",
        ]
        lines.extend(f"  {item['id']}: {json.dumps(item['name'])}" for item in classes)
        return "\n".join(lines) + "\n"

    @staticmethod
    def _training_status_message(*, generated: bool, stale: bool, eligible_count: int) -> str:
        if eligible_count < 2:
            return "Save labels for at least two non-bad captures before building the managed training dataset."
        if not generated:
            return "Labels are ready. Build the managed YOLO dataset before starting training with yolo/data.yaml."
        if stale:
            return "Saved labels changed after the last build. Rebuild the managed YOLO dataset before training."
        return "Managed YOLO dataset is current and ready for the optional training runner."


dataset_labeling_service = DatasetLabelingService()
