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
    """Persist camera frames and paired metadata inside the project dataset folder."""

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
