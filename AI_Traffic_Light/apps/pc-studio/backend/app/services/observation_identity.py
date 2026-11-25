"""Immutable, internal identity of an accepted camera observation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ObservationProvenance = Literal["simulation", "esp32_stream", "external_upload", "unknown"]


@dataclass(frozen=True)
class ObservationIdentity:
    source_id: str
    frame_number: int
    received_at_ms: int
    width: int
    height: int
    provenance: ObservationProvenance
    session_generation: int | None = None
    source_epoch: int | None = None
    mode_generation: int | None = None

    @property
    def frame_key(self) -> tuple[str, int, int]:
        """Process-local observation key; selection is not acquisition."""
        return self.source_id, self.frame_number, self.received_at_ms


def observation_provenance(origin: str, session_generation: int | None) -> ObservationProvenance:
    if origin == "simulation":
        return "simulation"
    if origin == "upload":
        return "esp32_stream" if session_generation is not None else "external_upload"
    return "unknown"
