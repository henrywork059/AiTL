"""Source-qualified observations; additive analytics, never signal authority."""
from __future__ import annotations

from time import time
from typing import Any

from app.services.observation_identity import ObservationIdentity
from app.services.tracking_scope import TRACKING_MAX_GAP_MS, TrackingScope

STATIONARY_RADIUS_REFERENCE_PX = 8.0
STATIONARY_MIN_MS = 1000


def observation_fields(observation: ObservationIdentity, scope: TrackingScope) -> dict[str, Any]:
    return {
        "source_id": observation.source_id,
        "intersection_id": scope.intersection_id,
        "provenance": observation.provenance,
        "source_timestamp_ms": observation.received_at_ms,
        "source_frame_number": observation.frame_number,
        "session_generation": observation.session_generation,
        "source_epoch": observation.source_epoch,
        "mode_generation": observation.mode_generation,
    }


def unavailable_observation() -> dict[str, Any]:
    return {
        "available": False, "source_id": None, "intersection_id": None,
        "provenance": "unavailable", "source_timestamp_ms": None,
        "source_frame_number": None, "occupancy": None, "queue": None,
    }


def selected_observation_is_current(observation: ObservationIdentity) -> bool:
    """Check selected lifetime, not equality to the newest frame after inference."""
    # Lazy imports preserve the existing camera/manager ownership and import graph.
    from app.services.camera_frames import camera_frame_service
    from app.services.remote_camera_manager import remote_camera_manager

    if not 0 <= int(time() * 1000) - observation.received_at_ms <= TRACKING_MAX_GAP_MS:
        return False
    mode = camera_frame_service.observation_mode_token
    if observation.mode_generation != mode[1]:
        return False
    current = camera_frame_service.latest_frame()
    if current is None:
        return False
    identity = current.observation
    if (identity.source_id, identity.provenance, identity.session_generation,
        identity.source_epoch, identity.mode_generation) != (
        observation.source_id, observation.provenance, observation.session_generation,
        observation.source_epoch, observation.mode_generation):
        return False
    if observation.provenance == "esp32_stream":
        if observation.source_epoch is None:
            return False
        return remote_camera_manager.observation_is_current(
            observation.source_id, (mode, observation.source_epoch), observation.received_at_ms
        )
    return (observation.provenance == "simulation" and mode[0]) or (
        observation.provenance == "external_upload" and not mode[0]
    )


def event_attribution(record: dict[str, Any]) -> tuple[str | None, str | None, str]:
    """Historical records have no inferred source/junction or physical provenance."""
    return (record.get("source_id"), record.get("intersection_id"),
            record.get("provenance") or "unknown")


def observation_for_junction(observation: dict[str, Any], intersection_id: str,
                             source_id: str | None, *, now_ms: int) -> dict[str, Any]:
    stamp = observation.get("source_timestamp_ms")
    if (not observation.get("available") or not source_id
        or observation.get("source_id") != source_id
        or observation.get("intersection_id") != intersection_id
        or not isinstance(stamp, int)
        or not 0 <= now_ms - stamp <= TRACKING_MAX_GAP_MS):
        return unavailable_observation()
    return observation
