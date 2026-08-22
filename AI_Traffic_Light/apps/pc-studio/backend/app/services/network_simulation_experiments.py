from __future__ import annotations

from collections import deque
from copy import deepcopy
from dataclasses import dataclass
import csv
import hashlib
from io import StringIO
import json
import math
from pathlib import Path
import random
import re
import tempfile
import time
from typing import Any, Callable
import uuid

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.core.json_store import read_json, write_json_atomic
from app.core.logging_config import get_logger
from app.services.decision_evidence import build_network_decision_evidence, export_network_decision_evidence_csv
from app.services.intersection_network import intersection_network_service
from app.services.signal_rules import PHASE_SEQUENCE, SignalRulesService, signal_rules_service
from app.services.zones import zone_service

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_STORAGE_ROOT = PROJECT_ROOT / "outputs" / "simulation_experiments"
RUN_ID_PATTERN = re.compile(r"^netexp_[A-Za-z0-9._-]{1,88}$")
DENSITIES = {"light", "normal", "busy"}
STEP_SECONDS = 0.5
MAX_STORED_RUNS = 100

# Exogenous demand remains intentionally simple and deterministic. The same
# generated arrival plan is supplied to every network comparison mode, including
# class-aware and emergency variants. Policy-dependent upstream service can still change the
# timing of transferred arrivals at the downstream intersection; that is an
# experiment outcome, not a changed input.
VEHICLE_RATES_PER_MINUTE = {
    "light": (5.0, 2.5),
    "normal": (10.0, 5.0),
    "busy": (18.0, 9.0),
}
PEDESTRIAN_RATES_PER_MINUTE = {
    "light": (2.0, 2.0),
    "normal": (5.0, 4.0),
    "busy": (9.0, 7.0),
}
VEHICLE_SERVICE_PER_SECOND = 0.9
PEDESTRIAN_SERVICE_PER_SECOND = 1.6
COOPERATION_SERVICE_BUFFER_SECONDS = 2.0
PEDESTRIAN_AWARE_MODES = {
    "pedestrian_aware_cooperative",
    "class_aware_cooperative",
    "emergency_baseline_cooperative",
    "emergency_priority_cooperative",
}
COOPERATIVE_MODES = {
    "cooperative",
    "pedestrian_aware_cooperative",
    "class_aware_cooperative",
    "emergency_baseline_cooperative",
    "emergency_priority_cooperative",
}
CLASS_AWARE_MODES = {"class_aware_cooperative"}
EMERGENCY_EVENT_MODES = {"emergency_baseline_cooperative", "emergency_priority_cooperative"}
EMERGENCY_PRIORITY_MODES = {"emergency_priority_cooperative"}
NETWORK_EXPERIMENT_MODES = (
    "fixed",
    "adaptive",
    "cooperative",
    "pedestrian_aware_cooperative",
    "class_aware_cooperative",
    "emergency_baseline_cooperative",
    "emergency_priority_cooperative",
)
REGULAR_VEHICLE_CLASSES = ("car", "bus", "truck", "motorcycle", "bicycle", "other")
SPECIAL_VEHICLE_CLASSES = ("emergency",)
VEHICLE_CLASS_PROFILES = {
    "legacy": {"car": 0.84, "bus": 0.16},
    "mixed_urban": {
        "car": 0.62,
        "bus": 0.12,
        "truck": 0.10,
        "motorcycle": 0.08,
        "bicycle": 0.06,
        "other": 0.02,
    },
    "freight_heavy": {
        "car": 0.48,
        "bus": 0.10,
        "truck": 0.27,
        "motorcycle": 0.07,
        "bicycle": 0.04,
        "other": 0.04,
    },
}
EMERGENCY_SERVICE_BUFFER_SECONDS = 2.0
EMERGENCY_VEHICLE_TYPES = {"ambulance", "fire_engine", "police"}


@dataclass
class _VehicleArrival:
    at_s: float
    vehicle_id: str
    class_name: str
    continues_to_destination: bool


@dataclass
class _QueuedVehicle:
    vehicle_id: str
    class_name: str
    queued_at_s: float
    network_started_at_s: float
    continues_to_destination: bool = False
    origin: str = "external"
    source_departed_at_s: float | None = None


@dataclass
class _Transfer:
    arrive_at_s: float
    vehicle: _QueuedVehicle


@dataclass
class _PedestrianArrival:
    at_s: float
    pedestrian_id: str


class _BenchmarkSignalRulesService(SignalRulesService):
    """Signal-rules adapter using simulation time for stale/memory evaluation."""

    def __init__(self, *, config_path: Path, history_path: Path) -> None:
        self._benchmark_clock_s = 0.0
        super().__init__(config_path=config_path, history_path=history_path)

    def set_benchmark_clock(self, clock_s: float) -> None:
        self._benchmark_clock_s = max(0.0, float(clock_s))

    def observe(self, observation: dict[str, Any]) -> None:
        now = self._benchmark_clock_s
        with self._lock:
            self._last_observation = {
                "pedestrians_waiting": max(0, int(observation.get("pedestrians_waiting", 0) or 0)),
                "pedestrians_crossing": max(0, int(observation.get("pedestrians_crossing", 0) or 0)),
                "vehicles_waiting": max(0, int(observation.get("vehicles_waiting", 0) or 0)),
                "zone_class_counts": deepcopy(observation.get("zone_class_counts", {}))
                if isinstance(observation.get("zone_class_counts", {}), dict)
                else {},
                "source_frame_number": observation.get("source_frame_number"),
                "source_timestamp_ms": observation.get("source_timestamp_ms"),
                "data_source": observation.get("data_source"),
            }
            self._last_observation_monotonic = now
            self._update_memory_locked(self._pedestrian_wait, self._last_observation["pedestrians_waiting"], now)
            self._update_memory_locked(self._vehicle_wait, self._last_observation["vehicles_waiting"], now)
            self._update_memory_locked(self._crossing, self._last_observation["pedestrians_crossing"], now)

    def _observation_values_locked(self, profile: dict[str, Any]) -> tuple[dict[str, Any], bool, str | None]:
        now = self._benchmark_clock_s
        fresh = self._last_observation_monotonic is not None and now - self._last_observation_monotonic <= float(
            profile["stale_data_seconds"]
        )
        memory_window = float(profile["demand_memory_seconds"])

        def memory_count(memory: Any, current: int) -> int:
            if current > 0:
                return current
            if memory.last_seen_monotonic is not None and now - memory.last_seen_monotonic <= memory_window:
                return max(1, memory.last_count)
            return 0

        base = dict(self._last_observation)
        base.setdefault("pedestrians_waiting", 0)
        base.setdefault("pedestrians_crossing", 0)
        base.setdefault("vehicles_waiting", 0)
        base.setdefault("zone_class_counts", {})
        base["pedestrians_waiting"] = memory_count(self._pedestrian_wait, int(base["pedestrians_waiting"]))
        base["pedestrians_crossing"] = memory_count(self._crossing, int(base["pedestrians_crossing"]))
        base["vehicles_waiting"] = memory_count(self._vehicle_wait, int(base["vehicles_waiting"]))
        base["pedestrian_wait_seconds"] = self._memory_age(self._pedestrian_wait, now, memory_window)
        base["vehicle_wait_seconds"] = self._memory_age(self._vehicle_wait, now, memory_window)
        base["crossing_dwell_seconds"] = self._memory_age(self._crossing, now, memory_window)
        base["mobility_assistance"] = False
        base["incident_person_fallen"] = False
        config = self._load_config_locked()
        if config["mode"] == "test":
            base.update(self._test_inputs)
            fresh = True
        fallback_reason = None if fresh else "Adaptive observations are stale or unavailable; normal configured timing is active."
        return base, fresh, fallback_reason

    def apply_network_coordination(
        self,
        *,
        clock_s: float,
        incoming_vehicle_count: int,
        earliest_arrival_eta_seconds: float | None,
        lookahead_seconds: float,
        max_extension_seconds: float,
        local_pedestrians_waiting: int,
        local_pedestrians_crossing: int = 0,
        link_id: str,
        source_intersection_id: str,
        destination_intersection_id: str,
    ) -> dict[str, Any]:
        """Apply one bounded simulation-only neighbour timing advisory.

        The coordinator never changes phase order. During vehicle green it may
        extend the current phase only inside the saved phase/cycle caps. During
        non-vehicle phases it may request earlier protected progression by
        reducing only the current phase toward its configured minimum. Active
        pedestrian demand prevents shortening pedestrian WALK/CLEAR phases.
        """

        incoming = max(0, int(incoming_vehicle_count))
        eta = None if earliest_arrival_eta_seconds is None else max(0.0, float(earliest_arrival_eta_seconds))
        result = {
            "applied": False,
            "action": "none",
            "reason": "no incoming vehicles inside the cooperation lookahead",
            "incoming_vehicle_count": incoming,
            "earliest_arrival_eta_seconds": round(eta, 1) if eta is not None else None,
            "timing_delta_seconds": 0.0,
        }
        if incoming <= 0 or eta is None or eta > float(lookahead_seconds) + 1e-9:
            return result

        with self._lock:
            config = self._load_config_locked()
            profile = self._active_profile_locked(config)
            if self._incident_hold:
                result["reason"] = "incident hold blocks network timing coordination"
                return result

            phase_key, _phase = PHASE_SEQUENCE[self._phase_index]
            elapsed = max(0.0, float(clock_s) - self._phase_started_clock)
            phase_limits = profile["phases"][phase_key]
            previous = float(self._phase_duration_seconds)
            changed = False

            if phase_key == "vehicle_green":
                target_duration = elapsed + eta + COOPERATION_SERVICE_BUFFER_SECONDS
                phase_cap = min(float(phase_limits["max_seconds"]), self._cycle_phase_cap_locked(profile, phase_key))
                cooperation_cap = min(
                    phase_cap,
                    float(self._phase_base_seconds) + max(0.0, float(max_extension_seconds)),
                )
                bounded_extension_target = min(cooperation_cap, target_duration)
                self._phase_duration_seconds = max(previous, bounded_extension_target)
                changed = self._phase_duration_seconds > previous + 0.05
                result["action"] = "extend_vehicle_green" if changed else "vehicle_green_already_sufficient"
                result["reason"] = (
                    "extended downstream vehicle green for predicted upstream arrivals"
                    if changed
                    else "current downstream vehicle green already covers the predicted arrival window within configured bounds"
                )
            else:
                pedestrian_phase = phase_key in {"pedestrian_green", "pedestrian_flashing"}
                if pedestrian_phase and (int(local_pedestrians_waiting) > 0 or int(local_pedestrians_crossing) > 0):
                    result["action"] = "protect_pedestrian_service"
                    result["reason"] = "pedestrian waiting/crossing demand is active, so cooperation does not shorten the protected pedestrian phase"
                else:
                    minimum = float(phase_limits["min_seconds"])
                    requested_duration = max(minimum, elapsed + 0.2)
                    requested_duration = min(previous, requested_duration)
                    self._phase_duration_seconds = requested_duration
                    self._pending_request = "vehicle"
                    changed = self._phase_duration_seconds < previous - 0.05
                    result["action"] = "request_protected_vehicle_progression" if changed else "vehicle_progression_pending"
                    result["reason"] = (
                        "shortened only the current protected phase toward its configured minimum for predicted upstream arrivals"
                        if changed
                        else "vehicle service is requested, but the current phase cannot be shortened further within protected bounds"
                    )

            delta = float(self._phase_duration_seconds) - previous
            result["applied"] = changed
            result["timing_delta_seconds"] = round(delta, 1)
            result["phase_key"] = phase_key
            result["previous_duration_seconds"] = round(previous, 1)
            result["effective_duration_seconds"] = round(float(self._phase_duration_seconds), 1)
            if changed:
                self._record_event_locked(
                    "network_coordination_applied",
                    {
                        "link_id": link_id,
                        "source_intersection_id": source_intersection_id,
                        "destination_intersection_id": destination_intersection_id,
                        "action": result["action"],
                        "phase_key": phase_key,
                        "incoming_vehicle_count": incoming,
                        "earliest_arrival_eta_seconds": result["earliest_arrival_eta_seconds"],
                        "previous_duration_seconds": result["previous_duration_seconds"],
                        "effective_duration_seconds": result["effective_duration_seconds"],
                        "simulation_clock_seconds": round(float(clock_s), 1),
                    },
                )
            return result


    def apply_pedestrian_service_guard(
        self,
        *,
        clock_s: float,
        waiting_count: int,
        oldest_wait_seconds: float,
        crossing_count: int,
        max_wait_seconds: float,
        clearance_reserve_seconds: float,
        intersection_id: str,
    ) -> dict[str, Any]:
        """Apply bounded local pedestrian service/clearance protection.

        This simulation-only guard never changes phase order. Starved waiting
        demand may request earlier protected progression toward pedestrian
        service by shortening only the current phase toward its configured
        minimum. Active simulated crossings may reserve more of the current
        pedestrian WALK/CLEAR phase, still within saved phase/cycle maxima.
        """

        waiting = max(0, int(waiting_count))
        crossing = max(0, int(crossing_count))
        oldest = max(0.0, float(oldest_wait_seconds))
        result = {
            "applied": False,
            "action": "none",
            "reason": "no pedestrian service guard action required",
            "waiting_count": waiting,
            "crossing_count": crossing,
            "oldest_wait_seconds": round(oldest, 1),
            "timing_delta_seconds": 0.0,
        }
        if waiting <= 0 and crossing <= 0:
            return result

        with self._lock:
            config = self._load_config_locked()
            profile = self._active_profile_locked(config)
            if self._incident_hold:
                result["reason"] = "incident hold blocks pedestrian timing adjustment"
                return result

            phase_key, _phase = PHASE_SEQUENCE[self._phase_index]
            elapsed = max(0.0, float(clock_s) - self._phase_started_clock)
            phase_limits = profile["phases"][phase_key]
            previous = float(self._phase_duration_seconds)
            changed = False

            if crossing > 0 and phase_key in {"pedestrian_green", "pedestrian_flashing"}:
                phase_cap = min(float(phase_limits["max_seconds"]), self._cycle_phase_cap_locked(profile, phase_key))
                reserve_target = elapsed + max(0.0, float(clearance_reserve_seconds))
                self._phase_duration_seconds = max(previous, min(phase_cap, reserve_target))
                changed = self._phase_duration_seconds > previous + 0.05
                result["action"] = "protect_crossing_clearance" if changed else "crossing_clearance_already_protected"
                result["reason"] = (
                    "extended the active simulated pedestrian phase to preserve crossing-clearance reserve within configured bounds"
                    if changed
                    else "the active pedestrian phase already has sufficient bounded crossing-clearance reserve"
                )
            elif waiting > 0 and oldest + 1e-9 >= float(max_wait_seconds):
                self._pending_request = "pedestrian"
                if phase_key in {"pedestrian_green", "pedestrian_flashing"}:
                    result["action"] = "pedestrian_service_active"
                    result["reason"] = "pedestrian service is already active for a request at or above the maximum-wait threshold"
                elif phase_key in {"vehicle_green", "vehicle_yellow", "all_red_to_pedestrian"}:
                    minimum = float(phase_limits["min_seconds"])
                    requested_duration = max(minimum, elapsed + 0.2)
                    self._phase_duration_seconds = min(previous, requested_duration)
                    changed = self._phase_duration_seconds < previous - 0.05
                    result["action"] = "request_pedestrian_service" if changed else "pedestrian_service_pending"
                    result["reason"] = (
                        "shortened only the current protected phase toward its configured minimum because pedestrian wait reached the threshold"
                        if changed
                        else "pedestrian service is requested, but the current phase cannot be shortened further within protected bounds"
                    )
                else:
                    result["action"] = "pedestrian_request_queued"
                    result["reason"] = "pedestrian service request is retained until the protected sequence can progress toward pedestrian service"
            else:
                result["action"] = "waiting_below_threshold"
                result["reason"] = "pedestrian demand is tracked, but the oldest wait remains below the configured service threshold"

            delta = float(self._phase_duration_seconds) - previous
            result["applied"] = changed
            result["timing_delta_seconds"] = round(delta, 1)
            result["phase_key"] = phase_key
            result["previous_duration_seconds"] = round(previous, 1)
            result["effective_duration_seconds"] = round(float(self._phase_duration_seconds), 1)
            if changed:
                self._record_event_locked(
                    "pedestrian_service_guard_applied",
                    {
                        "intersection_id": intersection_id,
                        "action": result["action"],
                        "phase_key": phase_key,
                        "waiting_count": waiting,
                        "crossing_count": crossing,
                        "oldest_wait_seconds": result["oldest_wait_seconds"],
                        "max_wait_seconds": float(max_wait_seconds),
                        "previous_duration_seconds": result["previous_duration_seconds"],
                        "effective_duration_seconds": result["effective_duration_seconds"],
                        "simulation_clock_seconds": round(float(clock_s), 1),
                    },
                )
            return result


    def apply_vehicle_class_priority(
        self,
        *,
        clock_s: float,
        class_name: str,
        waiting_count: int,
        oldest_wait_seconds: float,
        priority_weight: float,
        max_extension_seconds: float,
        local_pedestrians_waiting: int,
        local_pedestrians_crossing: int,
        intersection_id: str,
    ) -> dict[str, Any]:
        """Apply one bounded simulation-only regular vehicle-class advisory.

        A configured class weight above 1.0 can reserve bounded vehicle service.
        The method never changes phase order, never shortens active pedestrian
        WALK/CLEAR with local demand, and has no effect for neutral weights.
        """

        normalized_class = _normalize_vehicle_class(class_name)
        waiting = max(0, int(waiting_count))
        oldest = max(0.0, float(oldest_wait_seconds))
        weight = max(0.0, float(priority_weight))
        result = {
            "applied": False,
            "action": "none",
            "reason": "no configured class-aware timing action required",
            "class_name": normalized_class,
            "waiting_count": waiting,
            "oldest_wait_seconds": round(oldest, 1),
            "priority_weight": round(weight, 2),
            "weighted_waiting": round(waiting * weight, 2),
            "timing_delta_seconds": 0.0,
        }
        if waiting <= 0:
            result["reason"] = "configured priority class is not waiting"
            return result
        if weight <= 1.0 + 1e-9:
            result["action"] = "neutral_class_weight"
            result["reason"] = "class priority weight is neutral, so timing remains unchanged"
            return result

        with self._lock:
            config = self._load_config_locked()
            profile = self._active_profile_locked(config)
            if self._incident_hold:
                result["reason"] = "incident hold blocks class-aware timing adjustment"
                return result

            phase_key, _phase = PHASE_SEQUENCE[self._phase_index]
            elapsed = max(0.0, float(clock_s) - self._phase_started_clock)
            phase_limits = profile["phases"][phase_key]
            previous = float(self._phase_duration_seconds)
            changed = False
            pedestrian_phase = phase_key in {"pedestrian_green", "pedestrian_flashing"}
            if pedestrian_phase and (int(local_pedestrians_waiting) > 0 or int(local_pedestrians_crossing) > 0):
                result["action"] = "protect_pedestrian_service"
                result["reason"] = "class-aware vehicle priority cannot shorten active pedestrian WALK/CLEAR demand"
            elif phase_key == "vehicle_green":
                requested_extension = min(
                    max(0.0, float(max_extension_seconds)),
                    max(0.5, (weight - 1.0) * min(waiting, 4) * 1.5),
                )
                phase_cap = min(float(phase_limits["max_seconds"]), self._cycle_phase_cap_locked(profile, phase_key))
                class_cap = min(phase_cap, float(self._phase_base_seconds) + max(0.0, float(max_extension_seconds)))
                self._phase_duration_seconds = max(previous, min(class_cap, previous + requested_extension))
                changed = self._phase_duration_seconds > previous + 0.05
                result["action"] = "extend_vehicle_green_for_class" if changed else "class_vehicle_green_already_bounded"
                result["reason"] = (
                    f"extended bounded vehicle green for configured {normalized_class} demand"
                    if changed
                    else "vehicle green cannot be extended further within configured class/phase/cycle bounds"
                )
            else:
                minimum = float(phase_limits["min_seconds"])
                requested_duration = max(minimum, elapsed + 0.2)
                self._phase_duration_seconds = min(previous, requested_duration)
                self._pending_request = "vehicle"
                changed = self._phase_duration_seconds < previous - 0.05
                result["action"] = "request_protected_vehicle_service_for_class" if changed else "class_vehicle_service_pending"
                result["reason"] = (
                    f"shortened only the current protected phase toward its minimum for configured {normalized_class} demand"
                    if changed
                    else "vehicle service is requested, but the current phase cannot be shortened further within protected bounds"
                )

            delta = float(self._phase_duration_seconds) - previous
            result["applied"] = changed
            result["timing_delta_seconds"] = round(delta, 1)
            result["phase_key"] = phase_key
            result["previous_duration_seconds"] = round(previous, 1)
            result["effective_duration_seconds"] = round(float(self._phase_duration_seconds), 1)
            if changed:
                self._record_event_locked(
                    "vehicle_class_priority_applied",
                    {
                        "intersection_id": intersection_id,
                        "class_name": normalized_class,
                        "waiting_count": waiting,
                        "oldest_wait_seconds": round(oldest, 1),
                        "priority_weight": round(weight, 2),
                        "weighted_waiting": round(waiting * weight, 2),
                        "action": result["action"],
                        "phase_key": phase_key,
                        "previous_duration_seconds": result["previous_duration_seconds"],
                        "effective_duration_seconds": result["effective_duration_seconds"],
                        "simulation_clock_seconds": round(float(clock_s), 1),
                        "provenance": "synthetic_vehicle_class_demand",
                    },
                )
            return result


    def apply_emergency_priority(
        self,
        *,
        clock_s: float,
        emergency_active: bool,
        emergency_event_id: str,
        vehicle_type: str,
        role: str,
        eta_seconds: float | None,
        lookahead_seconds: float,
        max_extension_seconds: float,
        local_pedestrians_waiting: int,
        local_pedestrians_crossing: int,
        intersection_id: str,
        link_id: str,
    ) -> dict[str, Any]:
        """Apply one bounded simulation-only emergency priority request.

        Emergency priority never skips the protected phase sequence. Vehicle
        green may be extended inside saved phase/cycle caps. Other phases may
        progress only toward their configured minimum. An active simulated
        pedestrian crossing is a hard local guard: priority is denied until the
        crossing can clear through the normal protected sequence.
        """

        eta = None if eta_seconds is None else max(0.0, float(eta_seconds))
        result: dict[str, Any] = {
            "applied": False,
            "decision": "defer",
            "action": "none",
            "reason": "emergency priority is not active at this intersection",
            "timing_delta_seconds": 0.0,
            "eta_seconds": round(eta, 1) if eta is not None else None,
        }
        if not emergency_active:
            return result
        if eta is not None and eta > float(lookahead_seconds) + 1e-9:
            result["reason"] = "emergency vehicle is outside the configured priority lookahead"
            return result

        with self._lock:
            config = self._load_config_locked()
            profile = self._active_profile_locked(config)
            if self._incident_hold:
                result.update(
                    {
                        "decision": "deny",
                        "action": "deny_incident_hold",
                        "reason": "existing incident hold blocks emergency timing priority",
                    }
                )
                return result

            phase_key, _phase = PHASE_SEQUENCE[self._phase_index]
            elapsed = max(0.0, float(clock_s) - self._phase_started_clock)
            phase_limits = profile["phases"][phase_key]
            previous = float(self._phase_duration_seconds)
            changed = False

            if phase_key == "vehicle_green":
                phase_cap = min(float(phase_limits["max_seconds"]), self._cycle_phase_cap_locked(profile, phase_key))
                emergency_cap = min(
                    phase_cap,
                    float(self._phase_base_seconds) + max(0.0, float(max_extension_seconds)),
                )
                target_duration = elapsed + (eta or 0.0) + EMERGENCY_SERVICE_BUFFER_SECONDS
                self._phase_duration_seconds = max(previous, min(emergency_cap, target_duration))
                changed = self._phase_duration_seconds > previous + 0.05
                result.update(
                    {
                        "decision": "grant",
                        "action": "extend_vehicle_green_for_emergency" if changed else "emergency_vehicle_green_ready",
                        "reason": (
                            "extended vehicle green within configured caps for the simulated emergency vehicle"
                            if changed
                            else "vehicle green is already available long enough for the simulated emergency request"
                        ),
                    }
                )
            elif phase_key in {"pedestrian_green", "pedestrian_flashing"} and int(local_pedestrians_crossing) > 0:
                result.update(
                    {
                        "decision": "deny",
                        "action": "deny_active_pedestrian_crossing",
                        "reason": "active simulated pedestrian crossing must clear before emergency vehicle service can progress",
                    }
                )
            else:
                self._pending_request = "vehicle"
                minimum = float(phase_limits["min_seconds"])
                requested_duration = max(minimum, elapsed + 0.2)
                self._phase_duration_seconds = min(previous, requested_duration)
                changed = self._phase_duration_seconds < previous - 0.05
                result.update(
                    {
                        "decision": "grant",
                        "action": "request_protected_emergency_progression" if changed else "emergency_progression_pending",
                        "reason": (
                            "shortened only the current protected phase toward its configured minimum for the simulated emergency request"
                            if changed
                            else "emergency vehicle service is requested; protected progression cannot shorten the current phase further"
                        ),
                    }
                )

            delta = float(self._phase_duration_seconds) - previous
            result.update(
                {
                    "applied": changed,
                    "timing_delta_seconds": round(delta, 1),
                    "phase_key": phase_key,
                    "previous_duration_seconds": round(previous, 1),
                    "effective_duration_seconds": round(float(self._phase_duration_seconds), 1),
                }
            )
            if changed:
                self._record_event_locked(
                    "emergency_priority_applied",
                    {
                        "emergency_event_id": emergency_event_id,
                        "vehicle_type": vehicle_type,
                        "role": role,
                        "intersection_id": intersection_id,
                        "link_id": link_id,
                        "action": result["action"],
                        "phase_key": phase_key,
                        "eta_seconds": result["eta_seconds"],
                        "previous_duration_seconds": result["previous_duration_seconds"],
                        "effective_duration_seconds": result["effective_duration_seconds"],
                        "simulation_clock_seconds": round(float(clock_s), 1),
                        "provenance": "simulated_configured_emergency_event",
                    },
                )
            return result


