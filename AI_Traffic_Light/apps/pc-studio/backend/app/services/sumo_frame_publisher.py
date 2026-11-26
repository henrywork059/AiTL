"""Single-owner, isolated native frame publishing contract for migration tests.

This is not CameraFrameService and is never registered as an authoritative
source. Existing zones, capture routes, AI and physical control stay untouched.
"""
from __future__ import annotations

from copy import deepcopy

from app.services.sumo_projection import VIEW_FLIPS, PROVENANCE
from app.services.sumo_projection_capture import evaluation_frames


class NativeFramePublisher:
    def __init__(self):
        self._generation = -1
        self._meta = None
        self._frames = {}

    def begin(self, generation: int) -> None:
        if type(generation) is not int or generation <= self._generation:
            raise ValueError("Native generation must advance")
        self.invalidate()
        self._generation = generation
        self._active = True

    def invalidate(self) -> None:
        self._active = False
        self._meta = None
        self._frames = {}

    def publish(self, meta: dict, views: dict[str, bytes], *, received_at_ms: int) -> None:
        if not getattr(self, "_active", False) or meta.get("generation") != self._generation:
            raise ValueError("Inactive or retired native generation")
        tick = meta.get("tick")
        if self._meta is not None and (type(tick) is not int or tick <= self._meta["tick"]):
            raise ValueError("Native frame tick must advance")
        try:
            frames = evaluation_frames(meta, views, received_at_ms=received_at_ms)
            self._meta = deepcopy(meta)
            self._frames = dict(zip(VIEW_FLIPS, frames))
        except Exception:
            self.invalidate()
            raise

    def frame_for(self, source: str):
        if source not in VIEW_FLIPS:
            raise ValueError("Unknown native view")
        return self._frames.get(source)

    def scene_for(self, source: str) -> dict | None:
        frame = self.frame_for(source)
        if frame is None:
            return None
        return {**deepcopy(self._meta), "source_id": frame.source_id,
                "view_id": source, "frame_number": frame.frame_number,
                "received_at_ms": frame.received_at_ms,
                "provenance": PROVENANCE}
