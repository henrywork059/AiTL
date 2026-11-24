"""Read-only device capability and health projection over existing camera status.

The camera manager owns saved profiles and runtime sessions. This module never
stores configuration, probes hardware, or issues a device/output command.
"""
from __future__ import annotations

from typing import Any, Mapping

DEVICE_CONTRACT_SCHEMA_VERSION = 1


def project_camera_device(status: Mapping[str, Any]) -> dict[str, Any]:
    """Describe one saved camera using only its source-qualified status snapshot.

    `support` names an existing software input path, not a verified connected
    physical accessory. `available` requires a fresh active frame source.
    Future physical outputs must remain explicitly unsupported and unavailable.
    """
    kind = status.get("kind")
    if kind not in {"esp32", "simulation"}:
        raise ValueError("Device projection requires a known camera kind")

    simulation = kind == "simulation"
    streaming = status.get("streaming") is True
    transport_connected = status.get("stream_connected") is True
    configured = status.get("connected") is True
    reachable = status.get("device_reachable") is True
    paused = status.get("paused_for_simulation") is True
    stale = status.get("frame_stale") is True
    frame_age = status.get("frame_age_ms")
    frame_age_ms = (frame_age if isinstance(frame_age, int) and not isinstance(frame_age, bool)
                    and frame_age >= 0 else None)
    last_error = status.get("last_error")
    last_error = last_error if isinstance(last_error, str) and last_error else None

    fresh = (streaming and transport_connected and not paused and not stale
             and (simulation or (configured and frame_age_ms is not None)))
    if simulation:
        state = "simulated" if fresh else "idle"
    elif not configured:
        state = "error" if last_error else "not_connected"
    elif paused:
        state = "paused"
    elif streaming and not transport_connected:
        state = "error" if last_error else "reconnecting"
    elif streaming and not fresh:
        state = "stale" if frame_age_ms is not None else "waiting_for_frame"
    elif fresh:
        state = "streaming"
    elif last_error:
        state = "error"
    else:
        state = "connected" if reachable else "unreachable"

    return {
        "schema_version": DEVICE_CONTRACT_SCHEMA_VERSION,
        "source_id": str(status["source_id"]),
        "device_type": "simulation_camera" if simulation else "esp32_camera",
        "control_owner": "pc_studio",
        "capabilities": {
            "camera_input": {
                "direction": "input",
                "support": "simulation-only" if simulation else "implemented",
                "available": fresh,
            },
            "lighting_output": {
                "direction": "output", "support": "unavailable", "available": False,
            },
            "speaker_output": {
                "direction": "output", "support": "unavailable", "available": False,
            },
        },
        "health": {
            "state": state,
            "control_connected": None if simulation else configured,
            "reachable": None if simulation else reachable,
            "streaming": streaming,
            "transport_connected": transport_connected,
            "frame_fresh": fresh,
            "frame_age_ms": frame_age_ms,
            "last_error": last_error,
        },
        "physical_output_allowed": False,
    }
