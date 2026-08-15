from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from threading import Lock
from typing import Literal
from uuid import uuid4

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.core.logging_config import get_logger
from app.services.camera_frames import CameraFrame

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_DATASET_ROOT = PROJECT_ROOT / "datasets"
SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
CAPTURE_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,160}$")
IMAGE_SUFFIXES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/svg+xml": ".svg",
}
QualityTag = Literal["unreviewed", "useful", "bad"]


@dataclass(frozen=True)
class CaptureRecord:
    capture_id: str
    session_id: str
    source_id: str
    origin: str
    content_type: str
    width: int
    height: int
    source_frame_number: int
    source_received_at_ms: int
    captured_at_ms: int
    size_bytes: int
    quality_tag: QualityTag
    note: str
    image_path: str
    metadata_path: str

    def to_dict(self) -> dict:
        return asdict(self)


class DatasetCaptureService:
    """Persist and remove camera captures inside the project dataset folder."""

    def __init__(self, dataset_root: Path | None = None) -> None:
        configured_root = os.environ.get("AITL_DATASET_DIR")
        self._dataset_root = Path(configured_root) if configured_root else (dataset_root or DEFAULT_DATASET_ROOT)
        self._dataset_root = self._dataset_root.expanduser().resolve()
        self._capture_root = self._dataset_root / "captures"
        self._lock = Lock()
        self._last_capture: CaptureRecord | None = None

    @property
    def dataset_root(self) -> Path:
        return self._dataset_root

    def capture_frame(
        self,
        frame: CameraFrame,
        *,
        session_id: str,
        quality_tag: QualityTag = "unreviewed",
        note: str = "",
    ) -> CaptureRecord:
        """Save one exact source frame plus JSON metadata using atomic file replacement."""
        if not SESSION_ID_PATTERN.fullmatch(session_id):
            raise AppError(
                ErrorCode.INVALID_REQUEST,
                "session_id must contain 1-64 letters, numbers, dots, dashes, or underscores.",
                status_code=422,
                details={"session_id": session_id},
            )
        if quality_tag not in {"unreviewed", "useful", "bad"}:
            raise AppError(
                ErrorCode.INVALID_REQUEST,
                "quality_tag must be unreviewed, useful, or bad.",
                status_code=422,
                details={"quality_tag": quality_tag},
            )
        if len(note) > 500:
            raise AppError(
                ErrorCode.INVALID_REQUEST,
                "Capture notes cannot exceed 500 characters.",
                status_code=422,
            )

        suffix = IMAGE_SUFFIXES.get(frame.content_type)
        if suffix is None:
            raise AppError(
                ErrorCode.DATASET_WRITE_FAILED,
                "The current frame format cannot be saved as a dataset image.",
                status_code=422,
                details={"content_type": frame.content_type},
            )

        captured_at = datetime.now(timezone.utc)
        captured_at_ms = int(captured_at.timestamp() * 1000)
        capture_id = f"{captured_at.strftime('%Y%m%dT%H%M%S%fZ')}_{frame.frame_number:06d}_{uuid4().hex[:8]}"
        session_root = self._capture_root / session_id
        image_path = session_root / "images" / f"{capture_id}{suffix}"
        metadata_path = session_root / "metadata" / f"{capture_id}.json"
        image_relative = image_path.relative_to(self._dataset_root).as_posix()
        metadata_relative = metadata_path.relative_to(self._dataset_root).as_posix()
        record = CaptureRecord(
            capture_id=capture_id,
            session_id=session_id,
            source_id=frame.source_id,
            origin=frame.origin,
            content_type=frame.content_type,
            width=frame.width,
            height=frame.height,
            source_frame_number=frame.frame_number,
            source_received_at_ms=frame.received_at_ms,
            captured_at_ms=captured_at_ms,
            size_bytes=len(frame.content),
            quality_tag=quality_tag,
            note=note.strip(),
            image_path=image_relative,
            metadata_path=metadata_relative,
        )

        with self._lock:
            try:
                self._atomic_write(image_path, frame.content)
                metadata_bytes = (json.dumps(record.to_dict(), indent=2, sort_keys=True) + "\n").encode("utf-8")
                self._atomic_write(metadata_path, metadata_bytes)
            except OSError as exc:
                image_path.unlink(missing_ok=True)
                metadata_path.unlink(missing_ok=True)
                logger.exception(
                    "Dataset capture write failed",
                    extra={"error_code": ErrorCode.DATASET_WRITE_FAILED.value, "session_id": session_id},
                )
                raise AppError(
                    ErrorCode.DATASET_WRITE_FAILED,
                    "Failed to save the camera frame and metadata.",
                    status_code=500,
                    details={"session_id": session_id},
                ) from exc
            self._last_capture = record

        logger.info(
            "Dataset frame captured",
            extra={
                "capture_id": capture_id,
                "session_id": session_id,
                "source_id": frame.source_id,
                "origin": frame.origin,
            },
        )
        return record

    def delete_capture(self, capture_id: str) -> dict:
        """Delete one capture image, metadata, and optional manual-label document."""
        if not CAPTURE_ID_PATTERN.fullmatch(capture_id):
            raise AppError(
                ErrorCode.INVALID_REQUEST,
                "capture_id contains unsupported characters.",
                status_code=422,
                details={"capture_id": capture_id},
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

        metadata_path = matches[0]
        try:
            record = json.loads(metadata_path.read_text(encoding="utf-8"))
            if not isinstance(record, dict) or str(record.get("capture_id")) != capture_id:
                raise ValueError("capture metadata mismatch")
            session_id = str(record.get("session_id", ""))
            if not SESSION_ID_PATTERN.fullmatch(session_id):
                raise ValueError("invalid session id")
            image_path = self._safe_dataset_path(str(record.get("image_path", "")))
            declared_metadata = self._safe_dataset_path(str(record.get("metadata_path", "")))
            if declared_metadata != metadata_path.resolve():
                raise ValueError("metadata path mismatch")
            label_path = self._capture_root / session_id / "labels" / f"{capture_id}.json"
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise AppError(
                ErrorCode.DATASET_READ_FAILED,
                "Failed to read capture metadata before deletion.",
                status_code=500,
                details={"capture_id": capture_id},
            ) from exc

        originals = [path for path in (image_path, label_path, metadata_path) if path.is_file()]
        staged: list[tuple[Path, Path]] = []
        with self._lock:
            try:
                for original in originals:
                    temporary = original.with_name(f".{original.name}.{uuid4().hex}.delete")
                    os.replace(original, temporary)
                    staged.append((original, temporary))
            except OSError as exc:
                for original, temporary in reversed(staged):
                    try:
                        if temporary.exists() and not original.exists():
                            os.replace(temporary, original)
                    except OSError:
                        logger.exception("Failed to roll back capture deletion", extra={"capture_id": capture_id})
                raise AppError(
                    ErrorCode.DATASET_DELETE_FAILED,
                    "Failed to delete the captured frame safely.",
                    status_code=500,
                    details={"capture_id": capture_id},
                ) from exc

            cleanup_failed = False
            for _, temporary in staged:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    cleanup_failed = True
                    logger.warning("Capture delete staging file could not be removed", extra={"path": str(temporary)})
            if self._last_capture and self._last_capture.capture_id == capture_id:
                self._last_capture = None

        session_root = self._capture_root / session_id
        for directory in (session_root / "labels", session_root / "metadata", session_root / "images", session_root):
            try:
                directory.rmdir()
            except OSError:
                pass

        deleted_paths = [original.relative_to(self._dataset_root).as_posix() for original, _ in staged]
        logger.info(
            "Dataset capture deleted",
            extra={"capture_id": capture_id, "session_id": session_id, "deleted_file_count": len(deleted_paths)},
        )
        return {
            "capture_id": capture_id,
            "session_id": session_id,
            "deleted": True,
            "deleted_paths": deleted_paths,
            "cleanup_pending": cleanup_failed,
        }

    def status(self) -> dict:
        image_count = 0
        metadata_count = 0
        session_count = 0
        if self._capture_root.exists():
            session_count = sum(1 for path in self._capture_root.iterdir() if path.is_dir())
            image_count = sum(
                1
                for path in self._capture_root.glob("*/images/*")
                if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".svg"}
            )
            metadata_count = sum(1 for path in self._capture_root.glob("*/metadata/*.json") if path.is_file())
        return {
            "active_dataset_id": "captures",
            "session_count": session_count,
            "frame_count": image_count,
            "metadata_count": metadata_count,
            "capture_enabled": True,
            "status": "ready",
            "dataset_path": "datasets/captures",
            "last_capture": self._last_capture.to_dict() if self._last_capture else None,
        }

    def _safe_dataset_path(self, relative_path: str) -> Path:
        requested = Path(relative_path)
        if requested.is_absolute():
            raise ValueError("absolute dataset path")
        resolved = (self._dataset_root / requested).resolve()
        if not resolved.is_relative_to(self._dataset_root):
            raise ValueError("dataset path outside root")
        return resolved

    @staticmethod
    def _atomic_write(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        try:
            with temporary_path.open("xb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, path)
        finally:
            temporary_path.unlink(missing_ok=True)


dataset_capture_service = DatasetCaptureService()
