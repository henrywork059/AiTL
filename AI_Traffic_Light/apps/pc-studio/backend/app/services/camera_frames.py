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

SIMULATION_SIGNAL_SEQUENCE: tuple[tuple[str, float], ...] = (
    ("vehicle_green", 12.0),
    ("vehicle_yellow", 3.0),
    ("all_red", 3.0),
    ("pedestrian_green", 8.0),
    ("pedestrian_flashing", 6.0),
    ("all_red", 2.0),
)
SIMULATION_SIGNAL_CYCLE_SECONDS = sum(duration for _, duration in SIMULATION_SIGNAL_SEQUENCE)


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
    """Draw a compact walking pedestrian centred on ``x, y``."""
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


class CameraFrameService:
    """Store the latest uploaded frame and provide a signal-aware hardware-free simulator."""

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

    def _reset_simulation_locked(self) -> None:
        self._simulation_frame = None
        self._last_simulation_tick = -1
        self._simulation_clock_s = 0.0
        self._simulation_last_update_monotonic = time.monotonic()
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
                self._last_simulation_tick = -1
                self._simulation_last_update_monotonic = None
                self._vehicles = []
                self._pedestrians = []
        return self.status()

    def configure_simulation(self, *, density: str | None = None, paused: bool | None = None) -> dict:
        """Update synthetic-scene density or pause state without changing camera mode."""
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

    def latest_frame(self) -> CameraFrame | None:
        with self._lock:
            if self._simulation_enabled:
                if self._simulation_frame is None or not self._simulation_paused:
                    self._refresh_simulation_locked()
                return self._simulation_frame
            return self._uploaded_frame

    def simulation_signal_state(self) -> dict:
        """Return the deterministic signal state that simulated agents actually obey."""
        with self._lock:
            return dict(self._simulation_signal_state_locked())

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
            "simulation_signal_cycle_seconds": SIMULATION_SIGNAL_CYCLE_SECONDS if signal else None,
            "simulation_signal_vehicle_go": signal["vehicle_go"] if signal else False,
            "simulation_signal_pedestrian_walk": signal["pedestrian_walk"] if signal else False,
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

    def _simulation_signal_state_locked(self) -> dict:
        position = self._simulation_clock_s % SIMULATION_SIGNAL_CYCLE_SECONDS
        elapsed = 0.0
        for phase, duration in SIMULATION_SIGNAL_SEQUENCE:
            if position < elapsed + duration:
                remaining = elapsed + duration - position
                return {
                    "phase": phase,
                    "seconds_remaining": round(remaining, 1),
                    "vehicle_go": phase == "vehicle_green",
                    "pedestrian_walk": phase == "pedestrian_green",
                    "pedestrian_clear": phase == "pedestrian_flashing",
                }
            elapsed += duration
        return {
            "phase": "all_red",
            "seconds_remaining": 0.0,
            "vehicle_go": False,
            "pedestrian_walk": False,
            "pedestrian_clear": False,
        }

    def _initialize_agents_locked(self) -> None:
        vehicle_count = {"light": 4, "normal": 8, "busy": 12}[self._simulation_density]
        pedestrian_count = {"light": 4, "normal": 7, "busy": 11}[self._simulation_density]
        vehicle_palette = [
            (66, 135, 245),
            (94, 176, 110),
            (230, 144, 81),
            (181, 105, 200),
            (94, 188, 214),
            (122, 128, 137),
        ]
        pedestrian_palette = [
            (196, 111, 255),
            (119, 187, 255),
            (119, 220, 157),
            (255, 158, 132),
            (164, 142, 245),
            (114, 212, 229),
        ]

        self._vehicles = []
        per_direction = vehicle_count // 2
        for index in range(vehicle_count):
            direction = 1 if index % 2 == 0 else -1
            lane_index = index // 2
            vehicle_type = "bus" if index % 5 == 4 else "car"
            width = 220 if vehicle_type == "bus" else self._simulation_rng.randint(125, 170)
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
        self._frame_counter += 1
        now_ms = int(time.time() * 1000)
        signal = self._simulation_signal_state_locked()

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
        cv2.putText(canvas, "STOP", (410, 350), cv2.FONT_HERSHEY_SIMPLEX, 0.56, (220, 220, 220), 2)
        cv2.putText(canvas, "STOP", (800, 445), cv2.FONT_HERSHEY_SIMPLEX, 0.56, (220, 220, 220), 2)

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

        self._draw_signal_heads(canvas, signal)

        cv2.rectangle(canvas, (24, 20), (610, 137), (14, 17, 20), thickness=-1)
        cv2.putText(canvas, "PC CAMERA SIMULATION - SIGNAL AWARE", (46, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.70, (126, 231, 135), 2)
        cv2.putText(
            canvas,
            f"density: {self._simulation_density}   pedestrians: {len(self._pedestrians)}   vehicles: {len(self._vehicles)}",
            (46, 82),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.50,
            (217, 221, 224),
            1,
        )
        cv2.putText(
            canvas,
            f"signal: {signal['phase'].replace('_', ' ')}   {signal['seconds_remaining']:.1f}s",
            (46, 108),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.52,
            (217, 221, 224),
            1,
        )
        state_label = "PAUSED - inspection frame" if self._simulation_paused else f"frame {self._frame_counter}"
        cv2.putText(canvas, state_label, (46, 131), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (217, 221, 224), 1)

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

    @staticmethod
    def _draw_signal_heads(canvas: np.ndarray, signal: dict) -> None:
        phase = signal["phase"]
        red_on = phase not in {"vehicle_green", "vehicle_yellow"}
        amber_on = phase == "vehicle_yellow"
        green_on = phase == "vehicle_green"
        housing_x, housing_y = 1060, 185
        cv2.rectangle(canvas, (housing_x, housing_y), (housing_x + 78, housing_y + 222), (18, 20, 23), thickness=-1)
        lamps = [
            ((housing_x + 39, housing_y + 42), (35, 35, 120), (70, 70, 255), red_on),
            ((housing_x + 39, housing_y + 109), (35, 95, 110), (0, 205, 255), amber_on),
            ((housing_x + 39, housing_y + 176), (35, 95, 35), (60, 220, 80), green_on),
        ]
        for center, off_color, on_color, active in lamps:
            cv2.circle(canvas, center, 24, on_color if active else off_color, thickness=-1)

        ped_walk = phase == "pedestrian_green"
        ped_clear = phase == "pedestrian_flashing"
        cv2.rectangle(canvas, (1148, 218), (1262, 340), (18, 20, 23), thickness=-1)
        ped_text = "WALK" if ped_walk else "CLEAR" if ped_clear else "WAIT"
        ped_color = (70, 230, 90) if ped_walk else (0, 205, 255) if ped_clear else (70, 70, 255)
        cv2.putText(canvas, "PED", (1179, 251), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1)
        cv2.putText(canvas, ped_text, (1158, 303), cv2.FONT_HERSHEY_SIMPLEX, 0.58, ped_color, 2)


camera_frame_service = CameraFrameService()
