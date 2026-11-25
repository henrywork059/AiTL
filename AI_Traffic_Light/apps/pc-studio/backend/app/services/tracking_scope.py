"""Selected-source tracking continuity and bounded frame replay protection."""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

TRACKING_MAX_GAP_MS = 5000
MAX_TRACKING_SOURCES = 256


@dataclass(frozen=True)
class TrackingScope:
    source_id: str
    intersection_id: str | None
    width: int
    height: int
    provenance: str | None = None
    session_generation: int | None = None
    source_epoch: int | None = None
    mode_generation: int | None = None


class TrackingContinuity:
    """One selected scope; remember source watermarks across active resets."""

    def __init__(self) -> None:
        self.scope: TrackingScope | None = None
        self.last_sample: tuple[int, int] | None = None
        self._watermarks: OrderedDict[str, tuple[int, int]] = OrderedDict()

    def reset_active(self) -> None:
        self.scope = None
        self.last_sample = None

    def classify(self, scope: TrackingScope, timestamp_ms: int, frame_number: int) -> str:
        sample = (timestamp_ms, frame_number)
        if scope == self.scope and sample == self.last_sample:
            return "repeat"
        prior = self._watermarks.get(scope.source_id)
        if prior is not None and sample <= prior:
            return "replay"
        new_scope = (scope != self.scope or self.last_sample is None
                     or frame_number < self.last_sample[1]
                     or timestamp_ms - self.last_sample[0] > TRACKING_MAX_GAP_MS)
        self.scope = scope
        self.last_sample = sample
        self._watermarks[scope.source_id] = sample
        self._watermarks.move_to_end(scope.source_id)
        while len(self._watermarks) > MAX_TRACKING_SOURCES:
            self._watermarks.popitem(last=False)
        return "reset" if new_scope else "advance"
