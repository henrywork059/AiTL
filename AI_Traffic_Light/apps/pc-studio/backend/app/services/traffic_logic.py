from __future__ import annotations

from time import time
from typing import Any

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.core.logging_config import get_logger
from app.services.camera_frames import camera_frame_service
from app.services.inference import inference_service
from app.services.object_tracking import object_tracking_service
from app.services.runtime_settings import runtime_settings_service
from app.services.zones import REFERENCE_HEIGHT, REFERENCE_WIDTH, zone_service

logger = get_logger(__name__)

VALID_PHASES = {
    "vehicle_green",
    "vehicle_yellow",
    "pedestrian_green",
    "pedestrian_flashing",
    "all_red",
}
VEHICLE_CLASSES = {"car", "bus", "truck", "motorcycle", "bicycle"}


def validate_traffic_state(state: dict) -> None:
    """Validate a traffic simulation state dictionary before returning it to the API."""
    phase = state.get("phase")
    if phase not in VALID_PHASES:
        raise AppError(
            ErrorCode.TRAFFIC_STATE_INVALID,
            details={"phase": phase, "valid_phases": sorted(VALID_PHASES)},
        )


def point_in_polygon(point: tuple[float, float], polygon: list[list[int]]) -> bool:
    """Return whether a point is inside a polygon using ray casting."""
    x, y = point
    inside = False
    count = len(polygon)
    if count < 3:
        return False
    previous_x, previous_y = polygon[-1]
    for current_x, current_y in polygon:
        if (current_y > y) != (previous_y > y):
            denominator = previous_y - current_y
            if denominator != 0:
                intersection_x = (previous_x - current_x) * (y - current_y) / denominator + current_x
                if x < intersection_x:
                    inside = not inside
        previous_x, previous_y = current_x, current_y
    return inside


def _scaled_center(detection: dict[str, Any], width: int, height: int) -> tuple[float, float]:
    x1, y1, x2, y2 = detection["box_xyxy"]
    centre_x = (float(x1) + float(x2)) / 2
    centre_y = (float(y1) + float(y2)) / 2
    scale_x = REFERENCE_WIDTH / max(1, width)
    scale_y = REFERENCE_HEIGHT / max(1, height)
    return centre_x * scale_x, centre_y * scale_y


