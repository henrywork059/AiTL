from __future__ import annotations

from dataclasses import dataclass
import random
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
SIMULATION_DENSITIES = {"light", "normal", "busy"}


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


def _draw_pedestrian(canvas: np.ndarray, x: int, y: int, color: tuple[int, int, int], stride: int) -> None:
    """Draw a simple top-to-bottom walking pedestrian centred on ``x, y``."""
    cv2.circle(canvas, (x, y - 28), 14, color, thickness=-1)
    cv2.line(canvas, (x, y - 12), (x, y + 24), color, thickness=10)
    cv2.line(canvas, (x, y), (x - 18, y + 18), color, thickness=8)
    cv2.line(canvas, (x, y), (x + 18, y + 18), color, thickness=8)
    cv2.line(canvas, (x, y + 22), (x - 12 - stride, y + 48), color, thickness=8)
    cv2.line(canvas, (x, y + 22), (x + 12 + stride, y + 48), color, thickness=8)


def _draw_vehicle(
    canvas: np.ndarray,
    *,
    x: int,
    y: int,
    width: int,
    color: tuple[int, int, int],
    vehicle_type: str,
) -> None:
    """Draw a compact side-view vehicle for the synthetic horizontal lanes."""
    height = 58 if vehicle_type == "car" else 72
    body_top = y - height // 2
    body_bottom = y + height // 2
    cv2.rectangle(canvas, (x, body_top), (x + width, body_bottom), color, thickness=-1)

    if vehicle_type == "car":
        roof_left = x + width // 4
        roof_right = x + (width * 3) // 4
        cv2.rectangle(canvas, (roof_left, body_top - 22), (roof_right, body_top + 4), color, thickness=-1)
        cv2.rectangle(canvas, (roof_left + 7, body_top - 17), (roof_right - 7, body_top - 2), (77, 93, 110), thickness=-1)
    else:
        for window_x in range(x + 18, x + width - 20, 44):
            cv2.rectangle(canvas, (window_x, body_top + 10), (min(window_x + 28, x + width - 12), body_top + 31), (77, 93, 110), thickness=-1)

    wheel_y = body_bottom + 4
    cv2.circle(canvas, (x + 34, wheel_y), 14, (18, 20, 23), thickness=-1)
    cv2.circle(canvas, (x + width - 34, wheel_y), 14, (18, 20, 23), thickness=-1)
    cv2.circle(canvas, (x + 34, wheel_y), 6, (125, 133, 144), thickness=-1)
    cv2.circle(canvas, (x + width - 34, wheel_y), 6, (125, 133, 144), thickness=-1)


