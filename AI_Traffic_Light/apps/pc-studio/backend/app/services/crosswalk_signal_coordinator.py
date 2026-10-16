"""Simulation-only interlock for explicitly configured Network movement conflicts.

This supervises the published virtual signals. A blocked crossing's local phase
clock is paused by CrosswalkSignalService; no physical output is produced.
"""
from __future__ import annotations

from typing import Any

CLEARANCE_SECONDS = 2.0

MOVEMENT_BY_PHASE = {
    "vehicle_green": "vehicle",
    "vehicle_yellow": "vehicle",
    "pedestrian_green": "pedestrian",
    "pedestrian_flashing": "pedestrian",
}


def movement_of(state: dict[str, Any]) -> str | None:
    return MOVEMENT_BY_PHASE.get(str(state.get("phase")))


def movements_conflict(
    links: list[dict[str, Any]], source: str, source_movement: str,
    destination: str, destination_movement: str,
) -> bool:
    for link in links:
        a, b = link["source_crosswalk_id"], link["destination_crosswalk_id"]
        configured = link.get("movement_conflicts", [])
        if source == a and destination == b:
            pair = source_movement + "_" + destination_movement
        elif source == b and destination == a:
            pair = destination_movement + "_" + source_movement
        else:
            continue
        if pair in configured:
            return True
    return False


def coordinate_crosswalk_signals(
    states: dict[str, dict[str, Any]],
    links: list[dict[str, Any]],
    *,
    now: float,
    previous_grants: dict[str, str],
    released: dict[str, tuple[str, float]],
    emergency_targets: set[str] | None = None,
    previous_held: set[str] | None = None,
) -> tuple[dict[str, dict[str, Any]], set[str], dict[str, str], dict[str, tuple[str, float]]]:
    """Grant compatible virtual movement permissions, never conflicting greens.

    Existing grants retain precedence until their protected phase completes.
    A newly requested conflicting permission waits at virtual all-red for a
    minimum gap after the other movement loses its permission.
    """
    enabled = [link for link in links if link.get("movement_conflicts")]
    if not enabled:
        return states, set(), {}, {}
    wanted = {crossing: movement_of(state) for crossing, state in states.items()}
    recent = dict(released)
    for crossing, movement in previous_grants.items():
        if wanted.get(crossing) != movement:
            recent[crossing] = (movement, now)
    emergency_targets = emergency_targets or set()
    previous_held = previous_held or set()

    def rank(crossing: str) -> tuple[int, int, int, str]:
        state = states[crossing]
        continuing = int(wanted[crossing] is not None and previous_grants.get(crossing) == wanted[crossing])
        waiting = int(wanted[crossing] is not None and crossing in previous_held)
        protected_clearance = int(state.get("phase") == "pedestrian_flashing")
        emergency = int(crossing in emergency_targets and wanted[crossing] == "vehicle")
        return (-continuing, -waiting, -protected_clearance * 2 - emergency, crossing)

    grants: dict[str, str] = {}
    held: set[str] = set()
    reservations: dict[str, str] = {}
    output: dict[str, dict[str, Any]] = {}
    for crossing in sorted(states, key=rank):
        requested = wanted[crossing]
        blocked_by: str | None = None
        wait: float | None = None
        if requested:
            for other, other_movement in reservations.items():
                if movements_conflict(links, crossing, requested, other, other_movement):
                    blocked_by = other
                    break
            for other, other_movement in grants.items():
                if blocked_by:
                    break
                if movements_conflict(links, crossing, requested, other, other_movement):
                    blocked_by = other
                    break
            if not blocked_by:
                for other, (movement, ended_at) in recent.items():
                    if other != crossing and now - ended_at < CLEARANCE_SECONDS and movements_conflict(
                        links, crossing, requested, other, movement
                    ):
                        blocked_by = other
                        wait = round(max(0.0, CLEARANCE_SECONDS - (now - ended_at)), 1)
                        if crossing in previous_held:
                            reservations[crossing] = requested
                        break
        if blocked_by:
            held.add(crossing)
            reason = (
                "Waiting for " + blocked_by + " to clear a conflicting movement"
                + (f" ({wait:.1f}s minimum clearance remaining)" if wait is not None else "")
            )
            output[crossing] = {
                **states[crossing],
                "phase": "all_red",
                "phase_key": "coordination_hold",
                "vehicle_go": False,
                "pedestrian_walk": False,
                "pedestrian_clear": False,
                "seconds_remaining": 0.0,
                "coordination_hold": True,
                "coordination_requested_phase": states[crossing].get("phase_key"),
                "coordination_blocked_by": blocked_by,
                "coordination_wait_seconds": wait,
                "coordination_reason": reason,
            }
        else:
            if requested:
                grants[crossing] = requested
                recent.pop(crossing, None)
            output[crossing] = {
                **states[crossing],
                "coordination_hold": False,
                "coordination_requested_phase": None,
                "coordination_blocked_by": None,
                "coordination_wait_seconds": None,
                "coordination_reason": (
                    "Protected movement permitted by Network conflict interlock"
                    if requested else "All-red or no active movement"
                ),
            }
    # If a previously granted movement was blocked by a newly configured link,
    # force a virtual red now and require clearance before future conflicting grants.
    for crossing, movement in previous_grants.items():
        if crossing not in grants and wanted.get(crossing) == movement:
            recent[crossing] = (movement, now)
    return output, held, grants, recent
