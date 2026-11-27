"""Single-owner, isolated native frame publishing contract for migration tests.

This is not CameraFrameService and is never registered as an authoritative
source. Existing zones, capture routes, AI and physical control stay untouched.
"""
from __future__ import annotations

from copy import deepcopy
import struct
import zlib
import cv2
import numpy as np
from app.services.camera_frames import CameraFrame

from app.services.sumo_projection import VIEW_FLIPS, PROVENANCE, WIDTH, HEIGHT, RASTER_PALETTE
from app.services.sumo_projection_capture import evaluation_frames
from app.services.observation_identity import EVALUATION_ORIGINS, evaluation_source_id


_PNG_SIGNATURE=b"\x89PNG\r\n\x1a\n"
_PALETTE=np.array(RASTER_PALETTE,np.uint8)
_CHANNEL_LUTS=tuple(np.pad(_PALETTE[:,i],(0,256-len(_PALETTE))) for i in range(3))


def _png_chunk(kind, data):
    return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data)&0xffffffff)


def encode_indexed_png(indices):
    """Trusted fixed-palette PNG, filter None, exact decoded BGR validation.
    One byte per pixel; no quantisation, external dependency or lossy conversion.
    """
    if indices.shape!=(HEIGHT,WIDTH) or indices.dtype!=np.uint8 or int(indices.max())>=len(_PALETTE):
        raise ValueError("Invalid native palette indices")
    rows=np.zeros((HEIGHT,WIDTH+1),np.uint8)
    rows[:,1:]=indices
    return (_PNG_SIGNATURE+_png_chunk(b"IHDR",struct.pack(">IIBBBBB",WIDTH,HEIGHT,8,3,0,0,0))
            +_png_chunk(b"PLTE",_PALETTE[:,::-1].tobytes())
            +_png_chunk(b"IDAT",zlib.compress(memoryview(rows),1))+_png_chunk(b"IEND",b""))


def validate_indexed_png(content,indices):
    if not content.startswith(_PNG_SIGNATURE):
        raise ValueError("Invalid indexed PNG signature")
    decoded=cv2.imdecode(np.frombuffer(content,np.uint8),cv2.IMREAD_COLOR)
    if decoded is None or decoded.shape!=(HEIGHT,WIDTH,3) or any(
        not np.array_equal(decoded[:,:,channel],cv2.LUT(indices,lut))
        for channel,lut in enumerate(_CHANNEL_LUTS)):
        raise ValueError("Native indexed PNG differs from raster")


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
        self._last_tick = -1
        self._minimum_tick = 0
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
        if type(tick) is not int or tick <= self._last_tick or tick < self._minimum_tick:
            raise ValueError("Native frame tick must advance")

    def publish(self, meta: dict, views: dict[str, bytes], *, received_at_ms: int) -> None:
        self._check_next(meta)
        try:
            frames = evaluation_frames(meta, views, received_at_ms=received_at_ms)
            self._meta = deepcopy(meta)
            self._last_tick = meta["tick"]
            self._frames = dict(zip(VIEW_FLIPS, frames))
            self._pixels = None
            self._received_at_ms = received_at_ms
        except Exception:
            self.invalidate()
            raise

    def retire_before(self,tick: int) -> None:
        """Release pixels/frames already retired by the owner clock."""
        self._minimum_tick=max(self._minimum_tick,tick)
        if self._meta is not None and self._meta["tick"]<tick:
            self._meta = self._pixels = self._received_at_ms = None
            self._frames = {}

    def has_tick(self, tick: int) -> bool:
        return self._meta is not None and self._meta["tick"] == tick

    def prepare(self, meta: dict, pixels: np.ndarray, *, received_at_ms: int, transfer_owned: bool=False, indexed: bool=False) -> None:
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
                type(indexed) is not bool or pixels.shape != ((HEIGHT, WIDTH) if indexed else (HEIGHT, WIDTH, 3)) or pixels.dtype != np.uint8 or
                (indexed and int(pixels.max())>=len(_PALETTE))):
                raise ValueError("Invalid native raster identity")
            # Only the internal renderer may transfer its newly allocated raster.
            # Keep defensive copy as the default for all external/test callers.
            if transfer_owned and (not pixels.flags.owndata or not pixels.flags.c_contiguous or not pixels.flags.writeable):
                raise ValueError("Raster transfer requires exclusive contiguous owned pixels")
            self._pixels = pixels if transfer_owned else pixels.copy()
            self._pixels.flags.writeable = False
            self._meta = deepcopy(meta)
            self._last_tick = meta["tick"]
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
            if expected.ndim==2:
                content=encode_indexed_png(expected)
                validate_indexed_png(content,expected)
            else:
                ok, encoded = cv2.imencode(".png", expected)
                if not ok:
                    raise RuntimeError("Native projection PNG encoding failed")
                content = encoded.tobytes()
                decoded = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
                if not content.startswith(_PNG_SIGNATURE) or decoded is None or not np.array_equal(decoded, expected):
                    raise ValueError("Native encoded view differs from raster")
            frame = CameraFrame(content=content, content_type="image/png",
                source_id=evaluation_source_id(self._provenance,self._generation,source), width=WIDTH, height=HEIGHT,
                received_at_ms=self._received_at_ms, frame_number=self._meta["tick"],
                origin=self._provenance, mode_generation=self._generation,
                simulation_engine="native" if self._meta.get("demand_model")=="native_cyclic_slots_v1" else None,
                simulation_demand_digest=self._meta.get("demand_digest"),
                coordinate_space=self._meta.get("coordinate_space"),layout_id=self._meta.get("layout_id"),
                observation_epoch=self._meta.get("epoch"))
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