class _IntersectionRuntime:
    def __init__(
        self,
        *,
        intersection: dict[str, Any],
        mode: str,
        profile: str,
        policy_config: dict[str, Any],
        zone_types: dict[str, str],
        temp_root: Path,
        controller_factory: Callable[[Path, Path], Any] | None = None,
    ) -> None:
        self.intersection = deepcopy(intersection)
        self.intersection_id = str(intersection["id"])
        self.mode = mode
        self.profile = profile
        self.zone_types = dict(zone_types)

        config = deepcopy(policy_config)
        config["mode"] = "adaptive" if mode in COOPERATIVE_MODES else mode
        config["dry_run"] = False
        config["active_profile"] = profile
        config_path = temp_root / f"{mode}_{self.intersection_id}_policy.json"
        history_path = temp_root / f"{mode}_{self.intersection_id}_history.jsonl"
        config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        self.history_path = history_path
        if controller_factory is None:
            self.controller = _BenchmarkSignalRulesService(config_path=config_path, history_path=history_path)
        else:
            self.controller = controller_factory(config_path, history_path)

        self.vehicle_queue: deque[_QueuedVehicle] = deque()
        self.pedestrian_queue: deque[float] = deque()
        self.pedestrian_crossing_clear_times: deque[float] = deque()
        self.vehicle_waits: list[float] = []
        self.pedestrian_waits: list[float] = []
        self.vehicle_class_external_arrivals: dict[str, int] = {}
        self.vehicle_class_transfer_arrivals: dict[str, int] = {}
        self.vehicle_class_served: dict[str, int] = {}
        self.vehicle_class_waits: dict[str, list[float]] = {}
        self.vehicle_class_queue_samples: dict[str, list[int]] = {}
        self.vehicle_queue_samples: list[int] = []
        self.pedestrian_queue_samples: list[int] = []
        self.vehicle_queue_seconds = 0.0
        self.pedestrian_queue_seconds = 0.0
        self.vehicle_queue_occupied_seconds = 0.0
        self.pedestrian_queue_occupied_seconds = 0.0
        self.vehicles_served = 0
        self.pedestrians_served = 0
        self.external_vehicle_arrivals = 0
        self.transfer_vehicle_arrivals = 0
        self.external_pedestrian_arrivals = 0
        self.pedestrian_requests_started = 0
        self.pedestrian_requests_fulfilled = 0
        self.pedestrian_service_sessions = 0
        self.pedestrian_wait_threshold_hits = 0
        self.pedestrian_crossing_peak = 0
        self.max_observed_pedestrian_wait_seconds = 0.0
        self.pedestrian_request_fulfillment_seconds: list[float] = []
        self._pedestrian_request_started_at_s: float | None = None
        self._pedestrian_service_session_open = False
        self.phase_time_seconds: dict[str, float] = {}
        self.phase_transitions = 0
        self.cycles_completed = 0
        self._previous_phase_key: str | None = None
        self._vehicle_service_credit = 0.0
        self._pedestrian_service_credit = 0.0
        self.scenario_evidence_events: list[dict[str, Any]] = []
        self._last_scenario_evidence_signature: tuple[str, str] | None = None

    def enqueue_external_vehicle(self, event: _VehicleArrival) -> None:
        self.vehicle_queue.append(
            _QueuedVehicle(
                vehicle_id=event.vehicle_id,
                class_name=event.class_name,
                queued_at_s=event.at_s,
                network_started_at_s=event.at_s,
                continues_to_destination=event.continues_to_destination,
            )
        )
        self.external_vehicle_arrivals += 1
        class_name = _normalize_vehicle_class(event.class_name)
        self.vehicle_class_external_arrivals[class_name] = self.vehicle_class_external_arrivals.get(class_name, 0) + 1

    def enqueue_transfer(self, transfer: _Transfer) -> None:
        vehicle = transfer.vehicle
        vehicle.queued_at_s = transfer.arrive_at_s
        vehicle.origin = "transfer"
        vehicle.continues_to_destination = False
        self.vehicle_queue.append(vehicle)
        self.transfer_vehicle_arrivals += 1
        class_name = _normalize_vehicle_class(vehicle.class_name)
        self.vehicle_class_transfer_arrivals[class_name] = self.vehicle_class_transfer_arrivals.get(class_name, 0) + 1

    def enqueue_pedestrian(self, event: _PedestrianArrival) -> None:
        if not self.pedestrian_queue and self._pedestrian_request_started_at_s is None:
            self._pedestrian_request_started_at_s = event.at_s
            self.pedestrian_requests_started += 1
        self.pedestrian_queue.append(event.at_s)
        self.external_pedestrian_arrivals += 1

    def observation(self) -> dict[str, Any]:
        class_counts: dict[str, int] = {}
        for vehicle in self.vehicle_queue:
            class_name = _normalize_vehicle_class(vehicle.class_name)
            class_counts[class_name] = class_counts.get(class_name, 0) + 1

        zone_class_counts: dict[str, dict[str, int]] = {}
        for zone_id in self.intersection.get("zone_ids", []):
            zone_type = self.zone_types.get(str(zone_id))
            if zone_type == "vehicle_queue":
                zone_class_counts[str(zone_id)] = dict(class_counts)
            elif zone_type == "pedestrian_waiting":
                zone_class_counts[str(zone_id)] = {"person": len(self.pedestrian_queue)} if self.pedestrian_queue else {}
            elif zone_type == "crossing":
                zone_class_counts[str(zone_id)] = {"person": len(self.pedestrian_crossing_clear_times)} if self.pedestrian_crossing_clear_times else {}
            elif zone_type == "counting_region":
                combined = dict(class_counts)
                person_count = len(self.pedestrian_queue) + len(self.pedestrian_crossing_clear_times)
                if person_count:
                    combined["person"] = person_count
                zone_class_counts[str(zone_id)] = combined
            else:
                zone_class_counts[str(zone_id)] = {}

        return {
            "vehicles_waiting": len(self.vehicle_queue),
            "pedestrians_waiting": len(self.pedestrian_queue),
            "pedestrians_crossing": len(self.pedestrian_crossing_clear_times),
            "zone_class_counts": zone_class_counts,
            "data_source": "network_simulation_experiment",
        }

    def signal(self, clock_s: float) -> dict[str, Any]:
        if hasattr(self.controller, "set_benchmark_clock"):
            self.controller.set_benchmark_clock(clock_s)
        observation = self.observation()
        self.controller.observe(observation)
        signal = self.controller.signal_state(clock_s)
        self._capture_scenario_evidence(clock_s, signal, observation)
        return signal

    def _capture_scenario_evidence(
        self,
        clock_s: float,
        signal: dict[str, Any],
        observation: dict[str, Any],
    ) -> None:
        active_rules = signal.get("active_rules") if isinstance(signal.get("active_rules"), list) else []
        winner_id = signal.get("winning_scenario_id") or (active_rules[0] if active_rules else None)
        if not winner_id:
            self._last_scenario_evidence_signature = None
            return
        phase_key = str(signal.get("phase_key") or signal.get("phase") or "unknown")
        signature = (phase_key, str(winner_id))
        if signature == self._last_scenario_evidence_signature:
            return
        self._last_scenario_evidence_signature = signature

        statuses = signal.get("scenario_status") if isinstance(signal.get("scenario_status"), list) else signal.get("rule_status")
        winner_status: dict[str, Any] = {}
        if isinstance(statuses, list):
            for status in statuses:
                if not isinstance(status, dict):
                    continue
                status_id = status.get("scenario_id") or status.get("rule_id")
                if str(status_id) == str(winner_id):
                    winner_status = status
                    break
        action_data = winner_status.get("action") if isinstance(winner_status.get("action"), dict) else {}
        action = str(action_data.get("type") or "scenario_active")
        base_duration = signal.get("base_duration_seconds")
        effective_duration = signal.get("effective_duration_seconds")
        delta = 0.0
        if isinstance(base_duration, (int, float)) and isinstance(effective_duration, (int, float)):
            delta = float(effective_duration) - float(base_duration)
        self.scenario_evidence_events.append(
            {
                "scenario_id": str(winner_id),
                "t": round(float(clock_s), 1),
                "phase": signal.get("phase"),
                "phase_key": phase_key,
                "action": action,
                "applied": True,
                "reason": winner_status.get("reason") or "ranked scenario is active for the current protected phase",
                "observations": deepcopy(signal.get("observations"))
                if isinstance(signal.get("observations"), dict)
                else deepcopy(observation),
                "base_duration_seconds": float(base_duration) if isinstance(base_duration, (int, float)) else None,
                "effective_duration_seconds": float(effective_duration) if isinstance(effective_duration, (int, float)) else None,
                "timing_delta_seconds": round(delta, 1),
                "provenance": "simulation_signal_controller",
            }
        )

    def apply_coordination(self, *, clock_s: float, advisory: dict[str, Any]) -> dict[str, Any]:
        if self.mode not in COOPERATIVE_MODES:
            return {"applied": False, "action": "disabled", "reason": "cooperative mode is not active"}
        method = getattr(self.controller, "apply_network_coordination", None)
        if method is None:
            return {"applied": False, "action": "unsupported", "reason": "controller does not support network coordination"}
        return method(
            clock_s=clock_s,
            local_pedestrians_waiting=len(self.pedestrian_queue),
            local_pedestrians_crossing=len(self.pedestrian_crossing_clear_times),
            **advisory,
        )

    def prune_crossings(self, clock_s: float) -> None:
        while self.pedestrian_crossing_clear_times and self.pedestrian_crossing_clear_times[0] <= clock_s + 1e-9:
            self.pedestrian_crossing_clear_times.popleft()

    def pedestrian_context(self, clock_s: float) -> dict[str, Any]:
        self.prune_crossings(clock_s)
        oldest = max(0.0, clock_s - self.pedestrian_queue[0]) if self.pedestrian_queue else 0.0
        self.max_observed_pedestrian_wait_seconds = max(self.max_observed_pedestrian_wait_seconds, oldest)
        self.pedestrian_crossing_peak = max(self.pedestrian_crossing_peak, len(self.pedestrian_crossing_clear_times))
        return {
            "waiting_count": len(self.pedestrian_queue),
            "oldest_wait_seconds": oldest,
            "crossing_count": len(self.pedestrian_crossing_clear_times),
        }

    def apply_pedestrian_awareness(
        self,
        *,
        clock_s: float,
        max_wait_seconds: float,
        clearance_reserve_seconds: float,
    ) -> dict[str, Any]:
        if self.mode not in PEDESTRIAN_AWARE_MODES:
            return {"applied": False, "action": "disabled", "reason": "pedestrian-aware mode is not active"}
        method = getattr(self.controller, "apply_pedestrian_service_guard", None)
        if method is None:
            return {"applied": False, "action": "unsupported", "reason": "controller does not support pedestrian service guard"}
        context = self.pedestrian_context(clock_s)
        if context["waiting_count"] > 0 and context["oldest_wait_seconds"] + 1e-9 >= max_wait_seconds:
            self.pedestrian_wait_threshold_hits += 1
        return method(
            clock_s=clock_s,
            max_wait_seconds=max_wait_seconds,
            clearance_reserve_seconds=clearance_reserve_seconds,
            intersection_id=self.intersection_id,
            **context,
        )

    def vehicle_class_context(self, class_name: str, clock_s: float) -> dict[str, Any]:
        normalized = _normalize_vehicle_class(class_name)
        matches = [vehicle for vehicle in self.vehicle_queue if _normalize_vehicle_class(vehicle.class_name) == normalized]
        oldest = max((max(0.0, clock_s - vehicle.queued_at_s) for vehicle in matches), default=0.0)
        return {
            "class_name": normalized,
            "waiting_count": len(matches),
            "oldest_wait_seconds": oldest,
        }

    def apply_vehicle_class_priority(
        self,
        *,
        clock_s: float,
        class_name: str,
        priority_weight: float,
        max_extension_seconds: float,
    ) -> dict[str, Any]:
        if self.mode not in CLASS_AWARE_MODES:
            return {"applied": False, "action": "disabled", "reason": "vehicle-class-aware mode is not active"}
        method = getattr(self.controller, "apply_vehicle_class_priority", None)
        if method is None:
            return {"applied": False, "action": "unsupported", "reason": "controller does not support vehicle-class-aware priority"}
        context = self.vehicle_class_context(class_name, clock_s)
        pedestrian = self.pedestrian_context(clock_s)
        return method(
            clock_s=clock_s,
            priority_weight=priority_weight,
            max_extension_seconds=max_extension_seconds,
            local_pedestrians_waiting=int(pedestrian["waiting_count"]),
            local_pedestrians_crossing=int(pedestrian["crossing_count"]),
            intersection_id=self.intersection_id,
            **context,
        )


    def apply_emergency_priority(
        self,
        *,
        clock_s: float,
        emergency_event: dict[str, Any],
        role: str,
        eta_seconds: float | None,
        lookahead_seconds: float,
        max_extension_seconds: float,
        link_id: str,
    ) -> dict[str, Any]:
        if self.mode not in EMERGENCY_PRIORITY_MODES:
            return {"applied": False, "decision": "defer", "action": "disabled", "reason": "emergency priority mode is not active"}
        method = getattr(self.controller, "apply_emergency_priority", None)
        if method is None:
            return {"applied": False, "decision": "deny", "action": "unsupported", "reason": "controller does not support emergency priority"}
        context = self.pedestrian_context(clock_s)
        return method(
            clock_s=clock_s,
            emergency_active=True,
            emergency_event_id=str(emergency_event.get("event_id") or "emergency"),
            vehicle_type=str(emergency_event.get("vehicle_type") or "emergency"),
            role=role,
            eta_seconds=eta_seconds,
            lookahead_seconds=lookahead_seconds,
            max_extension_seconds=max_extension_seconds,
            local_pedestrians_waiting=int(context["waiting_count"]),
            local_pedestrians_crossing=int(context["crossing_count"]),
            intersection_id=self.intersection_id,
            link_id=link_id,
        )

    def advance_signal_metrics(self, signal: dict[str, Any], dt: float) -> None:
        phase = str(signal.get("phase") or "unknown")
        self.phase_time_seconds[phase] = self.phase_time_seconds.get(phase, 0.0) + dt
        phase_key = str(signal.get("phase_key") or phase)
        if self._previous_phase_key is not None and phase_key != self._previous_phase_key:
            self.phase_transitions += 1
            if phase_key == "vehicle_green":
                self.cycles_completed += 1
        self._previous_phase_key = phase_key

    def serve_vehicles(self, *, clock_s: float, dt: float, vehicle_go: bool) -> list[_QueuedVehicle]:
        if not vehicle_go:
            self._vehicle_service_credit = 0.0
            return []
        self._vehicle_service_credit += VEHICLE_SERVICE_PER_SECOND * dt
        served: list[_QueuedVehicle] = []
        while self._vehicle_service_credit + 1e-9 >= 1.0 and self.vehicle_queue:
            self._vehicle_service_credit -= 1.0
            vehicle = self.vehicle_queue.popleft()
            wait_seconds = max(0.0, clock_s - vehicle.queued_at_s)
            self.vehicle_waits.append(wait_seconds)
            class_name = _normalize_vehicle_class(vehicle.class_name)
            self.vehicle_class_waits.setdefault(class_name, []).append(wait_seconds)
            self.vehicle_class_served[class_name] = self.vehicle_class_served.get(class_name, 0) + 1
            self.vehicles_served += 1
            served.append(vehicle)
        return served

    def serve_pedestrians(
        self,
        *,
        clock_s: float,
        dt: float,
        pedestrian_walk: bool,
        crossing_clearance_seconds: float,
    ) -> None:
        self.prune_crossings(clock_s)
        if not pedestrian_walk:
            self._pedestrian_service_credit = 0.0
            self._pedestrian_service_session_open = False
            return
        if self.pedestrian_queue and not self._pedestrian_service_session_open:
            self.pedestrian_service_sessions += 1
            self._pedestrian_service_session_open = True
        self._pedestrian_service_credit += PEDESTRIAN_SERVICE_PER_SECOND * dt
        served_any = False
        while self._pedestrian_service_credit + 1e-9 >= 1.0 and self.pedestrian_queue:
            self._pedestrian_service_credit -= 1.0
            queued_at_s = self.pedestrian_queue.popleft()
            self.pedestrian_waits.append(max(0.0, clock_s - queued_at_s))
            self.pedestrian_crossing_clear_times.append(clock_s + max(0.0, float(crossing_clearance_seconds)))
            self.pedestrians_served += 1
            served_any = True
        if served_any:
            self.pedestrian_crossing_peak = max(self.pedestrian_crossing_peak, len(self.pedestrian_crossing_clear_times))
        if not self.pedestrian_queue and self._pedestrian_request_started_at_s is not None:
            self.pedestrian_requests_fulfilled += 1
            self.pedestrian_request_fulfillment_seconds.append(max(0.0, clock_s - self._pedestrian_request_started_at_s))
            self._pedestrian_request_started_at_s = None

    def record_queue_time(self, dt: float, *, clock_s: float | None = None) -> None:
        vehicle_count = len(self.vehicle_queue)
        pedestrian_count = len(self.pedestrian_queue)
        if clock_s is not None and self.pedestrian_queue:
            self.max_observed_pedestrian_wait_seconds = max(
                self.max_observed_pedestrian_wait_seconds, max(0.0, clock_s - self.pedestrian_queue[0])
            )
        self.vehicle_queue_seconds += vehicle_count * dt
        self.pedestrian_queue_seconds += pedestrian_count * dt
        if vehicle_count:
            self.vehicle_queue_occupied_seconds += dt
        if pedestrian_count:
            self.pedestrian_queue_occupied_seconds += dt

    def sample_queues(self) -> None:
        self.vehicle_queue_samples.append(len(self.vehicle_queue))
        self.pedestrian_queue_samples.append(len(self.pedestrian_queue))
        counts = {class_name: 0 for class_name in (*REGULAR_VEHICLE_CLASSES, *SPECIAL_VEHICLE_CLASSES)}
        for vehicle in self.vehicle_queue:
            class_name = _normalize_vehicle_class(vehicle.class_name)
            counts[class_name] = counts.get(class_name, 0) + 1
        for class_name, count in counts.items():
            self.vehicle_class_queue_samples.setdefault(class_name, []).append(count)

    def finalize_waits(self, clock_s: float) -> None:
        for vehicle in self.vehicle_queue:
            wait_seconds = max(0.0, clock_s - vehicle.queued_at_s)
            self.vehicle_waits.append(wait_seconds)
            class_name = _normalize_vehicle_class(vehicle.class_name)
            self.vehicle_class_waits.setdefault(class_name, []).append(wait_seconds)
        for queued_at_s in self.pedestrian_queue:
            self.pedestrian_waits.append(max(0.0, clock_s - queued_at_s))

    def scenario_evidence(self) -> list[dict[str, Any]]:
        """Return exact applied-scenario timing evidence when controller history exists.

        Live/fake focused controllers may not emit history; in that case the
        read-only active-winner snapshots captured from signal state are kept.
        """
        if not self.history_path.is_file():
            return deepcopy(self.scenario_evidence_events)
        applied: list[dict[str, Any]] = []
        try:
            lines = self.history_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return deepcopy(self.scenario_evidence_events)
        for line in lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("event_type") != "rule_applied":
                continue
            details = event.get("details") if isinstance(event.get("details"), dict) else {}
            scenario_id = str(details.get("scenario_id") or details.get("rule_id") or "unknown")
            clock_s = details.get("simulation_clock_seconds")
            matching = [
                snapshot
                for snapshot in self.scenario_evidence_events
                if str(snapshot.get("scenario_id")) == scenario_id
            ]
            snapshot = min(
                matching,
                key=lambda item: abs(float(item.get("t", 0.0) or 0.0) - float(clock_s or 0.0)),
                default={},
            )
            previous = float(details.get("previous_duration_seconds", 0.0) or 0.0)
            effective = float(details.get("effective_duration_seconds", previous) or previous)
            applied.append(
                {
                    "scenario_id": scenario_id,
                    "t": round(float(clock_s or snapshot.get("t", 0.0) or 0.0), 1),
                    "phase": snapshot.get("phase"),
                    "phase_key": details.get("phase_key") or snapshot.get("phase_key"),
                    "action": details.get("action") or snapshot.get("action") or "scenario_active",
                    "applied": True,
                    "reason": snapshot.get("reason") or "ranked scenario was applied by the protected signal controller",
                    "observations": deepcopy(snapshot.get("observations"))
                    if isinstance(snapshot.get("observations"), dict)
                    else {},
                    "base_duration_seconds": snapshot.get("base_duration_seconds"),
                    "previous_duration_seconds": round(previous, 1),
                    "effective_duration_seconds": round(effective, 1),
                    "timing_delta_seconds": round(effective - previous, 1),
                    "provenance": "simulation_signal_controller",
                }
            )
        return applied or deepcopy(self.scenario_evidence_events)

    def controller_stats(self) -> dict[str, Any]:
        applications: dict[str, int] = {}
        extension_seconds = 0.0
        reduction_seconds = 0.0
        if self.history_path.is_file():
            for line in self.history_path.read_text(encoding="utf-8").splitlines():
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("event_type") != "rule_applied":
                    continue
                details = event.get("details") if isinstance(event.get("details"), dict) else {}
                rule_id = str(details.get("rule_id") or "unknown")
                applications[rule_id] = applications.get(rule_id, 0) + 1
                previous = float(details.get("previous_duration_seconds", 0.0) or 0.0)
                effective = float(details.get("effective_duration_seconds", previous) or previous)
                delta = effective - previous
                if delta > 0:
                    extension_seconds += delta
                elif delta < 0:
                    reduction_seconds += abs(delta)
        return {
            "scenario_application_count": sum(applications.values()),
            "scenario_applications": dict(sorted(applications.items())),
            "extension_seconds": round(extension_seconds, 1),
            "reduction_seconds": round(reduction_seconds, 1),
        }

    def result(self, duration_seconds: int, last_signal: dict[str, Any] | None) -> dict[str, Any]:
        duration_minutes = duration_seconds / 60.0
        return {
            "intersection_id": self.intersection_id,
            "label": self.intersection.get("label"),
            "profile": self.profile,
            "metrics": {
                "waiting": {
                    "vehicle": _distribution(self.vehicle_waits),
                    "pedestrian": _distribution(self.pedestrian_waits),
                },
                "queues": {
                    "vehicle": _queue_distribution(
                        self.vehicle_queue_samples,
                        self.vehicle_queue_seconds,
                        self.vehicle_queue_occupied_seconds,
                        duration_seconds,
                    ),
                    "pedestrian": _queue_distribution(
                        self.pedestrian_queue_samples,
                        self.pedestrian_queue_seconds,
                        self.pedestrian_queue_occupied_seconds,
                        duration_seconds,
                    ),
                },
                "throughput": {
                    "vehicles_served": self.vehicles_served,
                    "pedestrians_served": self.pedestrians_served,
                    "vehicles_per_minute": round(self.vehicles_served / duration_minutes, 2) if duration_minutes else 0.0,
                    "pedestrians_per_minute": round(self.pedestrians_served / duration_minutes, 2) if duration_minutes else 0.0,
                    "external_vehicle_arrivals": self.external_vehicle_arrivals,
                    "transfer_vehicle_arrivals": self.transfer_vehicle_arrivals,
                    "external_pedestrian_arrivals": self.external_pedestrian_arrivals,
                },
                "vehicle_classes": _intersection_vehicle_class_metrics(self),
                "pedestrian_awareness": {
                    "requests_started": self.pedestrian_requests_started,
                    "requests_fulfilled": self.pedestrian_requests_fulfilled,
                    "service_sessions": self.pedestrian_service_sessions,
                    "wait_threshold_evaluations": self.pedestrian_wait_threshold_hits,
                    "max_observed_wait_seconds": round(self.max_observed_pedestrian_wait_seconds, 2),
                    "request_fulfillment": _distribution(self.pedestrian_request_fulfillment_seconds),
                    "crossing_peak": self.pedestrian_crossing_peak,
                    "crossing_active_at_end": len(self.pedestrian_crossing_clear_times),
                },
                "signal": {
                    "phase_time_seconds": {key: round(value, 1) for key, value in sorted(self.phase_time_seconds.items())},
                    "phase_share_percent": {
                        key: round(value / duration_seconds * 100.0, 1)
                        for key, value in sorted(self.phase_time_seconds.items())
                    },
                    "phase_transitions": self.phase_transitions,
                    "cycles_completed": self.cycles_completed,
                    **self.controller_stats(),
                },
            },
            "final_signal": last_signal,
            "scenario_evidence_events": self.scenario_evidence(),
        }


