from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
import hashlib
import json
from uuid import uuid4
from dataclasses import dataclass
import os
import random
import re
from threading import Lock
import time

import cv2
import numpy as np

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.services.signal_rules import signal_rules_service
from app.services.observation_identity import (ObservationIdentity, observation_provenance,
    SIMULATION_VIEW_FLIPS, simulation_view_point, synthetic_scene_identity)
from app.services.simulation_adapter import LegacySimulationAdapter
from app.services.legacy_world import (FRAME_WIDTH, FRAME_HEIGHT, ROAD_TOP, ROAD_BOTTOM,
    CROSSING_LEFT, CROSSING_RIGHT, EASTBOUND_STOP_LINE, WESTBOUND_STOP_LINE,
    TOP_PEDESTRIAN_WAIT_Y, BOTTOM_PEDESTRIAN_WAIT_Y, DENSITY_COUNTS, DENSITY_SEED_OFFSETS,
    vehicle_specs, pedestrian_specs, advance_vehicles, advance_pedestrians)
from app.services.sumo_shadow_runtime import ShadowRuntime

MAX_FRAME_BYTES = 8 * 1024 * 1024
MAX_FRAME_PIXELS = 16 * 1024 * 1024  # Reject decompression bombs before image decoding.
SOURCE_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
SUPPORTED_UPLOAD_TYPES = {"image/jpeg", "image/png"}
SIMULATION_DENSITIES = set(DENSITY_COUNTS)
# Fixed legacy editor plane: no native metre calibration is implied.
LEGACY_LAYOUT_ID = hashlib.sha256(json.dumps({
    'schema':'legacy_camera_pixels_v1','dimensions':[FRAME_WIDTH,FRAME_HEIGHT],
    'road':[ROAD_TOP,ROAD_BOTTOM],'crossing':[CROSSING_LEFT,CROSSING_RIGHT],
    'stop_lines':[EASTBOUND_STOP_LINE,WESTBOUND_STOP_LINE],
    'curbs':[TOP_PEDESTRIAN_WAIT_Y,BOTTOM_PEDESTRIAN_WAIT_Y],
    'views':SIMULATION_VIEW_FLIPS},sort_keys=True,separators=(',',':')).encode()).hexdigest()


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
    session_generation: int | None = None
    source_epoch: int | None = None
    mode_generation: int | None = None

    @property
    def observation(self) -> ObservationIdentity:
        """Internal projection; retain the original frame and public metadata."""
        return ObservationIdentity(
            source_id=self.source_id, frame_number=self.frame_number,
            received_at_ms=self.received_at_ms, width=self.width, height=self.height,
            provenance=observation_provenance(self.origin, self.session_generation),
            session_generation=self.session_generation, source_epoch=self.source_epoch,
            mode_generation=self.mode_generation,
        )

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


