from __future__ import annotations

from collections import Counter
import csv
from io import StringIO
from typing import Any

EVIDENCE_SCHEMA_VERSION = 1


def build_network_decision_evidence(result: dict[str, Any]) -> dict[str, Any]:
    """Project mode-specific simulation evidence into one stable compact ledger.

    The detailed per-mode histories remain authoritative and are preserved on the
    experiment result. This ledger is an additive normalized index/projection so
    callers can inspect decisions without learning each historical event shape.
    """

    run_id = str(result.get("run_id") or "network_experiment")
    scenario = result.get("scenario") if isinstance(result.get("scenario"), dict) else {}
    modes = [str(item) for item in scenario.get("comparison", []) if isinstance(item, str)]
    if not modes:
        modes = [
            key
            for key, value in result.items()
            if isinstance(value, dict) and isinstance(value.get("intersections"), dict)
        ]

    records: list[dict[str, Any]] = []
    for mode in modes:
        payload = result.get(mode)
        if not isinstance(payload, dict):
            continue
        records.extend(_scenario_records(run_id, mode, payload))
        records.extend(_coordination_records(run_id, mode, payload))
        records.extend(_pedestrian_records(run_id, mode, payload))
        records.extend(_vehicle_class_records(run_id, mode, payload))
        records.extend(_emergency_priority_records(run_id, mode, payload))
        records.extend(_emergency_lifecycle_records(run_id, mode, payload))

    records.sort(key=_record_sort_key)
    categories = Counter(str(record.get("trigger_category") or "unknown") for record in records)
    decisions = Counter(str(record.get("decision") or "observe") for record in records)
    applied_count = sum(1 for record in records if bool(record.get("applied")))

    return {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "record_count": len(records),
        "applied_count": applied_count,
        "categories": dict(sorted(categories.items())),
        "decisions": dict(sorted(decisions.items())),
        "records": records,
        "note": (
            "Compact normalized evidence projection. Detailed mode-specific scenario, cooperation, pedestrian, "
            "vehicle-class and emergency histories remain preserved on each experiment mode for traceability."
        ),
        "prototype_only": True,
    }


def export_network_decision_evidence_csv(evidence: dict[str, Any]) -> str:
    records = evidence.get("records") if isinstance(evidence.get("records"), list) else []
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        [
            "evidence_id",
            "mode",
            "t_seconds",
            "trigger_category",
            "trigger_id",
            "intersection_id",
            "source_intersection_id",
            "destination_intersection_id",
            "link_id",
            "decision",
            "action",
            "applied",
            "phase_before",
            "phase_key_before",
            "timing_delta_seconds",
            "previous_duration_seconds",
            "effective_duration_seconds",
            "provenance",
            "reason",
            "explanation",
            "local_context",
            "neighbour_context",
            "pedestrian_context",
            "vehicle_class_context",
            "emergency_context",
            "source_ref",
        ]
    )
    for record in records:
        if not isinstance(record, dict):
            continue
        timing = record.get("timing") if isinstance(record.get("timing"), dict) else {}
        context = record.get("context") if isinstance(record.get("context"), dict) else {}
        writer.writerow(
            [
                record.get("evidence_id", ""),
                record.get("mode", ""),
                record.get("t_seconds", ""),
                record.get("trigger_category", ""),
                record.get("trigger_id", ""),
                record.get("intersection_id", ""),
                record.get("source_intersection_id", ""),
                record.get("destination_intersection_id", ""),
                record.get("link_id", ""),
                record.get("decision", ""),
                record.get("action", ""),
                record.get("applied", ""),
                record.get("phase_before", ""),
                record.get("phase_key_before", ""),
                timing.get("delta_seconds", ""),
                timing.get("previous_duration_seconds", ""),
                timing.get("effective_duration_seconds", ""),
                record.get("provenance", ""),
                record.get("reason", ""),
                record.get("explanation", ""),
                _compact_context(context.get("local")),
                _compact_context(context.get("neighbour")),
                _compact_context(context.get("pedestrian")),
                _compact_context(context.get("vehicle_class")),
                _compact_context(context.get("emergency")),
                record.get("source_ref", ""),
            ]
        )
    return output.getvalue()