class _NetworkModeSimulation:
    def __init__(
        self,
        *,
        mode: str,
        duration_seconds: int,
        sample_interval_seconds: int,
        source_intersection: dict[str, Any],
        destination_intersection: dict[str, Any],
        link: dict[str, Any],
        policy_config: dict[str, Any],
        profile_override: str | None,
        zone_types: dict[str, str],
        source_vehicle_arrivals: list[_VehicleArrival],
        destination_vehicle_arrivals: list[_VehicleArrival],
        source_pedestrian_arrivals: list[_PedestrianArrival],
        destination_pedestrian_arrivals: list[_PedestrianArrival],
        temp_root: Path,
        controller_factory: Callable[[Path, Path], Any] | None = None,
        cooperation_lookahead_seconds: float = 12.0,
        cooperation_max_extension_seconds: float = 5.0,
        cooperation_min_incoming_vehicles: int = 1,
        pedestrian_max_wait_seconds: float = 30.0,
        pedestrian_crossing_clearance_seconds: float = 6.0,
        pedestrian_clearance_reserve_seconds: float = 3.0,
        vehicle_class_priority_enabled: bool = True,
        vehicle_class_priority_class: str = "bus",
        vehicle_class_priority_weight: float = 2.0,
        vehicle_class_priority_min_waiting: int = 1,
        vehicle_class_priority_max_extension_seconds: float = 4.0,
        emergency_event: dict[str, Any] | None = None,
        emergency_priority_lookahead_seconds: float = 20.0,
        emergency_priority_max_extension_seconds: float = 8.0,
    ) -> None:
        self.mode = mode
        self.duration_seconds = duration_seconds
        self.sample_interval_seconds = sample_interval_seconds
        self.link = deepcopy(link)
        self.cooperation_lookahead_seconds = float(cooperation_lookahead_seconds)
        self.cooperation_max_extension_seconds = float(cooperation_max_extension_seconds)
        self.cooperation_min_incoming_vehicles = int(cooperation_min_incoming_vehicles)
        self.pedestrian_max_wait_seconds = float(pedestrian_max_wait_seconds)
        self.pedestrian_crossing_clearance_seconds = float(pedestrian_crossing_clearance_seconds)
        self.pedestrian_clearance_reserve_seconds = float(pedestrian_clearance_reserve_seconds)
        self.vehicle_class_priority_enabled = bool(vehicle_class_priority_enabled)
        self.vehicle_class_priority_class = _normalize_vehicle_class(vehicle_class_priority_class)
        self.vehicle_class_priority_weight = float(vehicle_class_priority_weight)
        self.vehicle_class_priority_min_waiting = int(vehicle_class_priority_min_waiting)
        self.vehicle_class_priority_max_extension_seconds = float(vehicle_class_priority_max_extension_seconds)
        self.emergency_event = deepcopy(emergency_event) if emergency_event else None
        self.emergency_priority_lookahead_seconds = float(emergency_priority_lookahead_seconds)
        self.emergency_priority_max_extension_seconds = float(emergency_priority_max_extension_seconds)
        self.source_vehicle_arrivals = source_vehicle_arrivals
        self.destination_vehicle_arrivals = destination_vehicle_arrivals
        self.source_pedestrian_arrivals = source_pedestrian_arrivals
        self.destination_pedestrian_arrivals = destination_pedestrian_arrivals
        self._source_vehicle_index = 0
        self._destination_vehicle_index = 0
        self._source_pedestrian_index = 0
        self._destination_pedestrian_index = 0
        self.pipeline: list[_Transfer] = []
        self.pipeline_samples: list[int] = []
        self.transfers_departed = 0
        self.transfers_arrived = 0
        self.transfer_events: dict[str, dict[str, Any]] = {}
        self.corridor_completed = 0
        self.corridor_travel_times: list[float] = []
        self.timeline: list[dict[str, Any]] = []
        self.coordination_evaluations = 0
        self.coordination_triggered = 0
        self.coordination_applied = 0
        self.coordination_green_extensions = 0
        self.coordination_progression_requests = 0
        self.coordination_pedestrian_protections = 0
        self.coordination_seconds_added = 0.0
        self.coordination_seconds_reduced = 0.0
        self.coordination_events: list[dict[str, Any]] = []
        self.pedestrian_awareness_evaluations = 0
        self.pedestrian_awareness_applied = 0
        self.pedestrian_starvation_preventions = 0
        self.pedestrian_clearance_extensions = 0
        self.pedestrian_awareness_seconds_added = 0.0
        self.pedestrian_awareness_seconds_reduced = 0.0
        self.pedestrian_awareness_events: list[dict[str, Any]] = []
        self._latest_pedestrian_awareness: dict[str, dict[str, Any]] = {
            "source": {"active": False, "action": "none"},
            "destination": {"active": False, "action": "none"},
        }
        self._latest_coordination: dict[str, Any] = {
            "active": False,
            "incoming_vehicle_count": 0,
            "earliest_arrival_eta_seconds": None,
            "action": "none",
        }
        self.vehicle_class_priority_evaluations = 0
        self.vehicle_class_priority_triggered = 0
        self.vehicle_class_priority_applied = 0
        self.vehicle_class_priority_pedestrian_protections = 0
        self.vehicle_class_priority_seconds_added = 0.0
        self.vehicle_class_priority_seconds_reduced = 0.0
        self.vehicle_class_priority_events: list[dict[str, Any]] = []
        self._latest_vehicle_class_priority: dict[str, dict[str, Any]] = {
            "source": {"active": False, "action": "none"},
            "destination": {"active": False, "action": "none"},
        }
        self._emergency_injected = False
        self._emergency_status = "scheduled" if self.emergency_event else "none"
        self._emergency_source_departed_at_s: float | None = None
        self._emergency_destination_arrived_at_s: float | None = None
        self._emergency_cleared_at_s: float | None = None
        self.emergency_priority_evaluations = 0
        self.emergency_priority_grants = 0
        self.emergency_priority_denials = 0
        self.emergency_priority_applied = 0
        self.emergency_downstream_preparations = 0
        self.emergency_priority_seconds_added = 0.0
        self.emergency_priority_seconds_reduced = 0.0
        self.emergency_priority_events: list[dict[str, Any]] = []
        self.emergency_lifecycle_events: list[dict[str, Any]] = []
        self._latest_emergency_priority: dict[str, Any] = {
            "active": False,
            "status": self._emergency_status,
            "action": "none",
            "decision": "defer",
        }
        self._sample_at_s = 0.0

        profiles = policy_config.get("profiles") if isinstance(policy_config, dict) else None
        if not isinstance(profiles, dict):
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "Signal profile configuration is unavailable.", status_code=422)

        source_profile = profile_override or str(source_intersection.get("signal_profile") or policy_config.get("active_profile") or "")
        destination_profile = profile_override or str(destination_intersection.get("signal_profile") or policy_config.get("active_profile") or "")
        for intersection_id, profile in (
            (source_intersection["id"], source_profile),
            (destination_intersection["id"], destination_profile),
        ):
            if profile not in profiles:
                raise AppError(
                    ErrorCode.TRAFFIC_RULE_INVALID,
                    "Network experiment profile must identify an existing signal profile.",
                    status_code=422,
                    details={"intersection_id": intersection_id, "profile": profile, "available_profiles": sorted(profiles)},
                )

        self.source = _IntersectionRuntime(
            intersection=source_intersection,
            mode=mode,
            profile=source_profile,
            policy_config=policy_config,
            zone_types=zone_types,
            temp_root=temp_root,
            controller_factory=controller_factory,
        )
        self.destination = _IntersectionRuntime(
            intersection=destination_intersection,
            mode=mode,
            profile=destination_profile,
            policy_config=policy_config,
            zone_types=zone_types,
            temp_root=temp_root,
            controller_factory=controller_factory,
        )

    def run(self) -> dict[str, Any]:
        clock = 0.0
        last_source_signal: dict[str, Any] | None = None
        last_destination_signal: dict[str, Any] | None = None
        while clock < self.duration_seconds - 1e-9:
            dt = min(STEP_SECONDS, self.duration_seconds - clock)
            self._inject_arrivals(clock)
            self._deliver_transfers(clock)
            self._inject_emergency(clock)
            self.source.prune_crossings(clock)
            self.destination.prune_crossings(clock)

            source_signal = self.source.signal(clock)
            destination_signal = self.destination.signal(clock)
            if self.mode in PEDESTRIAN_AWARE_MODES:
                self._evaluate_pedestrian_awareness(clock, self.source, source_signal, role="source")
                self._evaluate_pedestrian_awareness(clock, self.destination, destination_signal, role="destination")
                source_signal = self.source.signal(clock)
                destination_signal = self.destination.signal(clock)
            if self.mode in COOPERATIVE_MODES:
                self._evaluate_cooperation(clock, destination_signal)
                # Re-read after a timing advisory so the served phase/remaining
                # time reflect the bounded mutation performed by the controller.
                destination_signal = self.destination.signal(clock)
            if self.mode in CLASS_AWARE_MODES and self.vehicle_class_priority_enabled:
                self._evaluate_vehicle_class_priority(clock, self.source, source_signal, role="source")
                self._evaluate_vehicle_class_priority(clock, self.destination, destination_signal, role="destination")
                source_signal = self.source.signal(clock)
                destination_signal = self.destination.signal(clock)
            if self.mode in EMERGENCY_PRIORITY_MODES:
                self._evaluate_emergency_priority(clock, source_signal, destination_signal)
                # Emergency priority is the last advisory layer, but still only
                # mutates timing through protected minimum/maximum/cycle bounds.
                source_signal = self.source.signal(clock)
                destination_signal = self.destination.signal(clock)
            last_source_signal = source_signal
            last_destination_signal = destination_signal
            self.source.advance_signal_metrics(source_signal, dt)
            self.destination.advance_signal_metrics(destination_signal, dt)

            served_source = self.source.serve_vehicles(
                clock_s=clock,
                dt=dt,
                vehicle_go=bool(source_signal.get("vehicle_go")),
            )
            for vehicle in served_source:
                if vehicle.continues_to_destination:
                    vehicle.source_departed_at_s = clock
                    scheduled_arrival = clock + float(self.link["travel_time_seconds"])
                    self.pipeline.append(_Transfer(arrive_at_s=scheduled_arrival, vehicle=vehicle))
                    self.transfers_departed += 1
                    self.transfer_events[vehicle.vehicle_id] = {
                        "vehicle_id": vehicle.vehicle_id,
                        "class_name": vehicle.class_name,
                        "departed_at_s": round(clock, 1),
                        "scheduled_arrival_s": round(scheduled_arrival, 1),
                        "arrived_at_s": None,
                    }
                    if self._is_emergency_vehicle(vehicle.vehicle_id):
                        self._mark_emergency_source_departed(clock, scheduled_arrival)

            served_destination = self.destination.serve_vehicles(
                clock_s=clock,
                dt=dt,
                vehicle_go=bool(destination_signal.get("vehicle_go")),
            )
            for vehicle in served_destination:
                if vehicle.origin == "transfer":
                    self.corridor_completed += 1
                    self.corridor_travel_times.append(max(0.0, clock - vehicle.network_started_at_s))
                if self._is_emergency_vehicle(vehicle.vehicle_id):
                    self._mark_emergency_cleared(clock)

            self.source.serve_pedestrians(
                clock_s=clock,
                dt=dt,
                pedestrian_walk=bool(source_signal.get("pedestrian_walk")),
                crossing_clearance_seconds=self.pedestrian_crossing_clearance_seconds,
            )
            self.destination.serve_pedestrians(
                clock_s=clock,
                dt=dt,
                pedestrian_walk=bool(destination_signal.get("pedestrian_walk")),
                crossing_clearance_seconds=self.pedestrian_crossing_clearance_seconds,
            )
            self.source.record_queue_time(dt, clock_s=clock)
            self.destination.record_queue_time(dt, clock_s=clock)

            clock += dt
            self._deliver_transfers(clock)
            if clock + 1e-9 >= self._sample_at_s:
                self.source.sample_queues()
                self.destination.sample_queues()
                self.pipeline_samples.append(len(self.pipeline))
                self._append_timeline(clock, source_signal, destination_signal)
                self._sample_at_s += self.sample_interval_seconds

        self.source.finalize_waits(self.duration_seconds)
        self.destination.finalize_waits(self.duration_seconds)
        return self._build_result(last_source_signal, last_destination_signal)

    def _evaluate_pedestrian_awareness(
        self,
        clock_s: float,
        runtime: _IntersectionRuntime,
        signal: dict[str, Any],
        *,
        role: str,
    ) -> None:
        self.pedestrian_awareness_evaluations += 1
        context = runtime.pedestrian_context(clock_s)
        outcome = runtime.apply_pedestrian_awareness(
            clock_s=clock_s,
            max_wait_seconds=self.pedestrian_max_wait_seconds,
            clearance_reserve_seconds=self.pedestrian_clearance_reserve_seconds,
        )
        event = {
            "pedestrian_awareness_id": f"pedaware_{runtime.intersection_id}_{int(round(clock_s * 1000.0))}",
            "t": round(clock_s, 1),
            "role": role,
            "intersection_id": runtime.intersection_id,
            "provenance": "synthetic_pedestrian_demand",
            "phase_before": signal.get("phase"),
            "phase_key_before": signal.get("phase_key"),
            "waiting_count": int(context["waiting_count"]),
            "oldest_wait_seconds": round(float(context["oldest_wait_seconds"]), 1),
            "crossing_count": int(context["crossing_count"]),
            "action": outcome.get("action", "none"),
            "applied": bool(outcome.get("applied")),
            "reason": outcome.get("reason"),
            "timing_delta_seconds": float(outcome.get("timing_delta_seconds", 0.0) or 0.0),
        }
        active = event["waiting_count"] > 0 or event["crossing_count"] > 0
        self._latest_pedestrian_awareness[role] = {"active": active, **event}
        if active or event["applied"]:
            self.pedestrian_awareness_events.append(event)
        if event["applied"]:
            self.pedestrian_awareness_applied += 1
            delta = event["timing_delta_seconds"]
            if delta > 0:
                self.pedestrian_awareness_seconds_added += delta
            elif delta < 0:
                self.pedestrian_awareness_seconds_reduced += abs(delta)
            if event["action"] == "request_pedestrian_service":
                self.pedestrian_starvation_preventions += 1
            elif event["action"] == "protect_crossing_clearance":
                self.pedestrian_clearance_extensions += 1

    def _cooperation_advisory(self, clock_s: float) -> dict[str, Any]:
        candidates = [
            transfer for transfer in self.pipeline
            if 0.0 <= transfer.arrive_at_s - clock_s <= self.cooperation_lookahead_seconds + 1e-9
        ]
        incoming_count = len(candidates)
        earliest_eta = min((transfer.arrive_at_s - clock_s for transfer in candidates), default=None)
        active = incoming_count >= self.cooperation_min_incoming_vehicles
        return {
            "incoming_vehicle_count": incoming_count if active else 0,
            "earliest_arrival_eta_seconds": earliest_eta if active else None,
            "lookahead_seconds": self.cooperation_lookahead_seconds,
            "max_extension_seconds": self.cooperation_max_extension_seconds,
            "link_id": str(self.link.get("id") or "link"),
            "source_intersection_id": self.source.intersection_id,
            "destination_intersection_id": self.destination.intersection_id,
        }

    def _evaluate_cooperation(self, clock_s: float, destination_signal: dict[str, Any]) -> None:
        self.coordination_evaluations += 1
        advisory = self._cooperation_advisory(clock_s)
        incoming = int(advisory["incoming_vehicle_count"])
        if incoming > 0:
            self.coordination_triggered += 1
        outcome = self.destination.apply_coordination(clock_s=clock_s, advisory=advisory)
        event = {
            "coordination_id": f"coord_{self.source.intersection_id}_{self.destination.intersection_id}_{int(round(clock_s * 1000.0))}",
            "t": round(clock_s, 1),
            "link_id": str(self.link.get("id") or "link"),
            "source_intersection_id": self.source.intersection_id,
            "destination_intersection_id": self.destination.intersection_id,
            "provenance": "synthetic_predicted_arrivals",
            "destination_phase_before": destination_signal.get("phase"),
            "destination_phase_key_before": destination_signal.get("phase_key"),
            "incoming_vehicle_count": incoming,
            "earliest_arrival_eta_seconds": (
                round(float(advisory["earliest_arrival_eta_seconds"]), 1)
                if advisory["earliest_arrival_eta_seconds"] is not None
                else None
            ),
            "action": outcome.get("action", "none"),
            "applied": bool(outcome.get("applied")),
            "reason": outcome.get("reason"),
            "timing_delta_seconds": float(outcome.get("timing_delta_seconds", 0.0) or 0.0),
        }
        self._latest_coordination = {"active": incoming > 0, **event}
        if incoming > 0 or event["applied"] or event["action"] == "protect_pedestrian_service":
            self.coordination_events.append(event)
        if event["applied"]:
            self.coordination_applied += 1
            delta = event["timing_delta_seconds"]
            if delta > 0:
                self.coordination_seconds_added += delta
            elif delta < 0:
                self.coordination_seconds_reduced += abs(delta)
            if event["action"] == "extend_vehicle_green":
                self.coordination_green_extensions += 1
            elif event["action"] == "request_protected_vehicle_progression":
                self.coordination_progression_requests += 1
        elif event["action"] == "protect_pedestrian_service":
            self.coordination_pedestrian_protections += 1

    def _is_emergency_vehicle(self, vehicle_id: str) -> bool:
        return bool(self.emergency_event) and str(vehicle_id) == str(self.emergency_event.get("vehicle_id"))

    def _record_emergency_lifecycle(self, clock_s: float, event_type: str, **details: Any) -> None:
        if not self.emergency_event:
            return
        self.emergency_lifecycle_events.append(
            {
                "emergency_event_id": str(self.emergency_event.get("event_id") or "emergency"),
                "t": round(float(clock_s), 1),
                "event_type": event_type,
                "status": self._emergency_status,
                "vehicle_type": self.emergency_event.get("vehicle_type"),
                "source_intersection_id": self.source.intersection_id,
                "destination_intersection_id": self.destination.intersection_id,
                "link_id": str(self.link.get("id") or "link"),
                "provenance": "simulated_configured_emergency_event",
                **details,
            }
        )

    def _inject_emergency(self, clock_s: float) -> None:
        if self.mode not in EMERGENCY_EVENT_MODES or not self.emergency_event or self._emergency_injected:
            return
        active_at_s = float(self.emergency_event.get("active_at_s", 0.0) or 0.0)
        if clock_s + 1e-9 < active_at_s:
            return
        event = _VehicleArrival(
            at_s=active_at_s,
            vehicle_id=str(self.emergency_event.get("vehicle_id") or "emergency_vehicle"),
            class_name="emergency",
            continues_to_destination=True,
        )
        self.source.enqueue_external_vehicle(event)
        self._emergency_injected = True
        self._emergency_status = "source_waiting"
        self._latest_emergency_priority = {
            "active": True,
            "status": self._emergency_status,
            "action": "emergency_event_activated",
            "decision": "defer",
        }
        self._record_emergency_lifecycle(
            clock_s,
            "activated",
            approach=self.emergency_event.get("source_approach"),
        )

    def _mark_emergency_source_departed(self, clock_s: float, scheduled_arrival_s: float) -> None:
        if not self.emergency_event:
            return
        self._emergency_source_departed_at_s = float(clock_s)
        self._emergency_status = "in_transit"
        self._record_emergency_lifecycle(
            clock_s,
            "source_departed",
            scheduled_destination_arrival_s=round(float(scheduled_arrival_s), 1),
        )

    def _mark_emergency_destination_arrived(self, clock_s: float) -> None:
        if not self.emergency_event or self._emergency_status == "destination_waiting":
            return
        self._emergency_destination_arrived_at_s = float(clock_s)
        self._emergency_status = "destination_waiting"
        self._record_emergency_lifecycle(
            clock_s,
            "destination_arrived",
            approach=self.emergency_event.get("destination_approach"),
        )

    def _mark_emergency_cleared(self, clock_s: float) -> None:
        if not self.emergency_event or self._emergency_status == "cleared":
            return
        self._emergency_cleared_at_s = float(clock_s)
        self._emergency_status = "cleared"
        self._record_emergency_lifecycle(clock_s, "cleared", recovery="normal protected control resumed")
        self._record_emergency_lifecycle(clock_s, "recovery", recovery="priority context removed")
        self._latest_emergency_priority = {
            "active": False,
            "status": self._emergency_status,
            "action": "recovery",
            "decision": "grant",
            "reason": "simulated emergency vehicle cleared the downstream intersection; normal protected control resumes",
        }

    def _emergency_priority_context(self, clock_s: float) -> tuple[_IntersectionRuntime | None, str, float | None]:
        if not self.emergency_event:
            return None, "inactive", None
        vehicle_id = str(self.emergency_event.get("vehicle_id") or "")
        if self._emergency_status == "source_waiting":
            return self.source, "source_priority", 0.0
        if self._emergency_status == "in_transit":
            transfer = next((item for item in self.pipeline if item.vehicle.vehicle_id == vehicle_id), None)
            if transfer is None:
                return None, "in_transit", None
            eta = max(0.0, float(transfer.arrive_at_s) - float(clock_s))
            return self.destination, "downstream_preparation", eta
        if self._emergency_status == "destination_waiting":
            return self.destination, "destination_priority", 0.0
        return None, self._emergency_status, None

    def _evaluate_vehicle_class_priority(
        self,
        clock_s: float,
        runtime: _IntersectionRuntime,
        signal: dict[str, Any],
        *,
        role: str,
    ) -> None:
        if self.mode not in CLASS_AWARE_MODES or not self.vehicle_class_priority_enabled:
            return
        self.vehicle_class_priority_evaluations += 1
        context = runtime.vehicle_class_context(self.vehicle_class_priority_class, clock_s)
        if int(context["waiting_count"]) < self.vehicle_class_priority_min_waiting:
            self._latest_vehicle_class_priority[role] = {
                "active": True,
                "class_name": self.vehicle_class_priority_class,
                "waiting_count": int(context["waiting_count"]),
                "oldest_wait_seconds": round(float(context["oldest_wait_seconds"]), 1),
                "priority_weight": self.vehicle_class_priority_weight,
                "weighted_waiting": round(int(context["waiting_count"]) * self.vehicle_class_priority_weight, 2),
                "action": "below_min_waiting",
                "applied": False,
                "reason": "configured class count is below the class-priority minimum waiting threshold",
            }
            return
        self.vehicle_class_priority_triggered += 1
        outcome = runtime.apply_vehicle_class_priority(
            clock_s=clock_s,
            class_name=self.vehicle_class_priority_class,
            priority_weight=self.vehicle_class_priority_weight,
            max_extension_seconds=self.vehicle_class_priority_max_extension_seconds,
        )
        event = {
            "vehicle_class_priority_id": f"classprio_{runtime.intersection_id}_{int(round(clock_s * 1000.0))}",
            "t": round(clock_s, 1),
            "role": role,
            "intersection_id": runtime.intersection_id,
            "class_name": self.vehicle_class_priority_class,
            "waiting_count": int(context["waiting_count"]),
            "oldest_wait_seconds": round(float(context["oldest_wait_seconds"]), 1),
            "priority_weight": round(self.vehicle_class_priority_weight, 2),
            "weighted_waiting": round(int(context["waiting_count"]) * self.vehicle_class_priority_weight, 2),
            "min_waiting": self.vehicle_class_priority_min_waiting,
            "provenance": "synthetic_vehicle_class_demand",
            "phase_before": signal.get("phase"),
            "phase_key_before": signal.get("phase_key"),
            "action": outcome.get("action", "none"),
            "applied": bool(outcome.get("applied")),
            "reason": outcome.get("reason"),
            "timing_delta_seconds": float(outcome.get("timing_delta_seconds", 0.0) or 0.0),
        }
        self._latest_vehicle_class_priority[role] = {"active": True, **event}
        self.vehicle_class_priority_events.append(event)
        if event["action"] == "protect_pedestrian_service":
            self.vehicle_class_priority_pedestrian_protections += 1
        if event["applied"]:
            self.vehicle_class_priority_applied += 1
            delta = event["timing_delta_seconds"]
            if delta > 0:
                self.vehicle_class_priority_seconds_added += delta
            elif delta < 0:
                self.vehicle_class_priority_seconds_reduced += abs(delta)


    def _evaluate_emergency_priority(
        self,
        clock_s: float,
        source_signal: dict[str, Any],
        destination_signal: dict[str, Any],
    ) -> None:
        if self.mode not in EMERGENCY_PRIORITY_MODES or not self.emergency_event:
            return
        runtime, role, eta = self._emergency_priority_context(clock_s)
        if runtime is None:
            return
        if role == "downstream_preparation" and eta is not None and eta > self.emergency_priority_lookahead_seconds + 1e-9:
            self._latest_emergency_priority = {
                "active": True,
                "status": self._emergency_status,
                "role": role,
                "decision": "defer",
                "action": "outside_priority_lookahead",
                "eta_seconds": round(eta, 1),
                "reason": "simulated emergency vehicle has not yet entered the configured downstream priority lookahead",
            }
            return

        self.emergency_priority_evaluations += 1
        signal = source_signal if runtime is self.source else destination_signal
        outcome = runtime.apply_emergency_priority(
            clock_s=clock_s,
            emergency_event=self.emergency_event,
            role=role,
            eta_seconds=eta,
            lookahead_seconds=self.emergency_priority_lookahead_seconds,
            max_extension_seconds=self.emergency_priority_max_extension_seconds,
            link_id=str(self.link.get("id") or "link"),
        )
        event = {
            "emergency_priority_id": f"emgprio_{runtime.intersection_id}_{int(round(clock_s * 1000.0))}",
            "emergency_event_id": str(self.emergency_event.get("event_id") or "emergency"),
            "t": round(clock_s, 1),
            "role": role,
            "intersection_id": runtime.intersection_id,
            "link_id": str(self.link.get("id") or "link"),
            "vehicle_type": self.emergency_event.get("vehicle_type"),
            "provenance": "simulated_configured_emergency_event",
            "phase_before": signal.get("phase"),
            "phase_key_before": signal.get("phase_key"),
            "eta_seconds": round(float(eta), 1) if eta is not None else None,
            "decision": outcome.get("decision", "defer"),
            "action": outcome.get("action", "none"),
            "applied": bool(outcome.get("applied")),
            "reason": outcome.get("reason"),
            "timing_delta_seconds": float(outcome.get("timing_delta_seconds", 0.0) or 0.0),
        }
        self._latest_emergency_priority = {"active": True, "status": self._emergency_status, **event}
        self.emergency_priority_events.append(event)
        if event["decision"] == "grant":
            self.emergency_priority_grants += 1
        elif event["decision"] == "deny":
            self.emergency_priority_denials += 1
        if role == "downstream_preparation":
            self.emergency_downstream_preparations += 1
        if event["applied"]:
            self.emergency_priority_applied += 1
            delta = event["timing_delta_seconds"]
            if delta > 0:
                self.emergency_priority_seconds_added += delta
            elif delta < 0:
                self.emergency_priority_seconds_reduced += abs(delta)

    def _inject_arrivals(self, clock_s: float) -> None:
        while (
            self._source_vehicle_index < len(self.source_vehicle_arrivals)
            and self.source_vehicle_arrivals[self._source_vehicle_index].at_s <= clock_s + 1e-9
        ):
            self.source.enqueue_external_vehicle(self.source_vehicle_arrivals[self._source_vehicle_index])
            self._source_vehicle_index += 1
        while (
            self._destination_vehicle_index < len(self.destination_vehicle_arrivals)
            and self.destination_vehicle_arrivals[self._destination_vehicle_index].at_s <= clock_s + 1e-9
        ):
            self.destination.enqueue_external_vehicle(self.destination_vehicle_arrivals[self._destination_vehicle_index])
            self._destination_vehicle_index += 1
        while (
            self._source_pedestrian_index < len(self.source_pedestrian_arrivals)
            and self.source_pedestrian_arrivals[self._source_pedestrian_index].at_s <= clock_s + 1e-9
        ):
            self.source.enqueue_pedestrian(self.source_pedestrian_arrivals[self._source_pedestrian_index])
            self._source_pedestrian_index += 1
        while (
            self._destination_pedestrian_index < len(self.destination_pedestrian_arrivals)
            and self.destination_pedestrian_arrivals[self._destination_pedestrian_index].at_s <= clock_s + 1e-9
        ):
            self.destination.enqueue_pedestrian(self.destination_pedestrian_arrivals[self._destination_pedestrian_index])
            self._destination_pedestrian_index += 1

    def _deliver_transfers(self, clock_s: float) -> None:
        if not self.pipeline:
            return
        due = [transfer for transfer in self.pipeline if transfer.arrive_at_s <= clock_s + 1e-9]
        if not due:
            return
        self.pipeline = [transfer for transfer in self.pipeline if transfer.arrive_at_s > clock_s + 1e-9]
        for transfer in sorted(due, key=lambda item: (item.arrive_at_s, item.vehicle.vehicle_id)):
            self.destination.enqueue_transfer(transfer)
            self.transfers_arrived += 1
            if self._is_emergency_vehicle(transfer.vehicle.vehicle_id):
                self._mark_emergency_destination_arrived(transfer.arrive_at_s)
            event = self.transfer_events.get(transfer.vehicle.vehicle_id)
            if event is not None:
                event["arrived_at_s"] = round(transfer.arrive_at_s, 1)

    def _append_timeline(
        self,
        clock_s: float,
        source_signal: dict[str, Any],
        destination_signal: dict[str, Any],
    ) -> None:
        self.timeline.append(
            {
                "t": round(min(clock_s, float(self.duration_seconds)), 1),
                "source": {
                    "intersection_id": self.source.intersection_id,
                    "phase": source_signal.get("phase"),
                    "phase_key": source_signal.get("phase_key"),
                    "vehicle_queue": len(self.source.vehicle_queue),
                    "pedestrian_queue": len(self.source.pedestrian_queue),
                    "pedestrians_crossing": len(self.source.pedestrian_crossing_clear_times),
                    "vehicles_served": self.source.vehicles_served,
                    "active_rules": list(source_signal.get("active_rules", [])),
                },
                "destination": {
                    "intersection_id": self.destination.intersection_id,
                    "phase": destination_signal.get("phase"),
                    "phase_key": destination_signal.get("phase_key"),
                    "vehicle_queue": len(self.destination.vehicle_queue),
                    "pedestrian_queue": len(self.destination.pedestrian_queue),
                    "pedestrians_crossing": len(self.destination.pedestrian_crossing_clear_times),
                    "vehicles_served": self.destination.vehicles_served,
                    "active_rules": list(destination_signal.get("active_rules", [])),
                },
                "pipeline_count": len(self.pipeline),
                "transfers_departed": self.transfers_departed,
                "transfers_arrived": self.transfers_arrived,
                "corridor_completed": self.corridor_completed,
                "coordination": deepcopy(self._latest_coordination) if self.mode in COOPERATIVE_MODES else None,
                "pedestrian_awareness": (
                    deepcopy(self._latest_pedestrian_awareness) if self.mode in PEDESTRIAN_AWARE_MODES else None
                ),
                "vehicle_class_priority": (
                    deepcopy(self._latest_vehicle_class_priority) if self.mode in CLASS_AWARE_MODES else None
                ),
                "emergency_priority": (
                    deepcopy(self._latest_emergency_priority) if self.mode in EMERGENCY_EVENT_MODES else None
                ),
            }
        )

    def _build_result(
        self,
        last_source_signal: dict[str, Any] | None,
        last_destination_signal: dict[str, Any] | None,
    ) -> dict[str, Any]:
        duration_minutes = self.duration_seconds / 60.0
        source_result = self.source.result(self.duration_seconds, last_source_signal)
        destination_result = self.destination.result(self.duration_seconds, last_destination_signal)
        total_queue_samples = [
            source + destination
            for source, destination in zip(self.source.vehicle_queue_samples, self.destination.vehicle_queue_samples)
        ]
        total_vehicle_wait = sum(self.source.vehicle_waits) + sum(self.destination.vehicle_waits)
        total_pedestrian_wait = sum(self.source.pedestrian_waits) + sum(self.destination.pedestrian_waits)
        total_pedestrian_queue_samples = [
            source + destination
            for source, destination in zip(self.source.pedestrian_queue_samples, self.destination.pedestrian_queue_samples)
        ]
        emergency_active_at = float(self.emergency_event.get("active_at_s", 0.0)) if self.emergency_event else None
        emergency_source_wait = (
            max(0.0, self._emergency_source_departed_at_s - emergency_active_at)
            if emergency_active_at is not None and self._emergency_source_departed_at_s is not None
            else None
        )
        emergency_destination_wait = (
            max(0.0, self._emergency_cleared_at_s - self._emergency_destination_arrived_at_s)
            if self._emergency_cleared_at_s is not None and self._emergency_destination_arrived_at_s is not None
            else None
        )
        emergency_total_travel = (
            max(0.0, self._emergency_cleared_at_s - emergency_active_at)
            if emergency_active_at is not None and self._emergency_cleared_at_s is not None
            else None
        )
        return {
            "mode": self.mode,
            "intersections": {
                self.source.intersection_id: source_result,
                self.destination.intersection_id: destination_result,
            },
            "network_metrics": {
                "transfers_departed": self.transfers_departed,
                "transfers_arrived": self.transfers_arrived,
                "configured_link_travel_time_seconds": float(self.link["travel_time_seconds"]),
                "transfer_pipeline_average": round(sum(self.pipeline_samples) / len(self.pipeline_samples), 2)
                if self.pipeline_samples
                else 0.0,
                "transfer_pipeline_peak": max(self.pipeline_samples, default=0),
                "corridor_completed": self.corridor_completed,
                "corridor_completed_per_minute": round(self.corridor_completed / duration_minutes, 2)
                if duration_minutes
                else 0.0,
                "corridor_travel_time": _distribution(self.corridor_travel_times),
                "total_vehicle_wait_seconds": round(total_vehicle_wait, 2),
                "total_vehicle_queue_average": round(sum(total_queue_samples) / len(total_queue_samples), 2)
                if total_queue_samples
                else 0.0,
                "total_vehicle_queue_p95": round(_percentile(total_queue_samples, 0.95), 2),
                "total_vehicle_queue_peak": max(total_queue_samples, default=0),
                "total_pedestrian_wait_seconds": round(total_pedestrian_wait, 2),
                "total_pedestrian_queue_average": (
                    round(sum(total_pedestrian_queue_samples) / len(total_pedestrian_queue_samples), 2)
                    if total_pedestrian_queue_samples
                    else 0.0
                ),
                "total_pedestrian_queue_p95": round(_percentile(total_pedestrian_queue_samples, 0.95), 2),
                "total_pedestrian_queue_peak": max(total_pedestrian_queue_samples, default=0),
                "max_observed_pedestrian_wait_seconds": round(
                    max(self.source.max_observed_pedestrian_wait_seconds, self.destination.max_observed_pedestrian_wait_seconds), 2
                ),
                "vehicle_classes": _network_vehicle_class_metrics(self.source, self.destination),
                "pedestrian_awareness": {
                    "evaluations": self.pedestrian_awareness_evaluations,
                    "applied": self.pedestrian_awareness_applied,
                    "starvation_preventions": self.pedestrian_starvation_preventions,
                    "crossing_clearance_extensions": self.pedestrian_clearance_extensions,
                    "timing_seconds_added": round(self.pedestrian_awareness_seconds_added, 1),
                    "timing_seconds_reduced": round(self.pedestrian_awareness_seconds_reduced, 1),
                    "max_wait_seconds": self.pedestrian_max_wait_seconds,
                    "crossing_clearance_seconds": self.pedestrian_crossing_clearance_seconds,
                    "clearance_reserve_seconds": self.pedestrian_clearance_reserve_seconds,
                },
                "coordination": {
                    "evaluations": self.coordination_evaluations,
                    "triggered": self.coordination_triggered,
                    "applied": self.coordination_applied,
                    "green_extensions": self.coordination_green_extensions,
                    "protected_progression_requests": self.coordination_progression_requests,
                    "pedestrian_service_protections": self.coordination_pedestrian_protections,
                    "timing_seconds_added": round(self.coordination_seconds_added, 1),
                    "timing_seconds_reduced": round(self.coordination_seconds_reduced, 1),
                    "lookahead_seconds": self.cooperation_lookahead_seconds,
                    "max_extension_seconds": self.cooperation_max_extension_seconds,
                    "min_incoming_vehicles": self.cooperation_min_incoming_vehicles,
                },
                "emergency": {
                    "event_present": self.emergency_event is not None,
                    "status": self._emergency_status,
                    "vehicle_type": self.emergency_event.get("vehicle_type") if self.emergency_event else None,
                    "source_wait_seconds": round(emergency_source_wait, 2) if emergency_source_wait is not None else None,
                    "destination_wait_seconds": round(emergency_destination_wait, 2) if emergency_destination_wait is not None else None,
                    "total_travel_seconds": round(emergency_total_travel, 2) if emergency_total_travel is not None else None,
                    "completed": self._emergency_status == "cleared",
                    "priority_evaluations": self.emergency_priority_evaluations,
                    "priority_grants": self.emergency_priority_grants,
                    "priority_denials": self.emergency_priority_denials,
                    "priority_timing_applied": self.emergency_priority_applied,
                    "downstream_preparations": self.emergency_downstream_preparations,
                    "timing_seconds_added": round(self.emergency_priority_seconds_added, 1),
                    "timing_seconds_reduced": round(self.emergency_priority_seconds_reduced, 1),
                    "lookahead_seconds": self.emergency_priority_lookahead_seconds,
                    "max_extension_seconds": self.emergency_priority_max_extension_seconds,
                },
            },
            "timeline": self.timeline,
            "transfer_events": [self.transfer_events[key] for key in sorted(self.transfer_events)],
            "coordination_events": self.coordination_events,
            "pedestrian_awareness_events": self.pedestrian_awareness_events,
            "vehicle_class_priority_events": self.vehicle_class_priority_events,
            "vehicle_class_priority_metrics": {
                "evaluations": self.vehicle_class_priority_evaluations,
                "triggered": self.vehicle_class_priority_triggered,
                "applied": self.vehicle_class_priority_applied,
                "pedestrian_service_protections": self.vehicle_class_priority_pedestrian_protections,
                "seconds_added": round(self.vehicle_class_priority_seconds_added, 1),
                "seconds_reduced": round(self.vehicle_class_priority_seconds_reduced, 1),
                "configured_class": self.vehicle_class_priority_class,
                "configured_weight": round(self.vehicle_class_priority_weight, 2),
            },
            "emergency_event": deepcopy(self.emergency_event) if self.emergency_event else None,
            "emergency_lifecycle_events": self.emergency_lifecycle_events,
            "emergency_priority_events": self.emergency_priority_events,
            "observation_provenance": "simulation",
            "transfer_provenance": "synthetic_network_simulation",
            "coordination_provenance": "synthetic_predicted_arrivals" if self.mode in COOPERATIVE_MODES else None,
            "pedestrian_awareness_provenance": (
                "synthetic_pedestrian_demand" if self.mode in PEDESTRIAN_AWARE_MODES else None
            ),
            "vehicle_class_provenance": "synthetic_vehicle_class_demand",
            "vehicle_class_priority_provenance": (
                "synthetic_vehicle_class_demand" if self.mode in CLASS_AWARE_MODES else None
            ),
            "emergency_event_provenance": (
                "simulated_configured_emergency_event" if self.mode in EMERGENCY_EVENT_MODES else None
            ),
            "cooperative_control_active": self.mode in COOPERATIVE_MODES,
            "pedestrian_aware_control_active": self.mode in PEDESTRIAN_AWARE_MODES,
            "vehicle_class_aware_control_active": self.mode in CLASS_AWARE_MODES and self.vehicle_class_priority_enabled,
            "emergency_event_active": self.mode in EMERGENCY_EVENT_MODES and self.emergency_event is not None,
            "emergency_priority_active": self.mode in EMERGENCY_PRIORITY_MODES and self.emergency_event is not None,
            "scope_note": (
                "Two-intersection emergency-priority cooperative simulation using an explicit simulated/configured emergency event, bounded protected timing, pedestrian crossing guards, and downstream preparation."
                if self.mode in EMERGENCY_PRIORITY_MODES
                else (
                    "Matched emergency-event baseline using the same simulated emergency vehicle without emergency timing priority."
                    if self.mode in EMERGENCY_EVENT_MODES
                    else (
                        "Two-intersection class-aware cooperative simulation with bounded configured regular vehicle-class priority plus pedestrian protections and synthetic predicted-arrival coordination."
                        if self.mode in CLASS_AWARE_MODES
                        else (
                            "Two-intersection pedestrian-aware cooperative simulation with bounded local pedestrian service/clearance guards plus synthetic predicted-arrival coordination."
                            if self.mode in PEDESTRIAN_AWARE_MODES
                            else (
                                "Two-intersection cooperative simulation using predicted synthetic upstream arrivals and bounded protected timing advisories."
                                if self.mode in COOPERATIVE_MODES
                                else "Two-intersection independent-controller simulation baseline; neighbour context does not alter timing in this mode."
                            )
                        )
                    )
                )
            ),
        }


