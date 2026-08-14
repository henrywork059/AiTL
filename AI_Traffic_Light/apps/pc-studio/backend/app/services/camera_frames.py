from __future__ import annotations

from dataclasses import dataclass
import re
from threading import Lock
import time

import cv2
import numpy as np

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError

MAX_FRAME_BYTES = 8 * 1024 * 1024
SOURCE_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
SUPPORTED_UPLOAD_TYPES = {"image/jpeg", "image/png"}


@dataclass(frozen=True)
class CameraFrame:
    """One displayable camera frame held in memory by PC Studio."""

    content: bytes
    content_type: str
    source_id: str
    width: int
    height: int
    received_at_ms: int
    frame_number: int
    origin: str

    def metadata(self) -> dict:
        return {
            "source_id": self.source_id,
            "content_type": self.content_type,
            "width": self.width,
            "height": self.height,
            "received_at_ms": self.received_at_ms,
            "frame_number": self.frame_number,
            "size_bytes": len(self.content),
            "origin": self.origin,
        }


def _png_dimensions(content: bytes) -> tuple[int, int] | None:
    if len(content) < 24 or content[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    width = int.from_bytes(content[16:20], "big")
    height = int.from_bytes(content[20:24], "big")
    return (width, height) if width > 0 and height > 0 else None


def _jpeg_dimensions(content: bytes) -> tuple[int, int] | None:
    if len(content) < 4 or content[:2] != b"\xff\xd8":
        return None

    index = 2
    start_of_frame_markers = {
        0xC0,
        0xC1,
        0xC2,
        0xC3,
        0xC5,
        0xC6,
        0xC7,
        0xC9,
        0xCA,
        0xCB,
        0xCD,
        0xCE,
        0xCF,
    }

    while index < len(content):
        while index < len(content) and content[index] != 0xFF:
            index += 1
        while index < len(content) and content[index] == 0xFF:
            index += 1
        if index >= len(content):
            break

        marker = content[index]
        index += 1
        if marker in {0x01, 0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
            continue
        if index + 2 > len(content):
            break

        segment_length = int.from_bytes(content[index : index + 2], "big")
        if segment_length < 2 or index + segment_length > len(content):
            break
        if marker in start_of_frame_markers and segment_length >= 7:
            height = int.from_bytes(content[index + 3 : index + 5], "big")
            width = int.from_bytes(content[index + 5 : index + 7], "big")
            return (width, height) if width > 0 and height > 0 else None
        index += segment_length

    return None


def _image_dimensions(content: bytes, content_type: str) -> tuple[int, int] | None:
    if content_type == "image/png":
        return _png_dimensions(content)
    if content_type == "image/jpeg":
        return _jpeg_dimensions(content)
    return None


class CameraFrameService:
    """Store the latest uploaded frame and provide a hardware-free simulator."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._uploaded_frame: CameraFrame | None = None
        self._simulation_frame: CameraFrame | None = None
        self._simulation_enabled = False
        self._frame_counter = 0
        self._last_simulation_tick = -1

    def store_upload(self, *, source_id: str, content_type: str, content: bytes) -> CameraFrame:
        normalized_type = content_type.split(";", maxsplit=1)[0].strip().lower()
        if not SOURCE_ID_PATTERN.fullmatch(source_id):
            raise AppError(
                ErrorCode.CAMERA_SOURCE_INVALID,
                "source_id must contain 1-64 letters, numbers, dots, dashes, or underscores.",
                status_code=422,
                details={"source_id": source_id},
            )
        if normalized_type not in SUPPORTED_UPLOAD_TYPES:
            raise AppError(
                ErrorCode.CAMERA_FRAME_TYPE_UNSUPPORTED,
                "Camera uploads must be JPEG or PNG images.",
                status_code=415,
                details={"content_type": normalized_type or "missing"},
            )
        if not content:
            raise AppError(
                ErrorCode.CAMERA_FRAME_INVALID,
                "The camera upload did not contain image bytes.",
                status_code=422,
            )
        if len(content) > MAX_FRAME_BYTES:
            raise AppError(
                ErrorCode.CAMERA_FRAME_TOO_LARGE,
                "The camera frame is larger than the 8 MiB limit.",
                status_code=413,
                details={"size_bytes": len(content), "max_size_bytes": MAX_FRAME_BYTES},
            )

        dimensions = _image_dimensions(content, normalized_type)
        if dimensions is None:
            raise AppError(
                ErrorCode.CAMERA_FRAME_INVALID,
                "The uploaded bytes are not a valid supported image.",
                status_code=422,
                details={"content_type": normalized_type},
            )

        with self._lock:
            self._frame_counter += 1
            frame = CameraFrame(
                content=content,
                content_type=normalized_type,
                source_id=source_id,
                width=dimensions[0],
                height=dimensions[1],
                received_at_ms=int(time.time() * 1000),
                frame_number=self._frame_counter,
                origin="upload",
            )
            self._uploaded_frame = frame
            return frame

    def set_simulation(self, enabled: bool) -> dict:
        with self._lock:
            self._simulation_enabled = enabled
            if not enabled:
                self._simulation_frame = None
                self._last_simulation_tick = -1
        return self.status()

    def latest_frame(self) -> CameraFrame | None:
        with self._lock:
            if self._simulation_enabled:
                self._refresh_simulation_locked()
                return self._simulation_frame
            return self._uploaded_frame

    def status(self) -> dict:
        frame = self.latest_frame()
        now_ms = int(time.time() * 1000)
        age_ms = now_ms - frame.received_at_ms if frame else None
        simulation_enabled = self.simulation_enabled
        return {
            "mode": "simulation" if simulation_enabled else "receiver",
            "simulation_enabled": simulation_enabled,
            "frame_available": frame is not None,
            "streaming": frame is not None and (simulation_enabled or (age_ms is not None and age_ms <= 5000)),
            "active_source_id": frame.source_id if frame else None,
            "resolution": {"width": frame.width, "height": frame.height} if frame else None,
            "content_type": frame.content_type if frame else None,
            "received_at_ms": frame.received_at_ms if frame else None,
            "age_ms": age_ms,
            "frame_number": frame.frame_number if frame else 0,
            "size_bytes": len(frame.content) if frame else 0,
            "origin": frame.origin if frame else None,
            "stale": bool(frame and not simulation_enabled and age_ms is not None and age_ms > 5000),
            "frame_url": "/api/camera/frame" if frame else None,
            "upload_endpoint": "/api/camera/frame?source_id=<camera_id>",
        }

    @property
    def simulation_enabled(self) -> bool:
        with self._lock:
            return self._simulation_enabled

    def _refresh_simulation_locked(self) -> None:
        tick = int(time.time() * 2)
        if self._simulation_frame is not None and tick == self._last_simulation_tick:
            return

        self._last_simulation_tick = tick
        self._frame_counter += 1
        now_ms = int(time.time() * 1000)
        car_x = (tick * 31) % 1120
        bus_x = 1100 - ((tick * 19) % 1040)
        pedestrian_x = 500 + ((tick * 7) % 180)
        canvas = np.full((720, 1280, 3), (39, 32, 17), dtype=np.uint8)
        cv2.rectangle(canvas, (0, 205), (1279, 719), (47, 41, 36), thickness=-1)
        for y in (360, 560):
            for x in range(0, 1280, 64):
                cv2.line(canvas, (x, y), (min(x + 36, 1279), y), (34, 153, 210), thickness=6)
        for index in range(9):
            x = 430 + index * 42
            cv2.rectangle(canvas, (x, 205), (x + 22, 719), (243, 237, 230), thickness=-1)

        cv2.rectangle(canvas, (car_x, 405), (car_x + 160, 475), (62, 136, 240), thickness=-1)
        cv2.circle(canvas, (car_x + 38, 478), 18, (10, 7, 5), thickness=-1)
        cv2.circle(canvas, (car_x + 125, 478), 18, (10, 7, 5), thickness=-1)
        cv2.rectangle(canvas, (bus_x, 590), (bus_x + 235, 672), (255, 166, 88), thickness=-1)
        cv2.circle(canvas, (bus_x + 48, 675), 17, (10, 7, 5), thickness=-1)
        cv2.circle(canvas, (bus_x + 190, 675), 17, (10, 7, 5), thickness=-1)

        cv2.circle(canvas, (pedestrian_x, 260), 22, (247, 113, 163), thickness=-1)
        cv2.line(canvas, (pedestrian_x, 282), (pedestrian_x, 364), (247, 113, 163), thickness=15)
        cv2.line(canvas, (pedestrian_x, 319), (pedestrian_x - 35, 361), (247, 113, 163), thickness=15)
        cv2.line(canvas, (pedestrian_x, 319), (pedestrian_x + 34, 361), (247, 113, 163), thickness=15)
        cv2.line(canvas, (pedestrian_x, 364), (pedestrian_x - 28, 419), (247, 113, 163), thickness=15)
        cv2.line(canvas, (pedestrian_x, 364), (pedestrian_x + 30, 419), (247, 113, 163), thickness=15)

        cv2.rectangle(canvas, (28, 24), (520, 116), (10, 7, 5), thickness=-1)
        cv2.putText(canvas, "PC CAMERA SIMULATION", (52, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (135, 231, 126), 2)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(
            canvas,
            f"{timestamp} - frame {self._frame_counter}",
            (52, 99),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.58,
            (217, 209, 201),
            1,
        )

        encoded_ok, encoded = cv2.imencode(".png", canvas)
        if not encoded_ok:
            raise AppError(
                ErrorCode.CAMERA_FRAME_READ_FAILED,
                "Failed to encode the synthetic camera frame.",
                status_code=500,
            )
        self._simulation_frame = CameraFrame(
            content=encoded.tobytes(),
            content_type="image/png",
            source_id="simulation_camera",
            width=1280,
            height=720,
            received_at_ms=now_ms,
            frame_number=self._frame_counter,
            origin="simulation",
        )


camera_frame_service = CameraFrameService()