def _scenario_records(run_id: str, mode: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    intersections = payload.get("intersections") if isinstance(payload.get("intersections"), dict) else {}
    for intersection_id, intersection in sorted(intersections.items(), key=lambda item: str(item[0])):
        if not isinstance(intersection, dict):
            continue
        events = intersection.get("scenario_evidence_events")
        if not isinstance(events, list):
            continue
        for index, event in enumerate(events):
            if not isinstance(event, dict):
                continue
            trigger_id = str(event.get("scenario_id") or event.get("rule_id") or f"scenario_{index}")
            applied = bool(event.get("applied", True))
            decision = "grant" if applied else "observe"
            action = str(event.get("action") or "scenario_active")
            reason = str(event.get("reason") or "ranked scenario evidence captured from the protected signal controller")
            observations = event.get("observations") if isinstance(event.get("observations"), dict) else {}
            local_context = dict(observations)
            if event.get("base_duration_seconds") is not None:
                local_context["base_duration_seconds"] = event.get("base_duration_seconds")
            records.append(
                _record(
                    run_id=run_id,
                    mode=mode,
                    category="scenario",
                    trigger_id=trigger_id,
                    source_ref=f"{mode}.intersections.{intersection_id}.scenario_evidence_events[{index}]",
                    t_seconds=event.get("t"),
                    intersection_id=str(intersection_id),
                    action=action,
                    decision=decision,
                    applied=applied,
                    reason=reason,
                    phase_before=event.get("phase"),
                    phase_key_before=event.get("phase_key"),
                    timing_delta_seconds=event.get("timing_delta_seconds", 0.0),
                    previous_duration_seconds=event.get("previous_duration_seconds"),
                    effective_duration_seconds=event.get("effective_duration_seconds"),
                    provenance=str(event.get("provenance") or "simulation_signal_controller"),
                    context={
                        "local": local_context,
                        "neighbour": {},
                        "pedestrian": _pedestrian_context_from_observations(observations),
                        "vehicle_class": _vehicle_class_context_from_observations(observations),
                        "emergency": {},
                    },
                    explanation=f"Scenario {trigger_id} {action}; {reason}",
                )
            )
    return records


def _coordination_records(run_id: str, mode: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    events = payload.get("coordination_events") if isinstance(payload.get("coordination_events"), list) else []
    records: list[dict[str, Any]] = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            continue
        trigger_id = str(event.get("coordination_id") or f"coordination_{index}")
        applied = bool(event.get("applied"))
        action = str(event.get("action") or "none")
        decision = "grant" if applied else ("deny" if action == "protect_pedestrian_service" else "defer")
        reason = str(event.get("reason") or "")
        records.append(
            _record(
                run_id=run_id,
                mode=mode,
                category="cooperation",
                trigger_id=trigger_id,
                source_ref=f"{mode}.coordination_events[{index}]",
                t_seconds=event.get("t"),
                intersection_id=event.get("destination_intersection_id"),
                source_intersection_id=event.get("source_intersection_id"),
                destination_intersection_id=event.get("destination_intersection_id"),
                link_id=event.get("link_id"),
                action=action,
                decision=decision,
                applied=applied,
                reason=reason,
                phase_before=event.get("destination_phase_before"),
                phase_key_before=event.get("destination_phase_key_before"),
                timing_delta_seconds=event.get("timing_delta_seconds", 0.0),
                provenance=str(event.get("provenance") or "synthetic_predicted_arrivals"),
                context={
                    "local": {},
                    "neighbour": {
                        "incoming_vehicle_count": event.get("incoming_vehicle_count"),
                        "earliest_arrival_eta_seconds": event.get("earliest_arrival_eta_seconds"),
                    },
                    "pedestrian": {"protected": action == "protect_pedestrian_service"},
                    "vehicle_class": {},
                    "emergency": {},
                },
                explanation=f"Neighbour cooperation {action}; {reason}",
            )
        )
    return records


def _pedestrian_records(run_id: str, mode: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    events = payload.get("pedestrian_awareness_events") if isinstance(payload.get("pedestrian_awareness_events"), list) else []
    records: list[dict[str, Any]] = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            continue
        trigger_id = str(event.get("pedestrian_awareness_id") or f"pedestrian_{index}")
        applied = bool(event.get("applied"))
        action = str(event.get("action") or "none")
        decision = "grant" if applied else "observe"
        reason = str(event.get("reason") or "")
        records.append(
            _record(
                run_id=run_id,
                mode=mode,
                category="pedestrian",
                trigger_id=trigger_id,
                source_ref=f"{mode}.pedestrian_awareness_events[{index}]",
                t_seconds=event.get("t"),
                intersection_id=event.get("intersection_id"),
                action=action,
                decision=decision,
                applied=applied,
                reason=reason,
                phase_before=event.get("phase_before"),
                phase_key_before=event.get("phase_key_before"),
                timing_delta_seconds=event.get("timing_delta_seconds", 0.0),
                provenance=str(event.get("provenance") or "synthetic_pedestrian_demand"),
                context={
                    "local": {},
                    "neighbour": {},
                    "pedestrian": {
                        "role": event.get("role"),
                        "waiting_count": event.get("waiting_count"),
                        "oldest_wait_seconds": event.get("oldest_wait_seconds"),
                        "crossing_count": event.get("crossing_count"),
                    },
                    "vehicle_class": {},
                    "emergency": {},
                },
                explanation=f"Pedestrian-aware guard {action}; {reason}",
            )
        )
    return records


def _vehicle_class_records(run_id: str, mode: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    events = payload.get("vehicle_class_priority_events") if isinstance(payload.get("vehicle_class_priority_events"), list) else []
    records: list[dict[str, Any]] = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            continue
        trigger_id = str(event.get("vehicle_class_priority_id") or f"vehicle_class_{index}")
        applied = bool(event.get("applied"))
        action = str(event.get("action") or "none")
        decision = "grant" if applied else ("deny" if action == "protect_pedestrian_service" else "defer")
        reason = str(event.get("reason") or "")
        records.append(
            _record(
                run_id=run_id,
                mode=mode,
                category="vehicle_class",
                trigger_id=trigger_id,
                source_ref=f"{mode}.vehicle_class_priority_events[{index}]",
                t_seconds=event.get("t"),
                intersection_id=event.get("intersection_id"),
                action=action,
                decision=decision,
                applied=applied,
                reason=reason,
                phase_before=event.get("phase_before"),
                phase_key_before=event.get("phase_key_before"),
                timing_delta_seconds=event.get("timing_delta_seconds", 0.0),
                provenance=str(event.get("provenance") or "synthetic_vehicle_class_demand"),
                context={
                    "local": {},
                    "neighbour": {},
                    "pedestrian": {"protected": action == "protect_pedestrian_service"},
                    "vehicle_class": {
                        "role": event.get("role"),
                        "class_name": event.get("class_name"),
                        "waiting_count": event.get("waiting_count"),
                        "oldest_wait_seconds": event.get("oldest_wait_seconds"),
                        "priority_weight": event.get("priority_weight"),
                        "weighted_waiting": event.get("weighted_waiting"),
                        "min_waiting": event.get("min_waiting"),
                    },
                    "emergency": {},
                },
                explanation=f"Vehicle-class-aware priority {action}; {reason}",
            )
        )
    return records


def _emergency_priority_records(run_id: str, mode: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    events = payload.get("emergency_priority_events") if isinstance(payload.get("emergency_priority_events"), list) else []
    records: list[dict[str, Any]] = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            continue
        trigger_id = str(event.get("emergency_priority_id") or f"emergency_priority_{index}")
        applied = bool(event.get("applied"))
        decision = str(event.get("decision") or ("grant" if applied else "defer"))
        action = str(event.get("action") or "none")
        reason = str(event.get("reason") or "")
        records.append(
            _record(
                run_id=run_id,
                mode=mode,
                category="emergency_priority",
                trigger_id=trigger_id,
                source_ref=f"{mode}.emergency_priority_events[{index}]",
                t_seconds=event.get("t"),
                intersection_id=event.get("intersection_id"),
                link_id=event.get("link_id"),
                action=action,
                decision=decision,
                applied=applied,
                reason=reason,
                phase_before=event.get("phase_before"),
                phase_key_before=event.get("phase_key_before"),
                timing_delta_seconds=event.get("timing_delta_seconds", 0.0),
                provenance=str(event.get("provenance") or "simulated_configured_emergency_event"),
                context={
                    "local": {},
                    "neighbour": {"eta_seconds": event.get("eta_seconds")},
                    "pedestrian": {"protected": decision == "deny" and "pedestrian" in reason.lower()},
                    "vehicle_class": {},
                    "emergency": {
                        "emergency_event_id": event.get("emergency_event_id"),
                        "vehicle_type": event.get("vehicle_type"),
                        "role": event.get("role"),
                        "eta_seconds": event.get("eta_seconds"),
                    },
                },
                explanation=f"Emergency priority {decision}: {action}; {reason}",
            )
        )
    return records


def _emergency_lifecycle_records(run_id: str, mode: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    events = payload.get("emergency_lifecycle_events") if isinstance(payload.get("emergency_lifecycle_events"), list) else []
    records: list[dict[str, Any]] = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            continue
        event_type = str(event.get("event_type") or "lifecycle")
        trigger_id = f"{event.get('emergency_event_id') or 'emergency'}:{event_type}:{index}"
        reason = _lifecycle_reason(event_type, event)
        records.append(
            _record(
                run_id=run_id,
                mode=mode,
                category="emergency_lifecycle",
                trigger_id=trigger_id,
                source_ref=f"{mode}.emergency_lifecycle_events[{index}]",
                t_seconds=event.get("t"),
                intersection_id=_lifecycle_intersection(event_type, event),
                source_intersection_id=event.get("source_intersection_id"),
                destination_intersection_id=event.get("destination_intersection_id"),
                link_id=event.get("link_id"),
                action=event_type,
                decision="observe",
                applied=False,
                reason=reason,
                provenance=str(event.get("provenance") or "simulated_configured_emergency_event"),
                context={
                    "local": {},
                    "neighbour": {},
                    "pedestrian": {},
                    "vehicle_class": {},
                    "emergency": {
                        "emergency_event_id": event.get("emergency_event_id"),
                        "vehicle_type": event.get("vehicle_type"),
                        "status": event.get("status"),
                        "event_type": event_type,
                        "approach": event.get("approach"),
                        "scheduled_destination_arrival_s": event.get("scheduled_destination_arrival_s"),
                        "recovery": event.get("recovery"),
                    },
                },
                explanation=f"Emergency lifecycle {event_type}; {reason}",
            )
        )
    return records


def _record(
    *,
    run_id: str,
    mode: str,
    category: str,
    trigger_id: str,
    source_ref: str,
    t_seconds: Any = None,
    intersection_id: Any = None,
    source_intersection_id: Any = None,
    destination_intersection_id: Any = None,
    link_id: Any = None,
    action: str,
    decision: str,
    applied: bool,
    reason: str,
    phase_before: Any = None,
    phase_key_before: Any = None,
    timing_delta_seconds: Any = 0.0,
    previous_duration_seconds: Any = None,
    effective_duration_seconds: Any = None,
    provenance: str,
    context: dict[str, Any],
    explanation: str,
) -> dict[str, Any]:
    safe_trigger = _id_fragment(trigger_id)
    safe_mode = _id_fragment(mode)
    safe_category = _id_fragment(category)
    safe_intersection = _id_fragment(intersection_id or destination_intersection_id or source_intersection_id or "network")
    return {
        "evidence_id": f"evidence_{safe_mode}_{safe_category}_{safe_intersection}_{safe_trigger}_{_id_fragment(source_ref.rsplit(chr(46), 1)[-1])}",
        "mode": mode,
        "t_seconds": _round_optional(t_seconds),
        "trigger_category": category,
        "trigger_id": trigger_id,
        "intersection_id": _string_optional(intersection_id),
        "source_intersection_id": _string_optional(source_intersection_id),
        "destination_intersection_id": _string_optional(destination_intersection_id),
        "link_id": _string_optional(link_id),
        "decision": decision,
        "action": action,
        "applied": bool(applied),
        "phase_before": _string_optional(phase_before),
        "phase_key_before": _string_optional(phase_key_before),
        "timing": {
            "delta_seconds": _round_optional(timing_delta_seconds) or 0.0,
            "previous_duration_seconds": _round_optional(previous_duration_seconds),
            "effective_duration_seconds": _round_optional(effective_duration_seconds),
        },
        "context": {
            "local": _dict_or_empty(context.get("local")),
            "neighbour": _dict_or_empty(context.get("neighbour")),
            "pedestrian": _dict_or_empty(context.get("pedestrian")),
            "vehicle_class": _dict_or_empty(context.get("vehicle_class")),
            "emergency": _dict_or_empty(context.get("emergency")),
        },
        "provenance": provenance,
        "reason": reason,
        "explanation": explanation,
        "source_ref": source_ref,
        "prototype_only": True,
    }


def _record_sort_key(record: dict[str, Any]) -> tuple[float, str, str, str]:
    t_value = record.get("t_seconds")
    t = float(t_value) if isinstance(t_value, (int, float)) else float("inf")
    return (t, str(record.get("mode") or ""), str(record.get("trigger_category") or ""), str(record.get("evidence_id") or ""))


def _pedestrian_context_from_observations(observations: dict[str, Any]) -> dict[str, Any]:
    return {
        "waiting_count": observations.get("pedestrians_waiting"),
        "crossing_count": observations.get("pedestrians_crossing"),
        "wait_seconds": observations.get("pedestrian_wait_seconds"),
    }


def _vehicle_class_context_from_observations(observations: dict[str, Any]) -> dict[str, Any]:
    zone_counts = observations.get("zone_class_counts")
    return {"zone_class_counts": zone_counts} if isinstance(zone_counts, dict) else {}


def _lifecycle_reason(event_type: str, event: dict[str, Any]) -> str:
    if event_type == "activated":
        return "configured simulated emergency event activated at the source intersection"
    if event_type == "source_departed":
        return "simulated emergency vehicle departed the source and entered the configured transfer link"
    if event_type == "destination_arrived":
        return "simulated emergency vehicle arrived at the downstream intersection"
    if event_type == "cleared":
        return str(event.get("recovery") or "simulated emergency vehicle cleared the downstream intersection")
    if event_type == "recovery":
        return str(event.get("recovery") or "emergency priority context removed and normal protected control resumed")
    return f"simulated emergency lifecycle event: {event_type}"


def _lifecycle_intersection(event_type: str, event: dict[str, Any]) -> str | None:
    if event_type in {"activated", "source_departed"}:
        return _string_optional(event.get("source_intersection_id"))
    if event_type in {"destination_arrived", "cleared", "recovery"}:
        return _string_optional(event.get("destination_intersection_id"))
    return None


def _compact_context(value: Any) -> str:
    if not isinstance(value, dict) or not value:
        return ""
    parts: list[str] = []
    for key, item in sorted(value.items(), key=lambda pair: str(pair[0])):
        if isinstance(item, dict):
            nested = ",".join(
                f"{sub_key}:{sub_value}"
                for sub_key, sub_value in sorted(item.items(), key=lambda pair: str(pair[0]))
            )
            parts.append(f"{key}={{{nested}}}")
        else:
            parts.append(f"{key}={item}")
    return ";".join(parts)


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _round_optional(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return round(float(value), 3)
    except (TypeError, ValueError):
        return None


def _string_optional(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def _id_fragment(value: Any) -> str:
    text = str(value or "unknown")
    return "".join(character if character.isalnum() or character in {"_", "-", "."} else "_" for character in text)[:160]
