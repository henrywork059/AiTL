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
from app.services.signal_rules import signal_rules_service

MAX_FRAME_BYTES = 8 * 1024 * 1024
SOURCE_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
SUPPORTED_UPLOAD_TYPES = {"image/jpeg", "image/png"}
SIMULATION_DENSITIES = {"light", "normal", "busy"}

FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
ROAD_TOP = 179
ROAD_BOTTOM = 625
CROSSING_LEFT = 520
CROSSING_RIGHT = 760
EASTBOUND_STOP_LINE = 495
WESTBOUND_STOP_LINE = 785
TOP_PEDESTRIAN_WAIT_Y = 126
BOTTOM_PEDESTRIAN_WAIT_Y = 674


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


@dataclass
class _SimVehicle:
    x: float
    y: int
    width: int
    speed: float
    direction: int
    color: tuple[int, int, int]
    vehicle_type: str


@dataclass
class _SimPedestrian:
    x: int
    y: float
    speed: float
    direction: int
    color: tuple[int, int, int]


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
        0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
        0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
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
        segment_length = int.from_bytes(content[index:index + 2], "big")
        if segment_length < 2 or index + segment_length > len(content):
            break
        if marker in start_of_frame_markers and segment_length >= 7:
            height = int.from_bytes(content[index + 3:index + 5], "big")
            width = int.from_bytes(content[index + 5:index + 7], "big")
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
            cv2.rectangle(
                canvas,
                (window_x, body_top + 10),
                (min(window_x + 28, x + width - 12), body_top + 31),
                (77, 93, 110),
                thickness=-1,
            )
    wheel_y = body_bottom + 4
    cv2.circle(canvas, (x + 34, wheel_y), 14, (18, 20, 23), thickness=-1)
    cv2.circle(canvas, (x + width - 34, wheel_y), 14, (18, 20, 23), thickness=-1)
    cv2.circle(canvas, (x + 34, wheel_y), 6, (125, 133, 144), thickness=-1)
    cv2.circle(canvas, (x + width - 34, wheel_y), 6, (125, 133, 144), thickness=-1)


SIMULATION_CAMERA_PAIRS = (
    ("simulation_camera", "simulation_camera_b"),
    ("simulation_camera_c", "simulation_camera_d"),
)
SIMULATION_CAMERA_SOURCE_IDS = tuple(source for pair in SIMULATION_CAMERA_PAIRS for source in pair)


