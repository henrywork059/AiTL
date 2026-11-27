"""Single-owner, isolated native frame publishing contract for migration tests.

This is not CameraFrameService and is never registered as an authoritative
source. Existing zones, capture routes, AI and physical control stay untouched.
"""
from __future__ import annotations

from copy import deepcopy
import cv2
import numpy as np
from app.services.camera_frames import CameraFrame

from app.services.sumo_projection import VIEW_FLIPS, PROVENANCE, WIDTH, HEIGHT
from app.services.sumo_projection_capture import evaluation_frames
from app.services.observation_identity import EVALUATION_ORIGINS, evaluation_source_id


class NativeFramePublisher:
    def __init__(self):
        self._generation = -1
        self._meta = None
        self._frames = {}
        self._pixels = None
        self._received_at_ms = None

    def begin(self, generation: int, *, provenance=PROVENANCE) -> None:
        if provenance not in EVALUATION_ORIGINS:
            raise ValueError("Invalid evaluation publication provenance")
        if type(generation) is not int or generation <= self._generation:
            raise ValueError("Native generation must advance")
        self.invalidate()
        self._generation = generation
        self._provenance = provenance
        self._active = True

    def invalidate(self) -> None:
        self._active = False
        self._meta = None
        self._frames = {}
        self._pixels = None
        self._received_at_ms = None

    def _check_next(self, meta):
        if not getattr(self, "_active", False) or meta.get("generation") != self._generation:
            raise ValueError("Inactive or retired native generation")
        if meta.get("provenance") != self._provenance:
            raise ValueError("Evaluation provenance changed within generation")
        tick = meta.get("tick")
        if self._meta is not None and (type(tick) is not int or tick <= self._meta["tick"]):
            raise ValueError("Native frame tick must advance")

    def publish(self, meta: dict, views: dict[str, bytes], *, received_at_ms: int) -> None:
        self._check_next(meta)
        try:
            frames = evaluation_frames(meta, views, received_at_ms=received_at_ms)
            self._meta = deepcopy(meta)
            self._frames = dict(zip(VIEW_FLIPS, frames))
            self._pixels = None
            self._received_at_ms = received_at_ms
        except Exception:
            self.invalidate()
            raise

    def has_tick(self, tick: int) -> bool:
        return self._meta is not None and self._meta["tick"] == tick

    def prepare(self, meta: dict, pixels: np.ndarray, *, received_at_ms: int) -> None:
        """Publish a trusted canonical raster; encode only requested views.

        The owner serializes calls. Retain a detached, read-only raster and at
        most four encoded frames for one tick. Validate each encoded view against
        its expected pixels, and retire all views on any failure.
        """
        self._check_next(meta)
        try:
            if (meta.get("provenance") != self._provenance or
                (meta.get("width"), meta.get("height")) != (WIDTH, HEIGHT) or
                type(meta.get("tick")) is not int or meta["tick"] < 0 or
                type(received_at_ms) is not int or received_at_ms < 0 or
                pixels.shape != (HEIGHT, WIDTH, 3) or pixels.dtype != np.uint8):
                raise ValueError("Invalid native raster identity")
            self._pixels = pixels.copy()
            self._pixels.flags.writeable = False
            self._meta = deepcopy(meta)
            self._received_at_ms = received_at_ms
            self._frames = {}
        except Exception:
            self.invalidate()
            raise

    def frame_for(self, source: str):
        if source not in VIEW_FLIPS:
            raise ValueError("Unknown native view")
        if source in self._frames or self._pixels is None:
            return self._frames.get(source)
        try:
            flip = VIEW_FLIPS[source]
            expected = self._pixels if flip is None else cv2.flip(self._pixels, flip)
            ok, encoded = cv2.imencode(".png", expected)
            if not ok:
                raise RuntimeError("Native projection PNG encoding failed")
            content = encoded.tobytes()
            decoded = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
            if not content.startswith(b"\x89PNG\r\n\x1a\n") or decoded is None or not np.array_equal(decoded, expected):
                raise ValueError("Native encoded view differs from raster")
            frame = CameraFrame(content=content, content_type="image/png",
                source_id=evaluation_source_id(self._provenance,self._generation,source), width=WIDTH, height=HEIGHT,
                received_at_ms=self._received_at_ms, frame_number=self._meta["tick"],
                origin=self._provenance, mode_generation=self._generation)
            self._frames[source] = frame
            if len(self._frames) == len(VIEW_FLIPS):
                self._pixels = None  # all validated views cached; release the raster
            return frame
        except Exception:
            self.invalidate()
            raise

    def scene_for(self, source: str) -> dict | None:
        frame = self.frame_for(source)
        if frame is None:
            return None
        meta = deepcopy(self._meta)
        flip = VIEW_FLIPS[source]
        for agent in meta["agents"]:
            if flip in (1, -1):
                agent["x"] = WIDTH - 1 - agent["x"]
            if flip in (0, -1):
                agent["y"] = HEIGHT - 1 - agent["y"]
        return {**meta, "source_id": frame.source_id,
                "view_id": source, "frame_number": frame.frame_number,
                "received_at_ms": frame.received_at_ms,
                "provenance": self._provenance}