class NetworkSimulationExperimentService:
    """Run/persist deterministic network comparisons with bounded synthetic policy layers."""

    def __init__(
        self,
        *,
        storage_root: Path | None = None,
        config_provider: Callable[[], dict[str, Any]] | None = None,
        network_provider: Callable[[], dict[str, Any]] | None = None,
        zones_provider: Callable[[], list[dict[str, Any]]] | None = None,
        controller_factory: Callable[[Path, Path], Any] | None = None,
    ) -> None:
        self._storage_root = (storage_root or DEFAULT_STORAGE_ROOT).expanduser().resolve()
        self._config_provider = config_provider or signal_rules_service.get_config
        self._network_provider = network_provider or intersection_network_service.get
        self._zones_provider = zones_provider or zone_service.zones
        self._controller_factory = controller_factory

    def run(
        self,
        *,
        duration_seconds: int,
        density: str,
        seed: int,
        sample_interval_seconds: int,
        profile: str | None,
        label: str = "",
        link_id: str | None = None,
        transfer_share_percent: int = 70,
        cooperation_lookahead_seconds: float = 12.0,
        cooperation_max_extension_seconds: float = 5.0,
        cooperation_min_incoming_vehicles: int = 1,
        pedestrian_max_wait_seconds: float = 30.0,
        pedestrian_crossing_clearance_seconds: float = 6.0,
        pedestrian_clearance_reserve_seconds: float = 3.0,
        vehicle_class_profile: str = "mixed_urban",
        vehicle_class_priority_enabled: bool = True,
        vehicle_class_priority_class: str = "bus",
        vehicle_class_priority_weight: float = 2.0,
        vehicle_class_priority_min_waiting: int = 1,
        vehicle_class_priority_max_extension_seconds: float = 4.0,
        emergency_event_enabled: bool = True,
        emergency_event_at_seconds: float = 15.0,
        emergency_vehicle_type: str = "ambulance",
        emergency_priority_lookahead_seconds: float = 20.0,
        emergency_priority_max_extension_seconds: float = 8.0,
    ) -> dict[str, Any]:
        density = density.strip().lower()
        if density not in DENSITIES:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "Experiment density must be light, normal, or busy.", status_code=422)
        if not 30 <= int(duration_seconds) <= 1800:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "Experiment duration must be between 30 and 1800 seconds.", status_code=422)
        if not 1 <= int(sample_interval_seconds) <= 10:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "Experiment sample interval must be between 1 and 10 seconds.", status_code=422)
        if not 0 <= int(transfer_share_percent) <= 100:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "transfer_share_percent must be between 0 and 100.", status_code=422)
        if not 1.0 <= float(cooperation_lookahead_seconds) <= 60.0:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "cooperation_lookahead_seconds must be between 1 and 60.", status_code=422)
        if not 0.0 <= float(cooperation_max_extension_seconds) <= 20.0:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "cooperation_max_extension_seconds must be between 0 and 20.", status_code=422)
        if not 1 <= int(cooperation_min_incoming_vehicles) <= 20:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "cooperation_min_incoming_vehicles must be between 1 and 20.", status_code=422)
        if not 5.0 <= float(pedestrian_max_wait_seconds) <= 180.0:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "pedestrian_max_wait_seconds must be between 5 and 180.", status_code=422)
        if not 2.0 <= float(pedestrian_crossing_clearance_seconds) <= 30.0:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "pedestrian_crossing_clearance_seconds must be between 2 and 30.", status_code=422)
        if not 1.0 <= float(pedestrian_clearance_reserve_seconds) <= 15.0:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "pedestrian_clearance_reserve_seconds must be between 1 and 15.", status_code=422)
        vehicle_class_profile = str(vehicle_class_profile).strip().lower()
        if vehicle_class_profile not in VEHICLE_CLASS_PROFILES:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "vehicle_class_profile must be legacy, mixed_urban, or freight_heavy.", status_code=422)
        vehicle_class_priority_class = _normalize_vehicle_class(vehicle_class_priority_class)
        if vehicle_class_priority_class not in REGULAR_VEHICLE_CLASSES:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "vehicle_class_priority_class must identify a regular supported vehicle class.", status_code=422)
        if not 1.0 <= float(vehicle_class_priority_weight) <= 5.0:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "vehicle_class_priority_weight must be between 1 and 5.", status_code=422)
        if not 1 <= int(vehicle_class_priority_min_waiting) <= 20:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "vehicle_class_priority_min_waiting must be between 1 and 20.", status_code=422)
        if not 0.0 <= float(vehicle_class_priority_max_extension_seconds) <= 20.0:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "vehicle_class_priority_max_extension_seconds must be between 0 and 20.", status_code=422)
        if emergency_event_enabled and not 0.0 <= float(emergency_event_at_seconds) < float(duration_seconds):
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "emergency_event_at_seconds must be within the experiment duration.", status_code=422)
        emergency_vehicle_type = str(emergency_vehicle_type).strip().lower()
        if emergency_vehicle_type not in EMERGENCY_VEHICLE_TYPES:
            raise AppError(
                ErrorCode.TRAFFIC_RULE_INVALID,
                "emergency_vehicle_type must be ambulance, fire_engine, or police.",
                status_code=422,
            )
        if not 1.0 <= float(emergency_priority_lookahead_seconds) <= 120.0:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "emergency_priority_lookahead_seconds must be between 1 and 120.", status_code=422)
        if not 0.0 <= float(emergency_priority_max_extension_seconds) <= 30.0:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "emergency_priority_max_extension_seconds must be between 0 and 30.", status_code=422)

        network = deepcopy(self._network_provider())
        link, source_intersection, destination_intersection = self._resolve_pair(network, link_id)
        policy = deepcopy(self._config_provider())
        zones = deepcopy(self._zones_provider())
        zone_types = {
            str(zone.get("id")): str(zone.get("type"))
            for zone in zones
            if isinstance(zone, dict) and zone.get("id") and zone.get("type")
        }
        arrivals = _arrival_plan(
            duration_seconds=int(duration_seconds),
            density=density,
            seed=int(seed),
            transfer_share_percent=int(transfer_share_percent),
            vehicle_class_profile=vehicle_class_profile,
        )
        emergency_event = (
            _emergency_event_plan(
                seed=int(seed),
                active_at_s=float(emergency_event_at_seconds),
                vehicle_type=emergency_vehicle_type,
                link=link,
                source_intersection=source_intersection,
                destination_intersection=destination_intersection,
            )
            if emergency_event_enabled
            else None
        )

        created_at_ms = int(time.time() * 1000)
        run_id = f"netexp_{created_at_ms}_{uuid.uuid4().hex[:8]}"
        with tempfile.TemporaryDirectory(prefix="aitl_network_experiment_") as temporary:
            temp_root = Path(temporary)

            def run_mode(mode: str) -> dict[str, Any]:
                return _NetworkModeSimulation(
                    mode=mode,
                    duration_seconds=int(duration_seconds),
                    sample_interval_seconds=int(sample_interval_seconds),
                    source_intersection=source_intersection,
                    destination_intersection=destination_intersection,
                    link=link,
                    policy_config=policy,
                    profile_override=profile,
                    zone_types=zone_types,
                    temp_root=temp_root,
                    controller_factory=self._controller_factory,
                    cooperation_lookahead_seconds=float(cooperation_lookahead_seconds),
                    cooperation_max_extension_seconds=float(cooperation_max_extension_seconds),
                    cooperation_min_incoming_vehicles=int(cooperation_min_incoming_vehicles),
                    pedestrian_max_wait_seconds=float(pedestrian_max_wait_seconds),
                    pedestrian_crossing_clearance_seconds=float(pedestrian_crossing_clearance_seconds),
                    pedestrian_clearance_reserve_seconds=float(pedestrian_clearance_reserve_seconds),
                    vehicle_class_priority_enabled=bool(vehicle_class_priority_enabled),
                    vehicle_class_priority_class=vehicle_class_priority_class,
                    vehicle_class_priority_weight=float(vehicle_class_priority_weight),
                    vehicle_class_priority_min_waiting=int(vehicle_class_priority_min_waiting),
                    vehicle_class_priority_max_extension_seconds=float(vehicle_class_priority_max_extension_seconds),
                    emergency_event=(deepcopy(emergency_event) if mode in EMERGENCY_EVENT_MODES else None),
                    emergency_priority_lookahead_seconds=float(emergency_priority_lookahead_seconds),
                    emergency_priority_max_extension_seconds=float(emergency_priority_max_extension_seconds),
                    **arrivals,
                ).run()

            fixed = run_mode("fixed")
            adaptive = run_mode("adaptive")
            cooperative = run_mode("cooperative")
            pedestrian_aware_cooperative = run_mode("pedestrian_aware_cooperative")
            class_aware_cooperative = run_mode("class_aware_cooperative")
            emergency_baseline_cooperative = run_mode("emergency_baseline_cooperative")
            emergency_priority_cooperative = run_mode("emergency_priority_cooperative")

        adaptive_vs_fixed = _network_comparison(fixed, adaptive)
        cooperative_vs_fixed = _network_comparison(
            fixed,
            cooperative,
            baseline_label="fixed",
            candidate_label="cooperative",
        )
        cooperative_vs_adaptive = _network_comparison(
            adaptive,
            cooperative,
            baseline_label="adaptive",
            candidate_label="cooperative",
        )
        pedestrian_aware_vs_cooperative = _network_comparison(
            cooperative,
            pedestrian_aware_cooperative,
            baseline_label="cooperative",
            candidate_label="pedestrian_aware_cooperative",
        )
        pedestrian_aware_vs_fixed = _network_comparison(
            fixed,
            pedestrian_aware_cooperative,
            baseline_label="fixed",
            candidate_label="pedestrian_aware_cooperative",
        )
        class_aware_vs_pedestrian_aware = _network_comparison(
            pedestrian_aware_cooperative,
            class_aware_cooperative,
            baseline_label="pedestrian_aware_cooperative",
            candidate_label="class_aware_cooperative",
        )
        class_aware_vs_pedestrian_aware["selected_class"] = _vehicle_class_comparison(
            pedestrian_aware_cooperative,
            class_aware_cooperative,
            vehicle_class_priority_class,
            baseline_label="pedestrian_aware_cooperative",
            candidate_label="class_aware_cooperative",
        )
        class_aware_vs_fixed = _network_comparison(
            fixed,
            class_aware_cooperative,
            baseline_label="fixed",
            candidate_label="class_aware_cooperative",
        )
        emergency_priority_vs_baseline = _network_comparison(
            emergency_baseline_cooperative,
            emergency_priority_cooperative,
            baseline_label="emergency_baseline_cooperative",
            candidate_label="emergency_priority_cooperative",
        )
        emergency_priority_vs_baseline["emergency"] = _emergency_comparison(
            emergency_baseline_cooperative,
            emergency_priority_cooperative,
        )
        result = {
            "run_id": run_id,
            "created_at_ms": created_at_ms,
            "label": label.strip(),
            "scenario": {
                "kind": "two_intersection_network",
                "duration_seconds": int(duration_seconds),
                "density": density,
                "seed": int(seed),
                "sample_interval_seconds": int(sample_interval_seconds),
                "profile_override": profile,
                "transfer_share_percent": int(transfer_share_percent),
                "pedestrian_awareness": {
                    "max_wait_seconds": float(pedestrian_max_wait_seconds),
                    "crossing_clearance_seconds": float(pedestrian_crossing_clearance_seconds),
                    "clearance_reserve_seconds": float(pedestrian_clearance_reserve_seconds),
                    "provenance": "synthetic_pedestrian_demand",
                },
                "vehicle_classes": {
                    "regular_taxonomy": list(REGULAR_VEHICLE_CLASSES),
                    "special_classes": list(SPECIAL_VEHICLE_CLASSES),
                    "unknown_fallback": "other",
                    "profile": vehicle_class_profile,
                    "mix": deepcopy(VEHICLE_CLASS_PROFILES[vehicle_class_profile]),
                    "provenance": "synthetic_vehicle_class_demand",
                },
                "vehicle_class_priority": {
                    "enabled": bool(vehicle_class_priority_enabled),
                    "class_name": vehicle_class_priority_class,
                    "priority_weight": float(vehicle_class_priority_weight),
                    "min_waiting": int(vehicle_class_priority_min_waiting),
                    "max_extension_seconds": float(vehicle_class_priority_max_extension_seconds),
                    "provenance": "synthetic_vehicle_class_demand",
                },
                "cooperation": {
                    "lookahead_seconds": float(cooperation_lookahead_seconds),
                    "max_extension_seconds": float(cooperation_max_extension_seconds),
                    "min_incoming_vehicles": int(cooperation_min_incoming_vehicles),
                    "service_buffer_seconds": COOPERATION_SERVICE_BUFFER_SECONDS,
                },
                "emergency_priority": {
                    "event_enabled": bool(emergency_event_enabled),
                    "event": deepcopy(emergency_event),
                    "lookahead_seconds": float(emergency_priority_lookahead_seconds),
                    "max_extension_seconds": float(emergency_priority_max_extension_seconds),
                    "service_buffer_seconds": EMERGENCY_SERVICE_BUFFER_SECONDS,
                    "event_provenance": "simulated_configured_emergency_event",
                    "detector_claimed": False,
                },
                "link": deepcopy(link),
                "source_intersection": _intersection_snapshot(source_intersection),
                "destination_intersection": _intersection_snapshot(destination_intersection),
                "comparison": [
                    "fixed",
                    "adaptive",
                    "cooperative",
                    "pedestrian_aware_cooperative",
                    "class_aware_cooperative",
                    "emergency_baseline_cooperative",
                    "emergency_priority_cooperative",
                ],
                "arrival_plan": _arrival_plan_snapshot(arrivals),
                "cooperative_control_active": True,
                "pedestrian_aware_control_active": True,
                "vehicle_class_aware_control_active": bool(vehicle_class_priority_enabled),
                "emergency_priority_active": bool(emergency_event_enabled),
            },
            "fixed": fixed,
            "adaptive": adaptive,
            "cooperative": cooperative,
            "pedestrian_aware_cooperative": pedestrian_aware_cooperative,
            "class_aware_cooperative": class_aware_cooperative,
            "emergency_baseline_cooperative": emergency_baseline_cooperative,
            "emergency_priority_cooperative": emergency_priority_cooperative,
            "comparison": adaptive_vs_fixed,
            "comparisons": {
                "adaptive_vs_fixed": adaptive_vs_fixed,
                "cooperative_vs_fixed": cooperative_vs_fixed,
                "cooperative_vs_adaptive": cooperative_vs_adaptive,
                "pedestrian_aware_cooperative_vs_cooperative": pedestrian_aware_vs_cooperative,
                "pedestrian_aware_cooperative_vs_fixed": pedestrian_aware_vs_fixed,
                "class_aware_cooperative_vs_pedestrian_aware_cooperative": class_aware_vs_pedestrian_aware,
                "class_aware_cooperative_vs_fixed": class_aware_vs_fixed,
                "emergency_priority_vs_emergency_baseline": emergency_priority_vs_baseline,
            },
            "prototype_only": True,
            "scope_note": (
                "Controlled local two-intersection simulation benchmark only. V031 preserves the V030 class-aware/cooperation/pedestrian/emergency "
                "policy stack and adds persistent normalized decision evidence without adding another control mode. Synthetic class/emergency/network "
                "context is not presented as live AI detection, and no physical/public-road control is enabled."
            ),
        }
        result["decision_evidence"] = build_network_decision_evidence(result)
        self._write_run(result)
        self._trim_old_runs()
        return result

    def evidence(self, run_id: str) -> dict[str, Any]:
        result = self.get(run_id)
        evidence = result.get("decision_evidence")
        if isinstance(evidence, dict) and int(evidence.get("schema_version", 0) or 0) == 1:
            return evidence
        return build_network_decision_evidence(result)

    def export_evidence_csv(self, run_id: str) -> str:
        return export_network_decision_evidence_csv(self.evidence(run_id))

    def list(self, limit: int = 50) -> dict[str, Any]:
        limit = max(1, min(int(limit), 100))
        try:
            paths = (
                sorted(self._storage_root.glob("netexp_*.json"), key=lambda path: path.stat().st_mtime_ns, reverse=True)
                if self._storage_root.is_dir()
                else []
            )
            items: list[dict[str, Any]] = []
            for path in paths[:limit]:
                try:
                    payload = read_json(path)
                except (OSError, json.JSONDecodeError, TypeError):
                    continue
                if isinstance(payload, dict):
                    items.append(self._summary(payload))
        except OSError as exc:
            raise AppError(ErrorCode.TRAFFIC_EXPERIMENT_READ_FAILED, status_code=500) from exc
        return {
            "experiments": items,
            "total": len(paths),
            "storage_path": self._relative_storage_root(),
            "prototype_only": True,
            "cooperative_control_active": True,
            "pedestrian_aware_control_active": True,
            "emergency_priority_active": True,
        }

    def get(self, run_id: str) -> dict[str, Any]:
        path = self._run_path(run_id)
        if not path.is_file():
            raise AppError(
                ErrorCode.TRAFFIC_EXPERIMENT_READ_FAILED,
                "Network simulation experiment was not found.",
                status_code=404,
                details={"run_id": run_id},
            )
        try:
            payload = read_json(path)
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            raise AppError(
                ErrorCode.TRAFFIC_EXPERIMENT_READ_FAILED,
                status_code=500,
                details={"run_id": run_id},
            ) from exc
        if not isinstance(payload, dict):
            raise AppError(
                ErrorCode.TRAFFIC_EXPERIMENT_READ_FAILED,
                "Stored network simulation experiment is invalid.",
                status_code=500,
                details={"run_id": run_id},
            )
        return payload

    def delete(self, run_id: str) -> dict[str, Any]:
        path = self._run_path(run_id)
        if not path.exists():
            raise AppError(
                ErrorCode.TRAFFIC_EXPERIMENT_READ_FAILED,
                "Network simulation experiment was not found.",
                status_code=404,
                details={"run_id": run_id},
            )
        try:
            path.unlink()
        except OSError as exc:
            raise AppError(
                ErrorCode.TRAFFIC_EXPERIMENT_DELETE_FAILED,
                status_code=500,
                details={"run_id": run_id},
            ) from exc
        return {"deleted": True, "run_id": run_id}

    def export_csv(self, run_id: str) -> str:
        result = self.get(run_id)
        timelines = {mode: result.get(mode, {}).get("timeline", []) for mode in NETWORK_EXPERIMENT_MODES}
        rows = max((len(items) for items in timelines.values()), default=0)
        output = StringIO()
        writer = csv.writer(output, lineterminator="\n")
        header = ["t_seconds"]
        for mode in NETWORK_EXPERIMENT_MODES:
            header.extend(
                [
                    f"{mode}_source_phase",
                    f"{mode}_source_vehicle_queue",
                    f"{mode}_source_pedestrian_queue",
                    f"{mode}_source_vehicles_served",
                    f"{mode}_source_active_rules",
                    f"{mode}_destination_phase",
                    f"{mode}_destination_vehicle_queue",
                    f"{mode}_destination_pedestrian_queue",
                    f"{mode}_destination_vehicles_served",
                    f"{mode}_destination_active_rules",
                    f"{mode}_pipeline_count",
                    f"{mode}_transfers_departed",
                    f"{mode}_transfers_arrived",
                    f"{mode}_corridor_completed",
                    f"{mode}_coordination_action",
                    f"{mode}_coordination_incoming_vehicle_count",
                    f"{mode}_coordination_eta_seconds",
                    f"{mode}_coordination_applied",
                    f"{mode}_pedestrian_awareness_source_action",
                    f"{mode}_pedestrian_awareness_source_oldest_wait_seconds",
                    f"{mode}_pedestrian_awareness_source_crossing_count",
                    f"{mode}_pedestrian_awareness_source_applied",
                    f"{mode}_pedestrian_awareness_destination_action",
                    f"{mode}_pedestrian_awareness_destination_oldest_wait_seconds",
                    f"{mode}_pedestrian_awareness_destination_crossing_count",
                    f"{mode}_pedestrian_awareness_destination_applied",
                    f"{mode}_vehicle_class_priority_source_action",
                    f"{mode}_vehicle_class_priority_source_class",
                    f"{mode}_vehicle_class_priority_source_waiting_count",
                    f"{mode}_vehicle_class_priority_source_weighted_waiting",
                    f"{mode}_vehicle_class_priority_source_applied",
                    f"{mode}_vehicle_class_priority_destination_action",
                    f"{mode}_vehicle_class_priority_destination_class",
                    f"{mode}_vehicle_class_priority_destination_waiting_count",
                    f"{mode}_vehicle_class_priority_destination_weighted_waiting",
                    f"{mode}_vehicle_class_priority_destination_applied",
                    f"{mode}_emergency_status",
                    f"{mode}_emergency_role",
                    f"{mode}_emergency_decision",
                    f"{mode}_emergency_action",
                    f"{mode}_emergency_eta_seconds",
                    f"{mode}_emergency_applied",
                ]
            )
        writer.writerow(header)
        for index in range(rows):
            samples = {
                mode: timelines[mode][index] if index < len(timelines[mode]) else {}
                for mode in timelines
            }
            t_value = next((sample.get("t") for sample in samples.values() if sample.get("t") is not None), "")
            row: list[Any] = [t_value]
            for mode in NETWORK_EXPERIMENT_MODES:
                sample = samples[mode]
                source = sample.get("source", {})
                destination = sample.get("destination", {})
                coordination = sample.get("coordination") if isinstance(sample.get("coordination"), dict) else {}
                pedestrian_awareness = sample.get("pedestrian_awareness") if isinstance(sample.get("pedestrian_awareness"), dict) else {}
                ped_source = pedestrian_awareness.get("source") if isinstance(pedestrian_awareness.get("source"), dict) else {}
                ped_destination = pedestrian_awareness.get("destination") if isinstance(pedestrian_awareness.get("destination"), dict) else {}
                class_priority = sample.get("vehicle_class_priority") if isinstance(sample.get("vehicle_class_priority"), dict) else {}
                class_source = class_priority.get("source") if isinstance(class_priority.get("source"), dict) else {}
                class_destination = class_priority.get("destination") if isinstance(class_priority.get("destination"), dict) else {}
                emergency_priority = sample.get("emergency_priority") if isinstance(sample.get("emergency_priority"), dict) else {}
                row.extend(
                    [
                        source.get("phase", ""),
                        source.get("vehicle_queue", ""),
                        source.get("pedestrian_queue", ""),
                        source.get("vehicles_served", ""),
                        "|".join(source.get("active_rules", [])),
                        destination.get("phase", ""),
                        destination.get("vehicle_queue", ""),
                        destination.get("pedestrian_queue", ""),
                        destination.get("vehicles_served", ""),
                        "|".join(destination.get("active_rules", [])),
                        sample.get("pipeline_count", ""),
                        sample.get("transfers_departed", ""),
                        sample.get("transfers_arrived", ""),
                        sample.get("corridor_completed", ""),
                        coordination.get("action", ""),
                        coordination.get("incoming_vehicle_count", ""),
                        coordination.get("earliest_arrival_eta_seconds", ""),
                        coordination.get("applied", ""),
                        ped_source.get("action", ""),
                        ped_source.get("oldest_wait_seconds", ""),
                        ped_source.get("crossing_count", ""),
                        ped_source.get("applied", ""),
                        ped_destination.get("action", ""),
                        ped_destination.get("oldest_wait_seconds", ""),
                        ped_destination.get("crossing_count", ""),
                        ped_destination.get("applied", ""),
                        class_source.get("action", ""),
                        class_source.get("class_name", ""),
                        class_source.get("waiting_count", ""),
                        class_source.get("weighted_waiting", ""),
                        class_source.get("applied", ""),
                        class_destination.get("action", ""),
                        class_destination.get("class_name", ""),
                        class_destination.get("waiting_count", ""),
                        class_destination.get("weighted_waiting", ""),
                        class_destination.get("applied", ""),
                        emergency_priority.get("status", ""),
                        emergency_priority.get("role", ""),
                        emergency_priority.get("decision", ""),
                        emergency_priority.get("action", ""),
                        emergency_priority.get("eta_seconds", ""),
                        emergency_priority.get("applied", ""),
                    ]
                )
            writer.writerow(row)
        return output.getvalue()

    @staticmethod
    def _resolve_pair(
        network: dict[str, Any], link_id: str | None
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        intersections = {
            str(item.get("id")): item
            for item in network.get("intersections", [])
            if isinstance(item, dict) and item.get("id")
        }
        enabled_links = [
            item
            for item in network.get("links", [])
            if isinstance(item, dict) and bool(item.get("enabled", True))
        ]
        if link_id is not None:
            enabled_links = [item for item in enabled_links if str(item.get("id")) == link_id]
        enabled_links.sort(key=lambda item: str(item.get("id")))
        if not enabled_links:
            raise AppError(
                ErrorCode.TRAFFIC_NETWORK_INVALID,
                "Network experiment requires an enabled directed intersection link.",
                status_code=422,
                details={"link_id": link_id},
            )
        link = deepcopy(enabled_links[0])
        source = intersections.get(str(link.get("source_intersection_id")))
        destination = intersections.get(str(link.get("destination_intersection_id")))
        if source is None or destination is None or not source.get("enabled", True) or not destination.get("enabled", True):
            raise AppError(
                ErrorCode.TRAFFIC_NETWORK_INVALID,
                "Network experiment link must connect two enabled configured intersections.",
                status_code=422,
                details={"link_id": link.get("id")},
            )
        return link, deepcopy(source), deepcopy(destination)

    def _write_run(self, result: dict[str, Any]) -> None:
        try:
            write_json_atomic(self._run_path(str(result["run_id"])), result)
        except (OSError, TypeError, ValueError) as exc:
            logger.exception("Network simulation experiment write failed")
            raise AppError(ErrorCode.TRAFFIC_EXPERIMENT_WRITE_FAILED, status_code=500) from exc

    def _trim_old_runs(self) -> None:
        try:
            paths = sorted(self._storage_root.glob("netexp_*.json"), key=lambda path: path.stat().st_mtime_ns, reverse=True)
            for path in paths[MAX_STORED_RUNS:]:
                path.unlink(missing_ok=True)
        except OSError:
            logger.warning("Network simulation experiment retention cleanup failed", exc_info=True)

    def _run_path(self, run_id: str) -> Path:
        if not RUN_ID_PATTERN.fullmatch(run_id):
            raise AppError(
                ErrorCode.TRAFFIC_EXPERIMENT_READ_FAILED,
                "Network simulation experiment id is invalid.",
                status_code=422,
                details={"run_id": run_id},
            )
        return self._storage_root / f"{run_id}.json"

    def _relative_storage_root(self) -> str:
        try:
            return str(self._storage_root.relative_to(PROJECT_ROOT)).replace("\\", "/")
        except ValueError:
            return str(self._storage_root)

    @staticmethod
    def _summary(payload: dict[str, Any]) -> dict[str, Any]:
        scenario = payload.get("scenario") if isinstance(payload.get("scenario"), dict) else {}
        comparison = payload.get("comparison") if isinstance(payload.get("comparison"), dict) else {}
        comparisons = payload.get("comparisons") if isinstance(payload.get("comparisons"), dict) else {}
        cooperation = comparisons.get("cooperative_vs_adaptive") if isinstance(comparisons.get("cooperative_vs_adaptive"), dict) else {}
        pedestrian_awareness = comparisons.get("pedestrian_aware_cooperative_vs_cooperative") if isinstance(
            comparisons.get("pedestrian_aware_cooperative_vs_cooperative"), dict
        ) else {}
        vehicle_class_priority = comparisons.get("class_aware_cooperative_vs_pedestrian_aware_cooperative") if isinstance(
            comparisons.get("class_aware_cooperative_vs_pedestrian_aware_cooperative"), dict
        ) else {}
        emergency_priority = comparisons.get("emergency_priority_vs_emergency_baseline") if isinstance(
            comparisons.get("emergency_priority_vs_emergency_baseline"), dict
        ) else {}
        emergency_metrics = emergency_priority.get("emergency") if isinstance(emergency_priority.get("emergency"), dict) else {}
        return {
            "run_id": payload.get("run_id"),
            "created_at_ms": payload.get("created_at_ms"),
            "label": payload.get("label", ""),
            "scenario": scenario,
            "decision_evidence": {
                "schema_version": (payload.get("decision_evidence") or {}).get("schema_version")
                if isinstance(payload.get("decision_evidence"), dict)
                else None,
                "record_count": (payload.get("decision_evidence") or {}).get("record_count")
                if isinstance(payload.get("decision_evidence"), dict)
                else None,
                "applied_count": (payload.get("decision_evidence") or {}).get("applied_count")
                if isinstance(payload.get("decision_evidence"), dict)
                else None,
            },
            "headline": {
                "adaptive_vs_fixed_corridor_completed": comparison.get("corridor_completed"),
                "adaptive_vs_fixed_total_vehicle_wait": comparison.get("total_vehicle_wait"),
                "cooperative_vs_adaptive_corridor_completed": cooperation.get("corridor_completed"),
                "cooperative_vs_adaptive_corridor_travel_average": cooperation.get("corridor_travel_average"),
                "cooperative_vs_adaptive_total_vehicle_wait": cooperation.get("total_vehicle_wait"),
                "cooperative_vs_adaptive_total_vehicle_queue_average": cooperation.get("total_vehicle_queue_average"),
                "pedestrian_aware_vs_cooperative_total_pedestrian_wait": pedestrian_awareness.get("total_pedestrian_wait"),
                "pedestrian_aware_vs_cooperative_pedestrian_queue_average": pedestrian_awareness.get("total_pedestrian_queue_average"),
                "pedestrian_aware_vs_cooperative_max_pedestrian_wait": pedestrian_awareness.get("max_observed_pedestrian_wait"),
                "class_aware_vs_pedestrian_aware_selected_class": vehicle_class_priority.get("selected_class"),
                "emergency_priority_total_travel": emergency_metrics.get("total_travel_seconds"),
                "emergency_priority_source_wait": emergency_metrics.get("source_wait_seconds"),
                "emergency_priority_downstream_preparations": emergency_metrics.get("downstream_preparations"),
            },
        }



def _emergency_event_plan(
    *,
    seed: int,
    active_at_s: float,
    vehicle_type: str,
    link: dict[str, Any],
    source_intersection: dict[str, Any],
    destination_intersection: dict[str, Any],
) -> dict[str, Any]:
    stamp = int(round(float(active_at_s) * 1000.0))
    return {
        "event_id": f"emergency_{int(seed)}_{stamp}",
        "event_type": "emergency_vehicle_priority_request",
        "vehicle_id": f"emergency_vehicle_{int(seed)}_{stamp}",
        "vehicle_type": vehicle_type,
        "class_name": "emergency",
        "active_at_s": round(float(active_at_s), 3),
        "source_intersection_id": source_intersection.get("id"),
        "source_approach": link.get("source_approach"),
        "destination_intersection_id": destination_intersection.get("id"),
        "destination_approach": link.get("destination_approach"),
        "link_id": link.get("id"),
        "provenance": "simulated_configured_emergency_event",
        "confidence": None,
        "detector_claimed": False,
    }


def _normalize_vehicle_class(class_name: Any) -> str:
    value = str(class_name or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "car": "car",
        "vehicle": "car",
        "passenger_car": "car",
        "bus": "bus",
        "coach": "bus",
        "truck": "truck",
        "lorry": "truck",
        "hgv": "truck",
        "motorcycle": "motorcycle",
        "motorbike": "motorcycle",
        "motor_cycle": "motorcycle",
        "bicycle": "bicycle",
        "bike": "bicycle",
        "cyclist": "bicycle",
        "emergency": "emergency",
    }
    normalized = aliases.get(value, value)
    if normalized in REGULAR_VEHICLE_CLASSES or normalized in SPECIAL_VEHICLE_CLASSES:
        return normalized
    return "other"


def _weighted_vehicle_class(rng: random.Random, class_mix: dict[str, float]) -> str:
    normalized: list[tuple[str, float]] = []
    total = 0.0
    for raw_class, raw_weight in class_mix.items():
        class_name = _normalize_vehicle_class(raw_class)
        if class_name not in REGULAR_VEHICLE_CLASSES:
            class_name = "other"
        weight = max(0.0, float(raw_weight))
        if weight <= 0:
            continue
        normalized.append((class_name, weight))
        total += weight
    if total <= 0 or not normalized:
        return "car"
    target = rng.random() * total
    cumulative = 0.0
    for class_name, weight in normalized:
        cumulative += weight
        if target <= cumulative + 1e-12:
            return class_name
    return normalized[-1][0]


def _vehicle_class_counts(vehicles: list[Any]) -> dict[str, int]:
    counts = {class_name: 0 for class_name in REGULAR_VEHICLE_CLASSES}
    for vehicle in vehicles:
        class_name = _normalize_vehicle_class(getattr(vehicle, "class_name", None))
        if class_name in SPECIAL_VEHICLE_CLASSES:
            continue
        counts[class_name] = counts.get(class_name, 0) + 1
    return {key: value for key, value in counts.items() if value > 0}


def _intersection_vehicle_class_metrics(runtime: Any) -> dict[str, Any]:
    classes = set(REGULAR_VEHICLE_CLASSES) | set(SPECIAL_VEHICLE_CLASSES)
    classes.update(runtime.vehicle_class_external_arrivals)
    classes.update(runtime.vehicle_class_transfer_arrivals)
    classes.update(runtime.vehicle_class_served)
    classes.update(runtime.vehicle_class_waits)
    classes.update(runtime.vehicle_class_queue_samples)
    result: dict[str, Any] = {}
    for class_name in sorted(classes):
        queue_samples = runtime.vehicle_class_queue_samples.get(class_name, [])
        result[class_name] = {
            "external_arrivals": int(runtime.vehicle_class_external_arrivals.get(class_name, 0)),
            "transfer_arrivals": int(runtime.vehicle_class_transfer_arrivals.get(class_name, 0)),
            "served": int(runtime.vehicle_class_served.get(class_name, 0)),
            "waiting": _distribution(runtime.vehicle_class_waits.get(class_name, [])),
            "queue": {
                "sample_count": len(queue_samples),
                "average": round(sum(queue_samples) / len(queue_samples), 2) if queue_samples else 0.0,
                "p95": round(_percentile(queue_samples, 0.95), 2),
                "max": max(queue_samples, default=0),
            },
        }
    return result


def _network_vehicle_class_metrics(source: Any, destination: Any) -> dict[str, Any]:
    classes = set(REGULAR_VEHICLE_CLASSES) | set(SPECIAL_VEHICLE_CLASSES)
    result: dict[str, Any] = {}
    for class_name in sorted(classes):
        waits = source.vehicle_class_waits.get(class_name, []) + destination.vehicle_class_waits.get(class_name, [])
        queue_samples = [
            a + b
            for a, b in zip(
                source.vehicle_class_queue_samples.get(class_name, []),
                destination.vehicle_class_queue_samples.get(class_name, []),
            )
        ]
        result[class_name] = {
            "external_arrivals": int(source.vehicle_class_external_arrivals.get(class_name, 0) + destination.vehicle_class_external_arrivals.get(class_name, 0)),
            "transfer_arrivals": int(source.vehicle_class_transfer_arrivals.get(class_name, 0) + destination.vehicle_class_transfer_arrivals.get(class_name, 0)),
            "served": int(source.vehicle_class_served.get(class_name, 0) + destination.vehicle_class_served.get(class_name, 0)),
            "waiting": _distribution(waits),
            "queue_average": round(sum(queue_samples) / len(queue_samples), 2) if queue_samples else 0.0,
            "queue_p95": round(_percentile(queue_samples, 0.95), 2),
            "queue_peak": max(queue_samples, default=0),
        }
    return result


def _arrival_plan(
    *,
    duration_seconds: int,
    density: str,
    seed: int,
    transfer_share_percent: int,
    vehicle_class_profile: str = "legacy",
) -> dict[str, list[Any]]:
    rng = random.Random(seed + {"light": 1103, "normal": 2207, "busy": 3301}[density])
    source_vehicle_rate, destination_vehicle_rate = VEHICLE_RATES_PER_MINUTE[density]
    source_ped_rate, destination_ped_rate = PEDESTRIAN_RATES_PER_MINUTE[density]
    class_mix = VEHICLE_CLASS_PROFILES.get(vehicle_class_profile, VEHICLE_CLASS_PROFILES["legacy"])

    return {
        "source_vehicle_arrivals": _vehicle_arrivals(
            rng,
            rate_per_minute=source_vehicle_rate,
            duration_seconds=duration_seconds,
            prefix="src",
            transfer_share_percent=transfer_share_percent,
            class_mix=class_mix,
        ),
        "destination_vehicle_arrivals": _vehicle_arrivals(
            rng,
            rate_per_minute=destination_vehicle_rate,
            duration_seconds=duration_seconds,
            prefix="dst",
            transfer_share_percent=0,
            class_mix=class_mix,
        ),
        "source_pedestrian_arrivals": _pedestrian_arrivals(
            rng,
            rate_per_minute=source_ped_rate,
            duration_seconds=duration_seconds,
            prefix="srcp",
        ),
        "destination_pedestrian_arrivals": _pedestrian_arrivals(
            rng,
            rate_per_minute=destination_ped_rate,
            duration_seconds=duration_seconds,
            prefix="dstp",
        ),
    }


def _arrival_plan_snapshot(arrivals: dict[str, list[Any]]) -> dict[str, Any]:
    source_vehicles = arrivals["source_vehicle_arrivals"]
    destination_vehicles = arrivals["destination_vehicle_arrivals"]
    source_pedestrians = arrivals["source_pedestrian_arrivals"]
    destination_pedestrians = arrivals["destination_pedestrian_arrivals"]
    canonical = {
        "source_vehicle_arrivals": [
            [round(item.at_s, 3), item.vehicle_id, item.class_name, item.continues_to_destination]
            for item in source_vehicles
        ],
        "destination_vehicle_arrivals": [
            [round(item.at_s, 3), item.vehicle_id, item.class_name, item.continues_to_destination]
            for item in destination_vehicles
        ],
        "source_pedestrian_arrivals": [[round(item.at_s, 3), item.pedestrian_id] for item in source_pedestrians],
        "destination_pedestrian_arrivals": [
            [round(item.at_s, 3), item.pedestrian_id] for item in destination_pedestrians
        ],
    }
    fingerprint = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "source_vehicle_count": len(source_vehicles),
        "source_transfer_candidate_count": sum(1 for item in source_vehicles if item.continues_to_destination),
        "destination_external_vehicle_count": len(destination_vehicles),
        "source_vehicle_class_counts": _vehicle_class_counts(source_vehicles),
        "source_transfer_candidate_class_counts": _vehicle_class_counts([item for item in source_vehicles if item.continues_to_destination]),
        "destination_vehicle_class_counts": _vehicle_class_counts(destination_vehicles),
        "source_pedestrian_count": len(source_pedestrians),
        "destination_pedestrian_count": len(destination_pedestrians),
        "fingerprint_sha256": fingerprint,
        "note": "Fixed, Independent Adaptive, and Cooperative Adaptive receive this same seeded exogenous arrival plan; transfer departure timing remains policy-dependent.",
    }