class CameraFrameService:
    """Store the latest uploaded frame and provide a signal-aware hardware-free simulator."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._uploaded_frame: CameraFrame | None = None
        self._simulation_frame: CameraFrame | None = None
        self._simulation_view_frames: dict[str, CameraFrame] = {}
        self._simulation_source_id = "simulation_camera"
        self._simulation_enabled = False
        self._simulation_paused = False
        self._simulation_density = "normal"
        self._simulation_seed = int(time.time() * 1000) & 0x7FFFFFFF
        self._frame_counter = 0
        self._last_simulation_tick = -1
        self._simulation_clock_s = 0.0
        self._simulation_last_update_monotonic: float | None = None
        self._vehicles: list[_SimVehicle] = []
        self._pedestrians: list[_SimPedestrian] = []
        self._simulation_rng = random.Random(self._simulation_seed)

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
            raise AppError(ErrorCode.CAMERA_FRAME_INVALID, "The camera upload did not contain image bytes.", status_code=422)
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

    def _reset_simulation_locked(self) -> None:
        self._simulation_frame = None
        self._simulation_view_frames.clear()
        self._last_simulation_tick = -1
        self._simulation_clock_s = 0.0
        self._simulation_last_update_monotonic = time.monotonic()
        signal_rules_service.reset_runtime(0.0)
        density_offset = {"light": 101, "normal": 211, "busy": 307}[self._simulation_density]
        self._simulation_rng = random.Random(self._simulation_seed + density_offset)
        self._initialize_agents_locked()

    def set_simulation(self, enabled: bool) -> dict:
        with self._lock:
            self._simulation_enabled = enabled
            self._simulation_paused = False
            if enabled:
                self._reset_simulation_locked()
            else:
                self._simulation_frame = None
                self._simulation_view_frames.clear()
                self._last_simulation_tick = -1
                self._simulation_last_update_monotonic = None
                self._vehicles = []
                self._pedestrians = []
                signal_rules_service.reset_runtime(0.0)
        return self.status()

    def configure_simulation(self, *, density: str | None = None, paused: bool | None = None) -> dict:
        with self._lock:
            reset_agents = False
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
                    reset_agents = True
            if paused is not None:
                if not self._simulation_enabled:
                    raise AppError(
                        ErrorCode.CAMERA_STREAM_NOT_STARTED,
                        "Start simulation mode before pausing or resuming the synthetic scene.",
                        status_code=409,
                    )
                if paused != self._simulation_paused:
                    self._simulation_paused = paused
                    self._simulation_last_update_monotonic = time.monotonic()
                    if not paused:
                        self._simulation_frame = None
                        self._last_simulation_tick = -1
            if reset_agents and self._simulation_enabled:
                self._reset_simulation_locked()
        return self.status()

    def set_simulation_source(self, source_id: str) -> None:
        if source_id not in SIMULATION_CAMERA_SOURCE_IDS:
            raise ValueError("Unknown simulation camera")
        with self._lock:
            self._simulation_source_id = source_id

    def _simulation_frame_for_locked(self, source_id: str) -> CameraFrame | None:
        if not self._simulation_enabled:
            return None
        if self._simulation_frame is None or not self._simulation_paused:
            self._refresh_simulation_locked()
        original = self._simulation_frame
        if source_id not in SIMULATION_CAMERA_SOURCE_IDS:
            raise ValueError("Unknown simulation camera")
        if original is None or source_id == SIMULATION_CAMERA_PAIRS[0][0]:
            return original
        cached = self._simulation_view_frames.get(source_id)
        if cached is None or cached.frame_number != original.frame_number:
            image = cv2.imdecode(np.frombuffer(original.content, dtype=np.uint8), cv2.IMREAD_COLOR)
            if image is None:
                raise AppError(ErrorCode.CAMERA_FRAME_READ_FAILED, "Simulation frame decode failed.", status_code=500)
            # Each pair shows vertically mirrored sides; pair 2 uses a horizontal viewpoint.
            flip = {"simulation_camera_b": 0, "simulation_camera_c": 1, "simulation_camera_d": -1}[source_id]
            success, encoded = cv2.imencode(".png", cv2.flip(image, flip))
            if not success:
                raise AppError(ErrorCode.CAMERA_FRAME_READ_FAILED, "Mirrored simulation frame encoding failed.", status_code=500)
            cached = CameraFrame(
                content=encoded.tobytes(), content_type="image/png",
                source_id=source_id, width=original.width, height=original.height,
                received_at_ms=original.received_at_ms, frame_number=original.frame_number,
                origin="simulation",
            )
            self._simulation_view_frames[source_id] = cached
        return cached

    def simulation_frame_for(self, source_id: str) -> CameraFrame | None:
        with self._lock:
            return self._simulation_frame_for_locked(source_id)

    def simulation_scene_for(self, source_id: str) -> dict | None:
        """Read the running simulator's actual agents for the optional 3D UI.

        This view is read-only with respect to controller policy. Every saved
        simulated camera observes the same physical scene with a different
        frontend viewing angle. Original 2D frames remain canonical for AI,
        capture and image-coordinate region editing.
        """
        if source_id not in SIMULATION_CAMERA_SOURCE_IDS:
            raise ValueError("Unknown simulation camera")
        with self._lock:
            frame = self._simulation_frame_for_locked(source_id)
            if frame is None:
                return None
            signal = self._simulation_signal_state_locked()
            return {
                "source_id": source_id,
                "frame_number": frame.frame_number,
                "received_at_ms": frame.received_at_ms,
                "width": FRAME_WIDTH,
                "height": FRAME_HEIGHT,
                "simulation_time_seconds": round(self._simulation_clock_s, 3),
                "paused": self._simulation_paused,
                "density": self._simulation_density,
                "signal": {
                    "phase": signal["phase"],
                    "vehicle_go": signal["vehicle_go"],
                    "pedestrian_walk": signal["pedestrian_walk"],
                    "seconds_remaining": signal["seconds_remaining"],
                },
                "vehicles": [
                    {
                        "id": f"vehicle_{index}",
                        "x": round(vehicle.x, 2),
                        "y": vehicle.y,
                        "width": vehicle.width,
                        "direction": vehicle.direction,
                        "vehicle_type": vehicle.vehicle_type,
                        "color": "#{:02x}{:02x}{:02x}".format(*reversed(vehicle.color)),
                    }
                    for index, vehicle in enumerate(self._vehicles)
                ],
                "pedestrians": [
                    {
                        "id": f"pedestrian_{index}",
                        "x": pedestrian.x,
                        "y": round(pedestrian.y, 2),
                        "direction": pedestrian.direction,
                        "color": "#{:02x}{:02x}{:02x}".format(*reversed(pedestrian.color)),
                    }
                    for index, pedestrian in enumerate(self._pedestrians)
                ],
            }

    def latest_frame(self) -> CameraFrame | None:
        with self._lock:
            if self._simulation_enabled:
                return self._simulation_frame_for_locked(self._simulation_source_id)
            return self._uploaded_frame

    def simulation_signal_state(self) -> dict:
        with self._lock:
            return dict(self._simulation_signal_state_locked())

    def reset_simulation_signal_policy(self) -> dict:
        """Reset transient adaptive policy state at the current simulation clock."""
        with self._lock:
            return signal_rules_service.reset_runtime(self._simulation_clock_s)

    def status(self) -> dict:
        frame = self.latest_frame()
        now_ms = int(time.time() * 1000)
        age_ms = now_ms - frame.received_at_ms if frame else None
        with self._lock:
            simulation_enabled = self._simulation_enabled
            simulation_paused = self._simulation_paused
            simulation_density = self._simulation_density
            signal = self._simulation_signal_state_locked() if simulation_enabled else None
        return {
            "mode": "simulation" if simulation_enabled else "receiver",
            "simulation_enabled": simulation_enabled,
            "simulation_paused": simulation_paused,
            "simulation_density": simulation_density,
            "simulation_signal_phase": signal["phase"] if signal else None,
            "simulation_signal_seconds_remaining": signal["seconds_remaining"] if signal else None,
            "simulation_signal_cycle_seconds": signal["base_cycle_seconds"] if signal else None,
            "simulation_signal_vehicle_go": signal["vehicle_go"] if signal else False,
            "simulation_signal_pedestrian_walk": signal["pedestrian_walk"] if signal else False,
            "simulation_signal_mode": signal["mode"] if signal else None,
            "simulation_signal_profile": signal["active_profile"] if signal else None,
            "simulation_signal_active_rules": signal["active_rules"] if signal else [],
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

    @property
    def simulation_paused(self) -> bool:
        with self._lock:
            return self._simulation_paused

    def _simulation_signal_state_locked(self) -> dict:
        return signal_rules_service.signal_state(self._simulation_clock_s)

    def _initialize_agents_locked(self) -> None:
        vehicle_count = {"light": 4, "normal": 8, "busy": 12}[self._simulation_density]
        pedestrian_count = {"light": 4, "normal": 7, "busy": 11}[self._simulation_density]
        vehicle_palette = [
            (66, 135, 245), (94, 176, 110), (230, 144, 81),
            (181, 105, 200), (94, 188, 214), (122, 128, 137),
        ]
        pedestrian_palette = [
            (196, 111, 255), (119, 187, 255), (119, 220, 157),
            (255, 158, 132), (164, 142, 245), (114, 212, 229),
        ]
        self._vehicles = []
        for index in range(vehicle_count):
            direction = 1 if index % 2 == 0 else -1
            lane_index = index // 2
            vehicle_type = "car"
            width = self._simulation_rng.randint(125, 170)
            spacing = 300
            if direction > 0:
                x = -240.0 + lane_index * spacing
                y = 265
            else:
                x = float(FRAME_WIDTH + 60 - width - lane_index * spacing)
                y = 455
            speed = float(self._simulation_rng.randint(92, 125))
            self._vehicles.append(
                _SimVehicle(
                    x=x,
                    y=y,
                    width=width,
                    speed=speed,
                    direction=direction,
                    color=vehicle_palette[index % len(vehicle_palette)],
                    vehicle_type=vehicle_type,
                )
            )
        self._pedestrians = []
        for index in range(pedestrian_count):
            direction = 1 if index % 2 == 0 else -1
            x = CROSSING_LEFT + 42 + (index * 47) % (CROSSING_RIGHT - CROSSING_LEFT - 84)
            if direction > 0:
                y = float(max(65, TOP_PEDESTRIAN_WAIT_Y - (index // 2) * 22))
            else:
                y = float(min(710, BOTTOM_PEDESTRIAN_WAIT_Y + (index // 2) * 18))
            self._pedestrians.append(
                _SimPedestrian(
                    x=x,
                    y=y,
                    speed=float(self._simulation_rng.randint(88, 106)),
                    direction=direction,
                    color=pedestrian_palette[index % len(pedestrian_palette)],
                )
            )

    def _advance_simulation_locked(self, dt: float) -> None:
        if dt <= 0 or self._simulation_paused:
            return
        remaining = min(dt, 2.0)
        while remaining > 1e-9:
            step = min(0.05, remaining)
            self._simulation_clock_s += step
            self._advance_vehicles_locked(step)
            self._advance_pedestrians_locked(step)
            remaining -= step

    def _advance_vehicles_locked(self, dt: float) -> None:
        phase = self._simulation_signal_state_locked()["phase"]
        vehicle_go = phase == "vehicle_green"
        gap = 22.0
        eastbound = sorted((v for v in self._vehicles if v.direction > 0), key=lambda item: item.x, reverse=True)
        ahead: _SimVehicle | None = None
        for vehicle in eastbound:
            proposed = vehicle.x + vehicle.speed * dt
            front = vehicle.x + vehicle.width
            already_committed = front > EASTBOUND_STOP_LINE
            if not vehicle_go and not already_committed:
                proposed = min(proposed, EASTBOUND_STOP_LINE - 8 - vehicle.width)
            if ahead is not None:
                proposed = min(proposed, ahead.x - gap - vehicle.width)
            vehicle.x = proposed
            ahead = vehicle
        westbound = sorted((v for v in self._vehicles if v.direction < 0), key=lambda item: item.x)
        ahead = None
        for vehicle in westbound:
            proposed = vehicle.x - vehicle.speed * dt
            front = vehicle.x
            already_committed = front < WESTBOUND_STOP_LINE
            if not vehicle_go and not already_committed:
                proposed = max(proposed, WESTBOUND_STOP_LINE + 8)
            if ahead is not None:
                proposed = max(proposed, ahead.x + ahead.width + gap)
            vehicle.x = proposed
            ahead = vehicle
        for vehicle in self._vehicles:
            if vehicle.direction > 0 and vehicle.x > FRAME_WIDTH + 120:
                peers = [item.x for item in self._vehicles if item.direction > 0 and item is not vehicle]
                vehicle.x = min(
                    -vehicle.width - self._simulation_rng.randint(80, 180),
                    min(peers, default=-120.0) - vehicle.width - self._simulation_rng.randint(70, 140),
                )
            elif vehicle.direction < 0 and vehicle.x + vehicle.width < -120:
                peers = [item.x + item.width for item in self._vehicles if item.direction < 0 and item is not vehicle]
                vehicle.x = max(
                    float(FRAME_WIDTH + self._simulation_rng.randint(80, 180)),
                    max(peers, default=float(FRAME_WIDTH + 120)) + self._simulation_rng.randint(70, 140),
                )

    def _advance_pedestrians_locked(self, dt: float) -> None:
        phase = self._simulation_signal_state_locked()["phase"]
        can_start_crossing = phase == "pedestrian_green"
        for pedestrian in self._pedestrians:
            delta = pedestrian.speed * dt * pedestrian.direction
            if pedestrian.direction > 0:
                if pedestrian.y < TOP_PEDESTRIAN_WAIT_Y:
                    pedestrian.y = min(TOP_PEDESTRIAN_WAIT_Y, pedestrian.y + pedestrian.speed * dt)
                elif pedestrian.y <= TOP_PEDESTRIAN_WAIT_Y + 0.5 and not can_start_crossing:
                    pedestrian.y = float(TOP_PEDESTRIAN_WAIT_Y)
                else:
                    pedestrian.y += pedestrian.speed * dt
                if pedestrian.y > FRAME_HEIGHT + 25:
                    pedestrian.y = float(70 - self._simulation_rng.randint(0, 42))
            else:
                if pedestrian.y > BOTTOM_PEDESTRIAN_WAIT_Y:
                    pedestrian.y = max(BOTTOM_PEDESTRIAN_WAIT_Y, pedestrian.y - pedestrian.speed * dt)
                elif pedestrian.y >= BOTTOM_PEDESTRIAN_WAIT_Y - 0.5 and not can_start_crossing:
                    pedestrian.y = float(BOTTOM_PEDESTRIAN_WAIT_Y)
                else:
                    pedestrian.y += delta
                if pedestrian.y < 20:
                    pedestrian.y = float(FRAME_HEIGHT - 10 + self._simulation_rng.randint(0, 36))

    def _refresh_simulation_locked(self) -> None:
        now_mono = time.monotonic()
        if self._simulation_last_update_monotonic is None:
            self._simulation_last_update_monotonic = now_mono
        dt = now_mono - self._simulation_last_update_monotonic
        self._simulation_last_update_monotonic = now_mono
        if not self._simulation_paused:
            self._advance_simulation_locked(dt)
        tick = int(self._simulation_clock_s * 2)
        if self._simulation_frame is not None and tick == self._last_simulation_tick:
            return
        self._last_simulation_tick = tick
        self._simulation_view_frames.clear()
        self._frame_counter += 1
        now_ms = int(time.time() * 1000)
        canvas = np.full((FRAME_HEIGHT, FRAME_WIDTH, 3), (29, 33, 37), dtype=np.uint8)
        cv2.rectangle(canvas, (0, 0), (FRAME_WIDTH - 1, ROAD_TOP - 1), (72, 79, 84), thickness=-1)
        cv2.rectangle(canvas, (0, ROAD_TOP), (FRAME_WIDTH - 1, ROAD_BOTTOM - 1), (48, 52, 57), thickness=-1)
        cv2.rectangle(canvas, (0, ROAD_BOTTOM), (FRAME_WIDTH - 1, FRAME_HEIGHT - 1), (72, 79, 84), thickness=-1)
        cv2.line(canvas, (0, ROAD_TOP), (FRAME_WIDTH - 1, ROAD_TOP), (128, 136, 144), thickness=5)
        cv2.line(canvas, (0, ROAD_BOTTOM), (FRAME_WIDTH - 1, ROAD_BOTTOM), (128, 136, 144), thickness=5)
        for lane_y in (310, 500):
            for x in range(0, FRAME_WIDTH, 86):
                cv2.line(canvas, (x, lane_y), (min(x + 50, FRAME_WIDTH - 1), lane_y), (46, 176, 224), thickness=5)
        cv2.rectangle(canvas, (CROSSING_LEFT, ROAD_TOP), (CROSSING_RIGHT, ROAD_BOTTOM), (55, 59, 63), thickness=-1)
        for stripe_y in range(205, 610, 46):
            cv2.rectangle(
                canvas,
                (CROSSING_LEFT + 18, stripe_y),
                (CROSSING_RIGHT - 18, stripe_y + 22),
                (225, 228, 230),
                thickness=-1,
            )
        cv2.line(canvas, (EASTBOUND_STOP_LINE, ROAD_TOP), (EASTBOUND_STOP_LINE, ROAD_BOTTOM), (240, 240, 240), thickness=6)
        cv2.line(canvas, (WESTBOUND_STOP_LINE, ROAD_TOP), (WESTBOUND_STOP_LINE, ROAD_BOTTOM), (240, 240, 240), thickness=6)
        for vehicle in self._vehicles:
            _draw_vehicle(
                canvas,
                x=int(round(vehicle.x)),
                y=vehicle.y,
                width=vehicle.width,
                color=vehicle.color,
                vehicle_type=vehicle.vehicle_type,
            )
        stride_sign = 5 if tick % 2 == 0 else -5
        for index, pedestrian in enumerate(self._pedestrians):
            _draw_pedestrian(
                canvas,
                x=pedestrian.x,
                y=int(round(pedestrian.y)),
                color=pedestrian.color,
                stride=stride_sign if index % 2 == 0 else -stride_sign,
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
            width=FRAME_WIDTH,
            height=FRAME_HEIGHT,
            received_at_ms=now_ms,
            frame_number=self._frame_counter,
            origin="simulation",
        )



camera_frame_service = CameraFrameService()