class CameraFrameService:
    """Store the latest uploaded frame and provide a hardware-free simulator."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._uploaded_frame: CameraFrame | None = None
        self._simulation_frame: CameraFrame | None = None
        self._simulation_enabled = False
        self._simulation_paused = False
        self._simulation_density = "normal"
        self._simulation_seed = int(time.time() * 1000) & 0x7FFFFFFF
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
            self._simulation_paused = False
            self._simulation_frame = None
            self._last_simulation_tick = -1
        return self.status()

    def configure_simulation(self, *, density: str | None = None, paused: bool | None = None) -> dict:
        """Update synthetic-scene density or pause state without changing camera mode."""
        with self._lock:
            if density is not None:
                normalized_density = density.strip().lower()
                if normalized_density not in SIMULATION_DENSITIES:
                    raise AppError(
                        ErrorCode.INVALID_REQUEST,
                        "Simulation density must be light, normal, or busy.",
                        status_code=422,
                        details={"density": density, "allowed": sorted(SIMULATION_DENSITIES)},
                    )
                if normalized_density != self._simulation_density:
                    self._simulation_density = normalized_density
                    self._simulation_frame = None
                    self._last_simulation_tick = -1

            if paused is not None:
                if not self._simulation_enabled:
                    raise AppError(
                        ErrorCode.CAMERA_STREAM_NOT_STARTED,
                        "Start simulation mode before pausing or resuming the synthetic scene.",
                        status_code=409,
                    )
                if paused != self._simulation_paused:
                    self._simulation_paused = paused
                    if not paused:
                        self._simulation_frame = None
                        self._last_simulation_tick = -1

        return self.status()

    def latest_frame(self) -> CameraFrame | None:
        with self._lock:
            if self._simulation_enabled:
                if self._simulation_frame is None or not self._simulation_paused:
                    self._refresh_simulation_locked()
                return self._simulation_frame
            return self._uploaded_frame

    def status(self) -> dict:
        frame = self.latest_frame()
        now_ms = int(time.time() * 1000)
        age_ms = now_ms - frame.received_at_ms if frame else None
        with self._lock:
            simulation_enabled = self._simulation_enabled
            simulation_paused = self._simulation_paused
            simulation_density = self._simulation_density
        return {
            "mode": "simulation" if simulation_enabled else "receiver",
            "simulation_enabled": simulation_enabled,
            "simulation_paused": simulation_paused,
            "simulation_density": simulation_density,
            "frame_available": frame is not None,
            "streaming": frame is not None and (
                (simulation_enabled and not simulation_paused)
                or (not simulation_enabled and age_ms is not None and age_ms <= 5000)
            ),
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
        density = self._simulation_density
        paused = self._simulation_paused

        canvas = np.full((720, 1280, 3), (29, 33, 37), dtype=np.uint8)

        # Sidewalks and horizontal road keep vehicle motion visually left/right.
        cv2.rectangle(canvas, (0, 0), (1279, 178), (72, 79, 84), thickness=-1)
        cv2.rectangle(canvas, (0, 179), (1279, 624), (48, 52, 57), thickness=-1)
        cv2.rectangle(canvas, (0, 625), (1279, 719), (72, 79, 84), thickness=-1)
        cv2.line(canvas, (0, 179), (1279, 179), (128, 136, 144), thickness=5)
        cv2.line(canvas, (0, 625), (1279, 625), (128, 136, 144), thickness=5)

        for lane_y in (310, 500):
            for x in range(0, 1280, 86):
                cv2.line(canvas, (x, lane_y), (min(x + 50, 1279), lane_y), (46, 176, 224), thickness=5)

        # A vertical pedestrian crossing: people travel from the top sidewalk to the bottom.
        crossing_left, crossing_right = 520, 760
        cv2.rectangle(canvas, (crossing_left, 179), (crossing_right, 625), (55, 59, 63), thickness=-1)
        for stripe_y in range(205, 610, 46):
            cv2.rectangle(
                canvas,
                (crossing_left + 18, stripe_y),
                (crossing_right - 18, stripe_y + 22),
                (225, 228, 230),
                thickness=-1,
            )
        cv2.line(canvas, (485, 179), (485, 625), (218, 218, 218), thickness=5)
        cv2.line(canvas, (795, 179), (795, 625), (218, 218, 218), thickness=5)

        profile = {
            "light": {"pedestrians": (2, 3), "vehicles": 2},
            "normal": {"pedestrians": (4, 6), "vehicles": 4},
            "busy": {"pedestrians": (7, 10), "vehicles": 6},
        }[density]
        scene_bucket = tick // 8
        rng = random.Random(self._simulation_seed + scene_bucket * 1009 + len(density) * 97)

        vehicle_palette = [
            (66, 135, 245),
            (94, 176, 110),
            (230, 144, 81),
            (181, 105, 200),
            (94, 188, 214),
            (122, 128, 137),
        ]
        for index in range(profile["vehicles"]):
            vehicle_type = "bus" if index % 5 == 4 else "car"
            width = 220 if vehicle_type == "bus" else rng.randint(125, 170)
            lane_y = 265 if index % 2 == 0 else 455
            direction = 1 if index % 2 == 0 else -1
            speed = rng.randint(13, 25)
            offset = rng.randint(0, 1500)
            span = 1280 + width + 220
            progress = (offset + tick * speed) % span
            x = -width + progress if direction > 0 else 1280 - progress
            _draw_vehicle(
                canvas,
                x=int(x),
                y=lane_y,
                width=width,
                color=vehicle_palette[index % len(vehicle_palette)],
                vehicle_type=vehicle_type,
            )

        pedestrian_count = rng.randint(*profile["pedestrians"])
        pedestrian_palette = [
            (196, 111, 255),
            (119, 187, 255),
            (119, 220, 157),
            (255, 158, 132),
            (164, 142, 245),
            (114, 212, 229),
        ]
        travel_top, travel_bottom = 120, 690
        travel_span = travel_bottom - travel_top
        for index in range(pedestrian_count):
            x = rng.randint(crossing_left + 45, crossing_right - 45)
            speed = rng.randint(6, 13)
            base = rng.randint(0, travel_span - 1)
            y = travel_top + ((base + tick * speed) % travel_span)
            stride = 5 if (tick + index) % 2 == 0 else -5
            _draw_pedestrian(
                canvas,
                x=x,
                y=int(y),
                color=pedestrian_palette[index % len(pedestrian_palette)],
                stride=stride,
            )

        cv2.rectangle(canvas, (24, 20), (490, 122), (14, 17, 20), thickness=-1)
        cv2.putText(canvas, "PC CAMERA SIMULATION", (46, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.74, (126, 231, 135), 2)
        cv2.putText(
            canvas,
            f"density: {density}   pedestrians: {pedestrian_count}   vehicles: {profile['vehicles']}",
            (46, 82),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.52,
            (217, 221, 224),
            1,
        )
        state_label = "PAUSED - inspection frame" if paused else f"frame {self._frame_counter}"
        cv2.putText(
            canvas,
            state_label,
            (46, 107),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.52,
            (217, 221, 224),
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