def _is_decodable_image(content: bytes, dimensions: tuple[int, int]) -> bool:
    """Validate legacy HTTP uploads without slowing the ESP TCP frame hot path."""
    try:
        decoded = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    except cv2.error:
        return False
    return decoded is not None and (decoded.shape[1], decoded.shape[0]) == dimensions


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
    height = {"car": 58, "suv": 64, "van": 70, "bus": 78}[vehicle_type]
    body_top = y - height // 2
    body_bottom = y + height // 2
    cv2.rectangle(canvas, (x, body_top), (x + width, body_bottom), color, thickness=-1)
    if vehicle_type in {"car", "suv"}:
        roof_left = x + width // (4 if vehicle_type == "car" else 6)
        roof_right = x + (width * (3 if vehicle_type == "car" else 5)) // (4 if vehicle_type == "car" else 6)
        cv2.rectangle(canvas, (roof_left, body_top - 22), (roof_right, body_top + 4), color, thickness=-1)
        cv2.rectangle(canvas, (roof_left + 7, body_top - 17), (roof_right - 7, body_top - 2), (77, 93, 110), thickness=-1)
    else:
        window_step = 35 if vehicle_type == "bus" else 50
        for window_x in range(x + 16, x + width - 20, window_step):
            cv2.rectangle(
                canvas,
                (window_x, body_top + 10),
                (min(window_x + window_step - 10, x + width - 12), body_top + 31),
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

    def __init__(self, *, simulation_seed: int | None = None,
                 simulation_monotonic: Callable[[], float] | None = None,
                 shadow: ShadowRuntime | None = None) -> None:
        self._lock = Lock()
        self._shadow = shadow
        self._simulation_monotonic = simulation_monotonic or time.monotonic
        self._uploaded_frame: CameraFrame | None = None
        self._simulation_frame: CameraFrame | None = None
        self._simulation_scene: dict | None = None
        self._simulation_epoch = uuid4().hex
        # Reuse the current render for mirrored views instead of decoding PNG.
        self._simulation_canvas: np.ndarray | None = None
        self._simulation_view_frames: dict[str, CameraFrame] = {}
        self._simulation_source_id = "simulation_camera"
        self._simulation_enabled = False
        self._observation_mode_generation = 0
        self._simulation_density = "normal"
        self._simulation_seed = (int(time.time() * 1000) & 0x7FFFFFFF) if simulation_seed is None else simulation_seed
        self._frame_counter = 0
        self._last_simulation_tick = -1
        self._simulation_adapter = LegacySimulationAdapter(self._step_simulation_world_locked)
        self._vehicles: list[_SimVehicle] = []
        self._pedestrians: list[_SimPedestrian] = []
        self._simulation_rng = random.Random(self._simulation_seed)

    @property
    def _simulation_clock_s(self) -> float:
        return self._simulation_adapter.time_s

    @_simulation_clock_s.setter
    def _simulation_clock_s(self, value: float) -> None:
        # Preserve the existing controlled regression-fixture seam.
        self._simulation_adapter.reanchor_time(value)

    @property
    def _simulation_paused(self) -> bool:
        return self._simulation_adapter.paused

    def clear_uploaded_source(self, source_id: str) -> None:
        """Invalidate only the receiver image belonging to this source."""
        with self._lock:
            if self._uploaded_frame is not None and self._uploaded_frame.source_id == source_id:
                self._uploaded_frame = None

    @property
    def observation_mode_token(self) -> tuple[bool, int]:
        with self._lock:
            return self._simulation_enabled, self._observation_mode_generation

    def store_upload(self, *, source_id: str, content_type: str, content: bytes, validate_decode: bool = False) -> CameraFrame:
        return self._create_upload(
            source_id=source_id, content_type=content_type, content=content,
            validate_decode=validate_decode, publish=True,
        )

    def prepare_upload(self, *, source_id: str, content_type: str, content: bytes, received_at_ms: int,
                       session_generation: int | None = None, source_epoch: int | None = None) -> CameraFrame:
        """Allocate one validated frame identity without changing the selected image."""
        return self._create_upload(
            source_id=source_id, content_type=content_type, content=content,
            received_at_ms=received_at_ms, publish=False,
            session_generation=session_generation, source_epoch=source_epoch,
        )

    def publish_cached_upload(self, frame: CameraFrame) -> CameraFrame:
        """Promote an already validated receiver frame without allocating a new observation."""
        with self._lock:
            self._uploaded_frame = frame
            return frame

    def _create_upload(
        self, *, source_id: str, content_type: str, content: bytes,
        publish: bool, validate_decode: bool = False, received_at_ms: int | None = None,
        session_generation: int | None = None, source_epoch: int | None = None,
    ) -> CameraFrame:
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
        if validate_decode and dimensions is not None:
            if dimensions[0] * dimensions[1] > MAX_FRAME_PIXELS or not _is_decodable_image(content, dimensions):
                dimensions = None
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
                received_at_ms=int(time.time() * 1000) if received_at_ms is None else received_at_ms,
                frame_number=self._frame_counter,
                origin="upload", session_generation=session_generation,
                source_epoch=source_epoch, mode_generation=self._observation_mode_generation,
            )
            if publish:
                self._uploaded_frame = frame
            return frame

    def _reset_simulation_locked(self) -> None:
        self._simulation_frame = None
        self._simulation_scene = None
        self._simulation_canvas = None
        self._simulation_view_frames.clear()
        self._last_simulation_tick = -1
        self._simulation_adapter.reset(seed=self._simulation_seed, now=self._simulation_monotonic(),
                                       paused=self._simulation_paused)
        signal_rules_service.reset_runtime(0.0)
        density_offset = DENSITY_SEED_OFFSETS[self._simulation_density]
        self._simulation_rng = random.Random(self._simulation_seed + density_offset)
        self._initialize_agents_locked()
        if self._shadow is not None:
            self._shadow.reset(self._simulation_seed)

    def set_simulation(self, enabled: bool) -> dict:
        with self._lock:
            self._simulation_enabled = enabled
            self._observation_mode_generation += 1
            self._simulation_adapter.stop()
            if enabled:
                self._reset_simulation_locked()
            else:
                if self._shadow is not None:
                    self._shadow.stop()
                self._simulation_frame = None
                self._simulation_scene = None
                self._simulation_canvas = None
                self._simulation_view_frames.clear()
                self._last_simulation_tick = -1
                self._vehicles = []
                self._pedestrians = []
                signal_rules_service.reset_runtime(0.0)
        return self.status()

    def configure_simulation(self, *, density: str | None = None, paused: bool | None = None) -> dict:
        with self._lock:
            reset_agents = False
            if paused is not None and not self._simulation_enabled:
                raise AppError(ErrorCode.CAMERA_STREAM_NOT_STARTED,
                    'Start simulation mode before pausing or resuming the synthetic scene.', status_code=409)
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
                if paused != self._simulation_paused:
                    self._simulation_adapter.set_paused(paused, self._simulation_monotonic())
                    if not paused:
                        self._simulation_frame = None
                        self._simulation_scene = None
                        self._simulation_canvas = None
                        self._last_simulation_tick = -1
            if reset_agents and self._simulation_enabled:
                # A reset retires pending inference even when simulation stays enabled.
                self._observation_mode_generation += 1
                self._reset_simulation_locked()
        return self.status()

    def set_simulation_source(self, source_id: str) -> None:
        if source_id not in SIMULATION_CAMERA_SOURCE_IDS:
            raise ValueError("Unknown simulation camera")
        with self._lock:
            self._simulation_source_id = source_id

    def _simulation_frame_for_locked(self, source_id: str, *, refresh: bool = True) -> CameraFrame | None:
        if not self._simulation_enabled:
            return None
        if refresh and (self._simulation_frame is None or not self._simulation_paused):
            self._refresh_simulation_locked()
        original = self._simulation_frame
        if source_id not in SIMULATION_CAMERA_SOURCE_IDS:
            raise ValueError("Unknown simulation camera")
        if original is None or source_id == SIMULATION_CAMERA_PAIRS[0][0]:
            return original
        cached = self._simulation_view_frames.get(source_id)
        if cached is None or cached.frame_number != original.frame_number:
            image = self._simulation_canvas
            if image is None:
                raise AppError(ErrorCode.CAMERA_FRAME_READ_FAILED, "Simulation render cache unavailable.", status_code=500)
            # Each pair shows vertically mirrored sides; pair 2 uses a horizontal viewpoint.
            flip = SIMULATION_VIEW_FLIPS[source_id]
            success, encoded = cv2.imencode(".png", cv2.flip(image, flip))
            if not success:
                raise AppError(ErrorCode.CAMERA_FRAME_READ_FAILED, "Mirrored simulation frame encoding failed.", status_code=500)
            cached = CameraFrame(
                content=encoded.tobytes(), content_type="image/png",
                source_id=source_id, width=original.width, height=original.height,
                received_at_ms=original.received_at_ms, frame_number=original.frame_number,
                origin="simulation", mode_generation=original.mode_generation,
            )
            self._simulation_view_frames[source_id] = cached
        return cached

    def simulation_frame_for(self, source_id: str) -> CameraFrame | None:
        with self._lock:
            return self._simulation_frame_for_locked(source_id)

    def simulation_frames_for(self, source_ids) -> list[CameraFrame]:
        """One world publication for an entire multi-camera inference batch."""
        ids = tuple(dict.fromkeys(source_ids))
        if any(sid not in SIMULATION_CAMERA_SOURCE_IDS for sid in ids):
            raise ValueError("Unknown simulation camera")
        with self._lock:
            if not self._simulation_enabled or not ids:
                return []
            if self._simulation_frame is None or not self._simulation_paused:
                self._refresh_simulation_locked()
            return [frame for sid in ids
                    if (frame := self._simulation_frame_for_locked(sid, refresh=False)) is not None]

    def exact_simulation_frame(self, *, epoch, generation, tick, layout_id, source_id):
        """Read the requested current publication without stepping or selecting."""
        with self._lock:
            if (not self._simulation_enabled or self._simulation_frame is None or
                epoch != self._simulation_epoch or generation != self._observation_mode_generation or
                tick != self._simulation_frame.frame_number or layout_id != LEGACY_LAYOUT_ID):
                raise AppError(ErrorCode.CAMERA_STREAM_NOT_STARTED,
                    "Retired legacy simulation publication or layout.", status_code=409)
            return self._simulation_frame_for_locked(source_id, refresh=False)

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
            # The scene must describe the actual published raster, not a newer
            # world step under the same frame identity.
            if self._simulation_scene is None:
                raise AppError(ErrorCode.CAMERA_FRAME_READ_FAILED,
                    "Simulation scene cache unavailable.", status_code=500)
            scene = deepcopy(self._simulation_scene)
            scene.update(source_id=source_id, frame_number=frame.frame_number,
                         received_at_ms=frame.received_at_ms, paused=self._simulation_paused)
            scene["observation"] = synthetic_scene_identity(
                epoch=self._simulation_epoch, generation=frame.mode_generation,
                tick=frame.frame_number, source_id=source_id, view_id=source_id,
                frame_number=frame.frame_number, received_at_ms=frame.received_at_ms,
                coordinate_space="legacy_camera_pixels_v1", layout_id=LEGACY_LAYOUT_ID,
                width=frame.width, height=frame.height, provenance="simulation",
                tick_kind="published_frame", detector_input_eligible=True)
            # Keep existing canonical vehicle/pedestrian arrays for the 3D
            # renderer; expose exact mirrored image-centres separately.
            scene["view_agents"] = [
                {"id": a["id"], "kind": kind, "x": x, "y": y}
                for kind, agents in (("vehicle",scene["vehicles"]),("pedestrian",scene["pedestrians"]))
                for a in agents
                for x,y in [simulation_view_point(
                    a["x"] + (a["width"]/2 if kind == "vehicle" else 0),
                    a["y"], FRAME_WIDTH, FRAME_HEIGHT, source_id)]]
            return scene

    def _snapshot_simulation_scene_locked(self) -> dict:
        clock = self._simulation_adapter.snapshot()
        signal = self._simulation_signal_state_locked()
        return {
            "width": FRAME_WIDTH,
            "height": FRAME_HEIGHT,
            "simulation_time_seconds": round(clock.time_s, 3),
            "paused": clock.paused,
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

    def shadow_diagnostics(self) -> dict:
        if self._shadow is None:
            return {"status": "disabled", "provenance": "synthetic_sumo_shadow", "snapshot": None}
        return self._shadow.status()

    def native_projection_diagnostics(self, *, scene_only: bool = False) -> dict:
        if self._shadow is None:
            return {"status": "disabled", "provenance": "synthetic_sumo_projection", "snapshot": None}
        return self._shadow.projection_bundle(scene_only=scene_only)

    def native_projection_frame(self, source_id: str, *, generation: int, tick: int) -> CameraFrame | None:
        if source_id not in SIMULATION_CAMERA_SOURCE_IDS:
            raise ValueError("Unknown native simulation view")
        if self._shadow is None:
            return None
        return self._shadow.projection_frame(source_id, generation=generation, tick=tick)

    def close_shadow(self) -> None:
        if self._shadow is not None:
            self._shadow.close()

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
        vehicle_palette = [
            (66, 135, 245), (94, 176, 110), (230, 144, 81),
            (181, 105, 200), (94, 188, 214), (122, 128, 137),
        ]
        pedestrian_palette = [
            (196, 111, 255), (119, 187, 255), (119, 220, 157),
            (255, 158, 132), (164, 142, 245), (114, 212, 229),
        ]
        self._vehicles = [
            _SimVehicle(x=v.x,y=v.y,width=v.width,speed=v.speed,direction=v.direction,
                        color=vehicle_palette[i % len(vehicle_palette)],vehicle_type=v.vehicle_type)
            for i,v in enumerate(vehicle_specs(self._simulation_density,self._simulation_rng))]
        self._pedestrians = [
            _SimPedestrian(x=v.x,y=v.y,speed=v.speed,direction=v.direction,
                           color=pedestrian_palette[i % len(pedestrian_palette)])
            for i,v in enumerate(pedestrian_specs(self._simulation_density,self._simulation_rng))]

    def _advance_simulation_locked(self, dt: float) -> None:
        self._simulation_adapter.step(dt)

    def _step_simulation_world_locked(self, step: float) -> None:
        # Both movement types must obey the same protected phase snapshot.
        phase = self._simulation_signal_state_locked()["phase"]
        self._advance_vehicles_locked(step, phase)
        self._advance_pedestrians_locked(step, phase)
        if self._shadow is not None:
            self._shadow.observe(phase)

    def _advance_vehicles_locked(self, dt: float, phase: str) -> None:
        advance_vehicles(self._vehicles,self._simulation_rng,dt,phase=="vehicle_green")

    def _advance_pedestrians_locked(self, dt: float, phase: str) -> None:
        advance_pedestrians(self._pedestrians,self._simulation_rng,dt,phase=="pedestrian_green")

    def _refresh_simulation_locked(self) -> None:
        self._simulation_adapter.sync(self._simulation_monotonic())
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
        self._simulation_scene = self._snapshot_simulation_scene_locked()
        self._simulation_canvas = canvas
        self._simulation_frame = CameraFrame(
            content=encoded.tobytes(),
            content_type="image/png",
            source_id="simulation_camera",
            width=FRAME_WIDTH,
            height=FRAME_HEIGHT,
            received_at_ms=now_ms,
            frame_number=self._frame_counter,
            origin="simulation", mode_generation=self._observation_mode_generation,
        )



camera_frame_service = CameraFrameService(
    shadow=ShadowRuntime(projection_enabled=os.getenv("MESH_SUMO_PROJECTION") == "1")
    if os.getenv("MESH_SUMO_SHADOW") == "1" else None
)