def _vehicle_arrivals(
    rng: random.Random,
    *,
    rate_per_minute: float,
    duration_seconds: int,
    prefix: str,
    transfer_share_percent: int,
    class_mix: dict[str, float] | None = None,
) -> list[_VehicleArrival]:
    events: list[_VehicleArrival] = []
    if rate_per_minute <= 0:
        return events
    clock = 0.0
    rate_per_second = rate_per_minute / 60.0
    index = 0
    while True:
        clock += rng.expovariate(rate_per_second)
        if clock > duration_seconds:
            break
        index += 1
        class_name = _weighted_vehicle_class(rng, class_mix or VEHICLE_CLASS_PROFILES["legacy"])
        continues = rng.random() * 100.0 < transfer_share_percent
        events.append(
            _VehicleArrival(
                at_s=round(clock, 3),
                vehicle_id=f"{prefix}_{index:04d}",
                class_name=class_name,
                continues_to_destination=continues,
            )
        )
    return events


def _pedestrian_arrivals(
    rng: random.Random,
    *,
    rate_per_minute: float,
    duration_seconds: int,
    prefix: str,
) -> list[_PedestrianArrival]:
    events: list[_PedestrianArrival] = []
    if rate_per_minute <= 0:
        return events
    clock = 0.0
    rate_per_second = rate_per_minute / 60.0
    index = 0
    while True:
        clock += rng.expovariate(rate_per_second)
        if clock > duration_seconds:
            break
        index += 1
        events.append(_PedestrianArrival(at_s=round(clock, 3), pedestrian_id=f"{prefix}_{index:04d}"))
    return events


