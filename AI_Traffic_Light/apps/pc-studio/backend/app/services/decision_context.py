from __future__ import annotations

from hashlib import sha1
from typing import Any


def _provenance(*, simulation_enabled: bool, traffic_state: dict[str, Any]) -> str:
    explicit = traffic_state.get("observation_provenance")
    if explicit in {"ai_detection", "simulation", "manual_test", "unavailable"}:
        return str(explicit)
    if simulation_enabled:
        return "simulation"
    if traffic_state.get("source_timestamp_ms") is not None and not str(traffic_state.get("data_source", "")).startswith("inference_unavailable"):
        return "ai_detection"
    return "unavailable"


def _scenario_conditions(signal: dict[str, Any]) -> list[dict[str, Any]]:
    winner_id = signal.get("winning_scenario_id")
    if not winner_id:
        return []
    for item in signal.get("scenario_status", signal.get("rule_status", [])):
        if item.get("scenario_id", item.get("rule_id")) == winner_id:
            return [dict(condition) for condition in item.get("conditions", []) if isinstance(condition, dict)]
    return []


def _category(signal: dict[str, Any], state: dict[str, Any]) -> str:
    if signal.get("incident_hold"):
        return "incident_test_hold"
    request = signal.get("pending_request")
    if request == "pedestrian":
        return "pedestrian_service"
    if request == "vehicle":
        return "vehicle_service"
    if signal.get("winning_scenario_id"):
        return "ranked_scenario"
    if state.get("pedestrians_crossing", 0) or state.get("pedestrians_waiting", 0):
        return "pedestrian_observation"
    if state.get("vehicles_waiting", 0):
        return "vehicle_observation"
    return "normal_timing"


def build_decision_context(
    state: dict[str, Any],
    *,
    network_resolution: dict[str, Any],
    simulation_enabled: bool,
) -> dict[str, Any]:
    """Build one deterministic, judge-readable decision context record.

    This is a structured live explanation surface, not a second controller and
    not a claim of historical causal reconstruction. Existing V025 signal-rule
    history remains authoritative for applied controller events.
    """

    signal = state.get("signal_policy") if isinstance(state.get("signal_policy"), dict) else {}
    intersection_id = str(network_resolution["intersection_id"])
    provenance = _provenance(simulation_enabled=simulation_enabled, traffic_state=state)
    test_inputs = signal.get("test_inputs") if isinstance(signal.get("test_inputs"), dict) else {}
    manual_test_active = bool(
        signal.get("mode") == "test"
        and any(bool(test_inputs.get(key)) for key in ("mobility_assistance", "incident_person_fallen"))
    )
    conditions = _scenario_conditions(signal)
    winner_id = signal.get("winning_scenario_id")
    winner_label = signal.get("winning_scenario_label")
    phase = str(state.get("phase") or "unknown")
    frame_number = state.get("evaluated_frame_number")
    source_timestamp = state.get("source_timestamp_ms")
    identity_source = "|".join(
        [
            intersection_id,
            str(frame_number if frame_number is not None else "no-frame"),
            str(source_timestamp if source_timestamp is not None else state.get("evaluated_at_ms", "no-time")),
            phase,
            str(winner_id or state.get("decision") or "normal"),
        ]
    )
    decision_id = f"dec_{sha1(identity_source.encode('utf-8')).hexdigest()[:16]}"

    category = _category(signal, state)
    if winner_label:
        explanation = (
            f"{intersection_id}: {winner_label} is the highest-ranked eligible scenario; "
            f"the protected simulated phase is {phase.replace('_', ' ')}."
        )
    else:
        explanation = (
            f"{intersection_id}: no ranked scenario is currently executing; "
            f"the active output is {phase.replace('_', ' ')} using normal protected timing or fallback behavior."
        )
    if not simulation_enabled:
        explanation += " The traffic phase is a prototype recommendation/display output only."

    return {
        "decision_id": decision_id,
        "intersection_id": intersection_id,
        "intersection_label": network_resolution["intersection_label"],
        "category": category,
        "observation_provenance": provenance,
        "source_id": network_resolution.get("source_id"),
        "source_mapping_matched": bool(network_resolution.get("source_mapping_matched")),
        "phase": phase,
        "recommended_phase": state.get("recommended_phase"),
        "decision": state.get("decision"),
        "recommended_decision": state.get("recommended_decision"),
        "scenario": {
            "id": winner_id,
            "label": winner_label,
            "conditions": conditions,
        },
        "requested_service": signal.get("pending_request"),
        "timing": {
            "base_duration_seconds": signal.get("base_duration_seconds"),
            "effective_duration_seconds": signal.get("effective_duration_seconds"),
            "seconds_remaining": signal.get("seconds_remaining"),
        },
        "pedestrian_context": {
            "waiting": int(state.get("pedestrians_waiting", 0) or 0),
            "crossing": int(state.get("pedestrians_crossing", 0) or 0),
            "manual_accessibility_test": bool(test_inputs.get("mobility_assistance")) if manual_test_active else False,
        },
        "vehicle_context": {
            "waiting": int(state.get("vehicles_waiting", 0) or 0),
            "total": int(state.get("vehicles_total", 0) or 0),
        },
        "emergency_context": {
            "active": False,
            "source": None,
            "note": "Emergency recognition/pre-emption is not implemented in V025; future events must identify their source as simulated, manual, or AI-derived.",
        },
        "neighbor_context": network_resolution["network_context"].get("neighbors", []),
        "cooperative_control_active": False,
        "manual_test_input_active": manual_test_active,
        "explanation": explanation,
        "prototype_only": True,
    }