def _empty_region_counts(zones: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    return {
        zone["id"]: {"pedestrians": 0, "vehicles": 0, "total": 0}
        for zone in zones
        if zone.get("type") not in {"ignore", "counting_line"}
    }


def evaluate_traffic_state(
    detection_frame: dict[str, Any] | None,
    zones: list[dict[str, Any]],
    *,
    source: str = "live_zone_evaluation",
) -> dict[str, Any]:
    """Convert one detection frame and persisted zones into supervised prototype traffic metrics.

    Counts here remain per-frame occupancy samples. V022 separately derives unique
    passage/entry/exit events from cross-frame track IDs; occupancy is intentionally
    preserved so the two metrics are never conflated.
    """
    evaluated_at_ms = int(time() * 1000)
    region_counts = _empty_region_counts(zones)
    zone_counts = {zone["id"]: 0 for zone in zones if zone.get("type") != "counting_line"}

    if detection_frame is None:
        state = {
            "phase": "vehicle_green",
            "pedestrians_waiting": 0,
            "pedestrians_crossing": 0,
            "vehicles_waiting": 0,
            "pedestrians_total": 0,
            "vehicles_total": 0,
            "decision": "await_live_detections",
            "decision_reason": "No trained-model detection frame is available yet. Load a model and provide a camera or simulation frame.",
            "extension_seconds": 0,
            "data_source": source,
            "evaluated_at_ms": evaluated_at_ms,
            "source_timestamp_ms": None,
            "evaluated_frame_number": None,
            "zone_counts": zone_counts,
            "region_counts": region_counts,
            "tracking": object_tracking_service.status(),
            "prototype_only": True,
        }
        validate_traffic_state(state)
        return state

    width = int(detection_frame.get("image_width") or REFERENCE_WIDTH)
    height = int(detection_frame.get("image_height") or REFERENCE_HEIGHT)
    pedestrian_waiting = 0
    pedestrian_crossing = 0
    vehicles_waiting = 0
    pedestrians_total = 0
    vehicles_total = 0
    ignore_zones = [zone for zone in zones if zone.get("type") == "ignore"]
    counting_zones = [zone for zone in zones if zone.get("type") not in {"ignore", "counting_line"}]
    crossing_zones = [zone for zone in zones if zone.get("type") == "crossing"]
    waiting_zones = [zone for zone in zones if zone.get("type") == "pedestrian_waiting"]
    queue_zones = [zone for zone in zones if zone.get("type") == "vehicle_queue"]
    analytics_zones = [zone for zone in zones if zone.get("type") == "counting_region"]

    for detection in detection_frame.get("detections", []):
        try:
            centre = _scaled_center(detection, width, height)
        except (KeyError, TypeError, ValueError):
            continue
        if any(point_in_polygon(centre, zone["polygon"]) for zone in ignore_zones):
            continue

        class_name = str(detection.get("class_name", ""))
        group: str | None = None
        if class_name == "person":
            pedestrians_total += 1
            group = "pedestrians"
        elif class_name in VEHICLE_CLASSES:
            vehicles_total += 1
            group = "vehicles"

        if group is None:
            continue

        for zone in counting_zones:
            if point_in_polygon(centre, zone["polygon"]):
                region = region_counts[zone["id"]]
                region[group] += 1
                region["total"] += 1

        if class_name == "person":
            crossing_matches = [zone for zone in crossing_zones if point_in_polygon(centre, zone["polygon"])]
            if crossing_matches:
                pedestrian_crossing += 1
                for zone in crossing_matches:
                    zone_counts[zone["id"]] += 1
            else:
                waiting_matches = [zone for zone in waiting_zones if point_in_polygon(centre, zone["polygon"])]
                if waiting_matches:
                    pedestrian_waiting += 1
                    for zone in waiting_matches:
                        zone_counts[zone["id"]] += 1
        else:
            queue_matches = [zone for zone in queue_zones if point_in_polygon(centre, zone["polygon"])]
            if queue_matches:
                vehicles_waiting += 1
                for zone in queue_matches:
                    zone_counts[zone["id"]] += 1

        for zone in analytics_zones:
            if point_in_polygon(centre, zone["polygon"]):
                zone_counts[zone["id"]] += 1

    if pedestrian_crossing > 0:
        phase = "pedestrian_green"
        decision = "hold_pedestrian_phase"
        extension_seconds = min(10, 2 + pedestrian_crossing * 2)
        reason = f"{pedestrian_crossing} pedestrian(s) are inside the configured crossing zone."
    elif pedestrian_waiting > 0:
        phase = "vehicle_yellow"
        decision = "prepare_pedestrian_green"
        extension_seconds = 0
        reason = f"{pedestrian_waiting} pedestrian(s) are waiting and the crossing zone is clear."
    elif vehicles_waiting >= 4:
        phase = "vehicle_green"
        decision = "extend_vehicle_green"
        extension_seconds = min(10, vehicles_waiting * 2)
        reason = f"The crossing is clear and {vehicles_waiting} queued vehicle(s) are inside vehicle queue zones."
    else:
        phase = "vehicle_green"
        decision = "hold_vehicle_green"
        extension_seconds = 0
        reason = "No pedestrian demand is currently detected in configured waiting or crossing zones."

    state = {
        "phase": phase,
        "pedestrians_waiting": pedestrian_waiting,
        "pedestrians_crossing": pedestrian_crossing,
        "vehicles_waiting": vehicles_waiting,
        "pedestrians_total": pedestrians_total,
        "vehicles_total": vehicles_total,
        "decision": decision,
        "decision_reason": reason,
        "extension_seconds": extension_seconds,
        "data_source": source,
        "evaluated_at_ms": evaluated_at_ms,
        "source_timestamp_ms": detection_frame.get("timestamp_ms"),
        "evaluated_frame_number": detection_frame.get("source_frame_number"),
        "zone_counts": zone_counts,
        "region_counts": region_counts,
        "tracking": detection_frame.get("tracking") if isinstance(detection_frame.get("tracking"), dict) else object_tracking_service.status(),
        "prototype_only": True,
    }
    validate_traffic_state(state)
    return state


def _apply_active_simulation_signal(state: dict[str, Any]) -> dict[str, Any]:
    """Align displayed traffic phase with the signal that synthetic agents actually obey.

    The detection-driven result is retained as recommendation metadata. This keeps
    simulation motion deterministic and non-circular: rendering never depends on
    inference, while the traffic layer can still explain what detections recommend.
    """
    if not camera_frame_service.simulation_enabled:
        return state

    signal = camera_frame_service.simulation_signal_state()
    recommendation_phase = state["phase"]
    recommendation_decision = state["decision"]
    recommendation_reason = state["decision_reason"]
    state = dict(state)
    state.update(
        {
            "recommended_phase": recommendation_phase,
            "recommended_decision": recommendation_decision,
            "recommended_decision_reason": recommendation_reason,
            "phase": signal["phase"],
            "decision": "follow_simulation_signal",
            "decision_reason": (
                f"Synthetic vehicles and pedestrians obey the active {signal['phase'].replace('_', ' ')} "
                f"signal ({signal['seconds_remaining']:.1f}s remaining). Detection-based recommendation: "
                f"{recommendation_phase.replace('_', ' ')} — {recommendation_reason}"
            ),
            "extension_seconds": int(round(float(signal["seconds_remaining"]))),
            "data_source": f"simulation_signal+{state.get('data_source', 'traffic_evaluation')}",
        }
    )
    validate_traffic_state(state)
    return state


def get_live_traffic_state() -> dict[str, Any]:
    """Run or reuse current inference and evaluate it against persisted zones for simulation-only logic."""
    zones = zone_service.zones()
    frame = camera_frame_service.latest_frame()
    if frame is None:
        object_tracking_service.reset_active()
        return _apply_active_simulation_signal(evaluate_traffic_state(None, zones, source="no_camera_frame"))
    status = inference_service.status()
    if not status.get("model_loaded"):
        object_tracking_service.reset_active()
        return _apply_active_simulation_signal(evaluate_traffic_state(None, zones, source="model_not_loaded"))
    try:
        settings = runtime_settings_service.get()
        detection_frame = inference_service.detect_frame(
            frame,
            confidence_threshold=float(settings["default_confidence"]),
        )
        detection_frame = object_tracking_service.update(detection_frame, zones)
    except AppError as exc:
        if exc.code in {
            ErrorCode.MODEL_NOT_LOADED,
            ErrorCode.INFERENCE_SOURCE_MISSING,
            ErrorCode.INFERENCE_FAILED,
            ErrorCode.INFERENCE_RESULT_INVALID,
        }:
            logger.warning(
                "Traffic simulation could not obtain live detections",
                extra={"error_code": exc.code.value},
            )
            return _apply_active_simulation_signal(
                evaluate_traffic_state(None, zones, source=f"inference_unavailable:{exc.code.value}")
            )
        raise
    return _apply_active_simulation_signal(evaluate_traffic_state(detection_frame, zones))


# Backward-compatible name used by older smoke code and offline fixtures.
def get_mock_traffic_state() -> dict[str, Any]:
    return get_live_traffic_state()
