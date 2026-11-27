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


# Shared synthetic scene/image view contract. A source name never grants
# camera or controller authority; the selected-frame service owns that decision.
SIMULATION_VIEW_FLIPS = {"simulation_camera": None, "simulation_camera_b": 0,
                         "simulation_camera_c": 1, "simulation_camera_d": -1}


def simulation_view_point(x, y, width, height, view_id):
    flip = SIMULATION_VIEW_FLIPS[view_id]
    return (width - 1 - x if flip in (1, -1) else x,
            height - 1 - y if flip in (0, -1) else y)


def synthetic_scene_identity(*, epoch, generation, tick, source_id, view_id,
                             frame_number, received_at_ms, coordinate_space,
                             layout_id, width, height, provenance,
                             tick_kind, detector_input_eligible=False):
    """Scene metadata only, never an inference result or permission token."""
    if view_id not in SIMULATION_VIEW_FLIPS:
        raise ValueError("Unknown simulation view")
    return {"epoch": epoch, "generation": generation, "tick": tick,
            "source_id": source_id, "view_id": view_id,
            "frame_number": frame_number, "received_at_ms": received_at_ms,
            "coordinate_space": coordinate_space, "layout_id": layout_id,
            "width": width, "height": height, "provenance": provenance,
            "tick_kind": tick_kind, "observation_kind": "synthetic_ground_truth",
            "detector_observation": False, "authoritative": False,
            "detector_input_eligible": detector_input_eligible,
            "physical_output_allowed": False}


# Distinct origins are mandatory for isolated evaluation frames.
SUMO_EVALUATION_ORIGIN = "synthetic_sumo_projection"
REFERENCE_EVALUATION_ORIGIN = "synthetic_finite_reference_projection"
EVALUATION_ORIGINS = frozenset({SUMO_EVALUATION_ORIGIN, REFERENCE_EVALUATION_ORIGIN})


def evaluation_source_id(origin, generation, view_id):
    if origin not in EVALUATION_ORIGINS or view_id not in SIMULATION_VIEW_FLIPS:
        raise ValueError("Invalid isolated evaluation identity")
    prefix = "native_eval" if origin == SUMO_EVALUATION_ORIGIN else "reference_eval"
    return f"{prefix}_g{generation}_{view_id}"