def _intersection_snapshot(intersection: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": intersection.get("id"),
        "label": intersection.get("label"),
        "signal_profile": intersection.get("signal_profile"),
        "zone_ids": list(intersection.get("zone_ids", [])),
    }


def _percentile(values: list[float] | list[int], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _distribution(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "count": 0,
            "average_seconds": 0.0,
            "median_seconds": 0.0,
            "p95_seconds": 0.0,
            "max_seconds": 0.0,
            "total_seconds": 0.0,
        }
    return {
        "count": len(values),
        "average_seconds": round(sum(values) / len(values), 2),
        "median_seconds": round(_percentile(values, 0.5), 2),
        "p95_seconds": round(_percentile(values, 0.95), 2),
        "max_seconds": round(max(values), 2),
        "total_seconds": round(sum(values), 2),
    }


def _queue_distribution(
    values: list[int],
    queue_seconds: float,
    occupied_seconds: float,
    duration_seconds: float,
) -> dict[str, Any]:
    return {
        "sample_count": len(values),
        "average": round(sum(values) / len(values), 2) if values else 0.0,
        "p95": round(_percentile(values, 0.95), 2),
        "max": max(values, default=0),
        "queue_seconds": round(queue_seconds, 2),
        "occupied_seconds": round(occupied_seconds, 2),
        "occupied_share_percent": round(occupied_seconds / duration_seconds * 100.0, 1)
        if duration_seconds
        else 0.0,
    }


def _delta(
    baseline: float,
    candidate: float,
    *,
    lower_is_better: bool,
    baseline_label: str = "fixed",
    candidate_label: str = "adaptive",
) -> dict[str, Any]:
    difference = candidate - baseline
    percent_change = (difference / baseline * 100.0) if abs(baseline) > 1e-9 else None
    if abs(difference) < 1e-9:
        direction = "same"
    elif (difference < 0) == lower_is_better:
        direction = "better"
    else:
        direction = "worse"
    return {
        baseline_label: round(baseline, 2),
        candidate_label: round(candidate, 2),
        "difference": round(difference, 2),
        "percent_change": round(percent_change, 1) if percent_change is not None else None,
        f"{candidate_label}_direction": direction,
        "lower_is_better": lower_is_better,
    }


def _network_comparison(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    *,
    baseline_label: str = "fixed",
    candidate_label: str = "adaptive",
) -> dict[str, Any]:
    baseline_metrics = baseline["network_metrics"]
    candidate_metrics = candidate["network_metrics"]

    def delta(key_a: str, key_b: str | None = None, *, lower_is_better: bool) -> dict[str, Any]:
        key_b = key_b or key_a
        return _delta(
            baseline_metrics[key_a],
            candidate_metrics[key_b],
            lower_is_better=lower_is_better,
            baseline_label=baseline_label,
            candidate_label=candidate_label,
        )

    return {
        "corridor_completed": _delta(
            baseline_metrics["corridor_completed_per_minute"],
            candidate_metrics["corridor_completed_per_minute"],
            lower_is_better=False,
            baseline_label=baseline_label,
            candidate_label=candidate_label,
        ),
        "corridor_travel_average": _delta(
            baseline_metrics["corridor_travel_time"]["average_seconds"],
            candidate_metrics["corridor_travel_time"]["average_seconds"],
            lower_is_better=True,
            baseline_label=baseline_label,
            candidate_label=candidate_label,
        ),
        "corridor_travel_p95": _delta(
            baseline_metrics["corridor_travel_time"]["p95_seconds"],
            candidate_metrics["corridor_travel_time"]["p95_seconds"],
            lower_is_better=True,
            baseline_label=baseline_label,
            candidate_label=candidate_label,
        ),
        "total_vehicle_wait": delta("total_vehicle_wait_seconds", lower_is_better=True),
        "total_vehicle_queue_average": delta("total_vehicle_queue_average", lower_is_better=True),
        "total_vehicle_queue_p95": delta("total_vehicle_queue_p95", lower_is_better=True),
        "transfer_pipeline_average": delta("transfer_pipeline_average", lower_is_better=True),
        "total_pedestrian_wait": delta("total_pedestrian_wait_seconds", lower_is_better=True),
        "total_pedestrian_queue_average": delta("total_pedestrian_queue_average", lower_is_better=True),
        "total_pedestrian_queue_p95": delta("total_pedestrian_queue_p95", lower_is_better=True),
        "max_observed_pedestrian_wait": delta("max_observed_pedestrian_wait_seconds", lower_is_better=True),
    }


def _vehicle_class_comparison(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    class_name: str,
    *,
    baseline_label: str,
    candidate_label: str,
) -> dict[str, Any]:
    normalized = _normalize_vehicle_class(class_name)
    baseline_metrics = baseline.get("network_metrics", {}).get("vehicle_classes", {}).get(normalized, {})
    candidate_metrics = candidate.get("network_metrics", {}).get("vehicle_classes", {}).get(normalized, {})
    baseline_wait = baseline_metrics.get("waiting", {})
    candidate_wait = candidate_metrics.get("waiting", {})
    return {
        "class_name": normalized,
        "baseline_label": baseline_label,
        "candidate_label": candidate_label,
        "served": _delta(
            float(baseline_metrics.get("served", 0) or 0),
            float(candidate_metrics.get("served", 0) or 0),
            baseline_label=baseline_label,
            candidate_label=candidate_label,
            lower_is_better=False,
        ),
        "average_wait_seconds": _delta(
            float(baseline_wait.get("average_seconds", 0.0) or 0.0),
            float(candidate_wait.get("average_seconds", 0.0) or 0.0),
            baseline_label=baseline_label,
            candidate_label=candidate_label,
            lower_is_better=True,
        ),
        "p95_wait_seconds": _delta(
            float(baseline_wait.get("p95_seconds", 0.0) or 0.0),
            float(candidate_wait.get("p95_seconds", 0.0) or 0.0),
            baseline_label=baseline_label,
            candidate_label=candidate_label,
            lower_is_better=True,
        ),
        "queue_average": _delta(
            float(baseline_metrics.get("queue_average", 0.0) or 0.0),
            float(candidate_metrics.get("queue_average", 0.0) or 0.0),
            baseline_label=baseline_label,
            candidate_label=candidate_label,
            lower_is_better=True,
        ),
    }


def _emergency_comparison(baseline: dict[str, Any], priority: dict[str, Any]) -> dict[str, Any]:
    baseline_metrics = baseline.get("network_metrics", {}).get("emergency", {})
    priority_metrics = priority.get("network_metrics", {}).get("emergency", {})

    def optional_delta(key: str) -> dict[str, Any]:
        baseline_value = baseline_metrics.get(key)
        priority_value = priority_metrics.get(key)
        if baseline_value is None or priority_value is None:
            return {
                "available": False,
                "baseline": baseline_value,
                "priority": priority_value,
                "lower_is_better": True,
                "note": "comparison unavailable unless the simulated emergency vehicle completes both matched runs",
            }
        payload = _delta(
            float(baseline_value),
            float(priority_value),
            lower_is_better=True,
            baseline_label="emergency_baseline_cooperative",
            candidate_label="emergency_priority_cooperative",
        )
        payload["available"] = True
        return payload

    return {
        "baseline_completed": bool(baseline_metrics.get("completed")),
        "priority_completed": bool(priority_metrics.get("completed")),
        "source_wait_seconds": optional_delta("source_wait_seconds"),
        "destination_wait_seconds": optional_delta("destination_wait_seconds"),
        "total_travel_seconds": optional_delta("total_travel_seconds"),
        "priority_evaluations": priority_metrics.get("priority_evaluations", 0),
        "priority_grants": priority_metrics.get("priority_grants", 0),
        "priority_denials": priority_metrics.get("priority_denials", 0),
        "downstream_preparations": priority_metrics.get("downstream_preparations", 0),
    }


network_simulation_experiment_service = NetworkSimulationExperimentService()
