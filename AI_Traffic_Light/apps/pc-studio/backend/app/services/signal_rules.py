from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import os
from pathlib import Path
from threading import Lock
import time
from typing import Any

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.core.json_store import read_json, write_json_atomic
from app.core.logging_config import get_logger

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "signal_rules.json"
DEFAULT_HISTORY_PATH = PROJECT_ROOT / "outputs" / "signal_rules" / "decision_history.jsonl"

PHASE_SEQUENCE: tuple[tuple[str, str], ...] = (
    ("vehicle_green", "vehicle_green"),
    ("vehicle_yellow", "vehicle_yellow"),
    ("all_red_to_pedestrian", "all_red"),
    ("pedestrian_green", "pedestrian_green"),
    ("pedestrian_flashing", "pedestrian_flashing"),
    ("all_red_to_vehicle", "all_red"),
)
PHASE_KEYS = tuple(key for key, _ in PHASE_SEQUENCE)
PROTECTED_MINIMUMS = {
    "vehicle_green": 5.0,
    "vehicle_yellow": 2.0,
    "all_red_to_pedestrian": 1.0,
    "pedestrian_green": 4.0,
    "pedestrian_flashing": 3.0,
    "all_red_to_vehicle": 1.0,
}
ALLOWED_MODES = {"fixed", "adaptive", "test"}
ALLOWED_ACTIONS = {"extend_current_phase", "reduce_current_phase", "hold_current_phase", "request_next_phase", "incident_hold"}
ALLOWED_LEGACY_TRIGGERS = {
    "pedestrians_crossing",
    "crossing_dwell_seconds",
    "pedestrians_waiting",
    "pedestrian_wait_seconds",
    "vehicles_waiting",
    "vehicle_wait_seconds",
    "low_vehicle_demand",
    "mobility_assistance",
    "incident_person_fallen",
}
ALLOWED_CONDITION_SOURCES = {"metric", "zone_class_count"}
ALLOWED_OPERATORS = {"gt", "gte", "lt", "lte", "eq"}
ALLOWED_MATCH = {"all", "any"}
ALLOWED_REQUEST_SERVICES = {None, "pedestrian", "vehicle"}
ALLOWED_METRICS = {
    "pedestrians_crossing",
    "crossing_dwell_seconds",
    "pedestrians_waiting",
    "pedestrian_wait_seconds",
    "vehicles_waiting",
    "vehicle_wait_seconds",
    "mobility_assistance",
    "incident_person_fallen",
}
TEST_ONLY_METRICS = {"mobility_assistance", "incident_person_fallen"}


def _legacy_rule_to_conditions(rule: dict[str, Any]) -> list[dict[str, Any]]:
    trigger = str(rule.get("trigger", ""))
    threshold = float(rule.get("threshold", 0.0) or 0.0)
    if trigger == "low_vehicle_demand":
        return [
            {"source": "metric", "metric": "vehicles_waiting", "operator": "lte", "threshold": threshold},
            {"source": "metric", "metric": "pedestrians_waiting", "operator": "gt", "threshold": 0.0},
        ]
    if trigger in TEST_ONLY_METRICS:
        return [{"source": "metric", "metric": trigger, "operator": "eq", "threshold": 1.0}]
    return [{"source": "metric", "metric": trigger, "operator": "gte", "threshold": threshold}]


def _legacy_rules_to_scenarios(rules: dict[str, Any]) -> list[dict[str, Any]]:
    ordered = sorted(rules.items(), key=lambda item: (-int(item[1].get("priority", 0)), item[0]))
    scenarios: list[dict[str, Any]] = []
    for index, (rule_id, rule) in enumerate(ordered, start=1):
        trigger = str(rule.get("trigger", ""))
        request_service: str | None = None
        if trigger in {"pedestrians_waiting", "pedestrian_wait_seconds", "low_vehicle_demand"}:
            request_service = "pedestrian"
        elif trigger in {"vehicles_waiting", "vehicle_wait_seconds"}:
            request_service = "vehicle"
        scenarios.append(
            {
                "id": rule_id,
                "label": str(rule.get("label") or rule_id.replace("_", " ").title()),
                "enabled": bool(rule.get("enabled", True)),
                "rank": index * 10,
                "match": "all",
                "conditions": _legacy_rule_to_conditions(rule),
                "persistence_seconds": float(rule.get("persistence_seconds", 0.0) or 0.0),
                "cooldown_seconds": float(rule.get("cooldown_seconds", 0.0) or 0.0),
                "action": {
                    "type": str(rule.get("action", "hold_current_phase")),
                    "adjustment_seconds": float(rule.get("adjustment_seconds", 0.0) or 0.0),
                    "target_phases": list(rule.get("target_phases", PHASE_KEYS)),
                    "request_service": request_service,
                },
            }
        )
    return scenarios


DEFAULT_RULES: dict[str, Any] = {
    "crossing_occupied": {
        "label": "Pedestrian still crossing",
        "enabled": True,
        "trigger": "pedestrians_crossing",
        "threshold": 1.0,
        "persistence_seconds": 0.5,
        "action": "hold_current_phase",
        "adjustment_seconds": 3.0,
        "target_phases": ["pedestrian_flashing"],
        "priority": 100,
        "cooldown_seconds": 0.0,
    },
    "mobility_assistance": {
        "label": "Mobility / accessibility assistance",
        "enabled": True,
        "trigger": "mobility_assistance",
        "threshold": 1.0,
        "persistence_seconds": 0.0,
        "action": "extend_current_phase",
        "adjustment_seconds": 6.0,
        "target_phases": ["pedestrian_green", "pedestrian_flashing"],
        "priority": 95,
        "cooldown_seconds": 0.0,
    },
    "slow_pedestrian": {
        "label": "Slow / extended pedestrian crossing",
        "enabled": True,
        "trigger": "crossing_dwell_seconds",
        "threshold": 5.0,
        "persistence_seconds": 1.0,
        "action": "extend_current_phase",
        "adjustment_seconds": 4.0,
        "target_phases": ["pedestrian_flashing"],
        "priority": 90,
        "cooldown_seconds": 0.0,
    },
    "max_pedestrian_wait": {
        "label": "Maximum pedestrian waiting time",
        "enabled": True,
        "trigger": "pedestrian_wait_seconds",
        "threshold": 30.0,
        "persistence_seconds": 1.0,
        "action": "reduce_current_phase",
        "adjustment_seconds": 4.0,
        "target_phases": ["vehicle_green"],
        "priority": 85,
        "cooldown_seconds": 12.0,
    },
    "heavy_pedestrian_demand": {
        "label": "Heavy pedestrian demand",
        "enabled": True,
        "trigger": "pedestrians_waiting",
        "threshold": 5.0,
        "persistence_seconds": 2.0,
        "action": "reduce_current_phase",
        "adjustment_seconds": 3.0,
        "target_phases": ["vehicle_green"],
        "priority": 80,
        "cooldown_seconds": 10.0,
    },
    "low_vehicle_demand": {
        "label": "Low vehicle demand with pedestrian request",
        "enabled": True,
        "trigger": "low_vehicle_demand",
        "threshold": 1.0,
        "persistence_seconds": 2.0,
        "action": "reduce_current_phase",
        "adjustment_seconds": 2.0,
        "target_phases": ["vehicle_green"],
        "priority": 75,
        "cooldown_seconds": 10.0,
    },
    "max_vehicle_wait": {
        "label": "Maximum vehicle waiting time",
        "enabled": True,
        "trigger": "vehicle_wait_seconds",
        "threshold": 45.0,
        "persistence_seconds": 1.0,
        "action": "extend_current_phase",
        "adjustment_seconds": 5.0,
        "target_phases": ["vehicle_green"],
        "priority": 70,
        "cooldown_seconds": 12.0,
    },
    "heavy_vehicle_queue": {
        "label": "Heavy vehicle queue",
        "enabled": True,
        "trigger": "vehicles_waiting",
        "threshold": 6.0,
        "persistence_seconds": 2.0,
        "action": "extend_current_phase",
        "adjustment_seconds": 5.0,
        "target_phases": ["vehicle_green"],
        "priority": 60,
        "cooldown_seconds": 10.0,
    },
    "incident_person_fallen": {
        "label": "Person fallen / incident",
        "enabled": True,
        "trigger": "incident_person_fallen",
        "threshold": 1.0,
        "persistence_seconds": 0.0,
        "action": "incident_hold",
        "adjustment_seconds": 0.0,
        "target_phases": list(PHASE_KEYS),
        "priority": 1000,
        "cooldown_seconds": 0.0,
    },
}

DEFAULT_PROFILE: dict[str, Any] = {
    "description": "Balanced scenario-driven classroom/prototype signal policy.",
    "phases": {
        "vehicle_green": {"base_seconds": 12.0, "min_seconds": 8.0, "max_seconds": 30.0},
        "vehicle_yellow": {"base_seconds": 3.0, "min_seconds": 2.0, "max_seconds": 5.0},
        "all_red_to_pedestrian": {"base_seconds": 3.0, "min_seconds": 2.0, "max_seconds": 6.0},
        "pedestrian_green": {"base_seconds": 8.0, "min_seconds": 6.0, "max_seconds": 20.0},
        "pedestrian_flashing": {"base_seconds": 6.0, "min_seconds": 4.0, "max_seconds": 20.0},
        "all_red_to_vehicle": {"base_seconds": 2.0, "min_seconds": 2.0, "max_seconds": 6.0},
    },
    "max_cycle_seconds": 90.0,
    "stale_data_seconds": 4.0,
    "demand_memory_seconds": 3.0,
    "rules": deepcopy(DEFAULT_RULES),
    "scenarios": _legacy_rules_to_scenarios(DEFAULT_RULES),
}

DEFAULT_CONFIG: dict[str, Any] = {
    "schema_version": 1,
    "mode": "adaptive",
    "dry_run": False,
    "active_profile": "Normal",
    "profiles": {
        "Normal": deepcopy(DEFAULT_PROFILE),
        "Pedestrian Priority": {**deepcopy(DEFAULT_PROFILE), "description": "Prototype preset that serves pedestrian demand sooner."},
        "Vehicle Priority": {**deepcopy(DEFAULT_PROFILE), "description": "Prototype preset that permits a larger bounded vehicle-green response."},
        "Accessibility": {**deepcopy(DEFAULT_PROFILE), "description": "Prototype preset emphasizing extended pedestrian service and mobility assistance."},
    },
}
DEFAULT_CONFIG["profiles"]["Pedestrian Priority"]["rules"]["heavy_pedestrian_demand"]["threshold"] = 3.0
DEFAULT_CONFIG["profiles"]["Pedestrian Priority"]["rules"]["max_pedestrian_wait"]["threshold"] = 20.0
DEFAULT_CONFIG["profiles"]["Vehicle Priority"]["phases"]["vehicle_green"]["max_seconds"] = 35.0
DEFAULT_CONFIG["profiles"]["Vehicle Priority"]["rules"]["heavy_vehicle_queue"]["adjustment_seconds"] = 7.0
DEFAULT_CONFIG["profiles"]["Accessibility"]["rules"]["mobility_assistance"]["adjustment_seconds"] = 9.0
DEFAULT_CONFIG["profiles"]["Accessibility"]["phases"]["pedestrian_flashing"]["max_seconds"] = 24.0
for _profile in DEFAULT_CONFIG["profiles"].values():
    _profile["scenarios"] = _legacy_rules_to_scenarios(_profile["rules"])


@dataclass
class _DemandMemory:
    first_seen_monotonic: float | None = None
    last_seen_monotonic: float | None = None
    last_count: int = 0


def _compare(operator: str, value: float, threshold: float) -> bool:
    if operator == "gt":
        return value > threshold
    if operator == "gte":
        return value >= threshold
    if operator == "lt":
        return value < threshold
    if operator == "lte":
        return value <= threshold
    return abs(value - threshold) <= 1e-9


class SignalRulesService:
    """Persist and evaluate ranked user-defined signal scenarios for local simulation only."""

    def __init__(self, *, config_path: Path | None = None, history_path: Path | None = None) -> None:
        configured_path = os.environ.get("AITL_SIGNAL_RULES")
        self._config_path = Path(configured_path) if configured_path else (config_path or DEFAULT_CONFIG_PATH)
        self._config_path = self._config_path.expanduser().resolve()
        self._history_path = (history_path or DEFAULT_HISTORY_PATH).expanduser().resolve()
        self._lock = Lock()
        self._config_cache: dict[str, Any] | None = None
        self._phase_index = 0
        self._phase_started_clock = 0.0
        self._phase_duration_seconds = 12.0
        self._phase_base_seconds = 12.0
        self._applied_rule_ids: set[str] = set()
        self._rule_condition_since: dict[str, float] = {}
        self._rule_last_applied_clock: dict[str, float] = {}
        self._last_rule_status: list[dict[str, Any]] = []
        self._last_active_rules: list[str] = []
        self._winning_scenario_id: str | None = None
        self._winning_scenario_label: str | None = None
        self._pending_request: str | None = None
        self._incident_hold = False
        self._resume_after_incident = False
        self._reinitialize_pending = False
        self._cycle_started_clock = 0.0
        self._last_clock_s = 0.0
        self._last_observation: dict[str, Any] = {}
        self._last_observation_monotonic: float | None = None
        self._pedestrian_wait = _DemandMemory()
        self._vehicle_wait = _DemandMemory()
        self._crossing = _DemandMemory()
        self._test_inputs = {
            "pedestrians_waiting": 0,
            "pedestrians_crossing": 0,
            "vehicles_waiting": 0,
            "mobility_assistance": False,
            "incident_person_fallen": False,
        }
        self._initialize_phase_locked(0.0)

    def defaults(self) -> dict[str, Any]:
        return deepcopy(DEFAULT_CONFIG)

    def get_config(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._load_config_locked())

    def save_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        validated = self._validate_config(payload)
        try:
            with self._lock:
                write_json_atomic(self._config_path, validated)
                self._config_cache = validated
                if validated["mode"] != "test":
                    self._test_inputs["mobility_assistance"] = False
                    self._test_inputs["incident_person_fallen"] = False
                    self._incident_hold = False
                    self._resume_after_incident = False
                self._applied_rule_ids.clear()
                self._rule_condition_since.clear()
                self._rule_last_applied_clock.clear()
                self._last_rule_status = []
                self._last_active_rules = []
                self._winning_scenario_id = None
                self._winning_scenario_label = None
                self._pending_request = None
                self._reinitialize_pending = True
                self._record_event_locked(
                    "config_saved",
                    {
                        "active_profile": validated["active_profile"],
                        "mode": validated["mode"],
                        "scenario_count": len(validated["profiles"][validated["active_profile"]]["scenarios"]),
                    },
                )
        except OSError as exc:
            logger.exception("Signal scenario configuration save failed")
            raise AppError(ErrorCode.SETTINGS_WRITE_FAILED, "Failed to save the signal scenario configuration.", status_code=500) from exc
        return deepcopy(validated)

    def reset_config(self) -> dict[str, Any]:
        return self.save_config(self.defaults())

    def set_test_inputs(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            for key in ("pedestrians_waiting", "pedestrians_crossing", "vehicles_waiting"):
                if key in payload and payload[key] is not None:
                    value = int(payload[key])
                    if value < 0 or value > 500:
                        raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"{key} must be between 0 and 500.", status_code=422)
                    self._test_inputs[key] = value
            for key in ("mobility_assistance", "incident_person_fallen"):
                if key in payload and payload[key] is not None:
                    self._test_inputs[key] = bool(payload[key])
            return deepcopy(self._test_inputs)

    def clear_incident(self) -> dict[str, Any]:
        with self._lock:
            self._test_inputs["incident_person_fallen"] = False
            if self._incident_hold:
                self._record_event_locked("incident_hold_cleared", {"source": "scenario_or_manual_test_input"})
            was_held = self._incident_hold
            self._incident_hold = False
            self._resume_after_incident = was_held
            return deepcopy(self._test_inputs)

    def reset_runtime(self, simulation_clock_s: float = 0.0) -> dict[str, Any]:
        with self._lock:
            self._reset_runtime_locked(simulation_clock_s)
            self._record_event_locked("runtime_reset", {})
            return self._status_locked(simulation_clock_s)

    def _reset_runtime_locked(self, simulation_clock_s: float) -> None:
        self._phase_index = 0
        self._phase_started_clock = max(0.0, float(simulation_clock_s))
        self._applied_rule_ids.clear()
        self._rule_condition_since.clear()
        self._rule_last_applied_clock.clear()
        self._last_rule_status = []
        self._last_active_rules = []
        self._winning_scenario_id = None
        self._winning_scenario_label = None
        self._pending_request = None
        self._incident_hold = False
        self._resume_after_incident = False
        self._reinitialize_pending = False
        self._cycle_started_clock = max(0.0, float(simulation_clock_s))
        self._last_clock_s = max(0.0, float(simulation_clock_s))
        self._pedestrian_wait = _DemandMemory()
        self._vehicle_wait = _DemandMemory()
        self._crossing = _DemandMemory()
        self._initialize_phase_locked(self._phase_started_clock)

    def observe(self, observation: dict[str, Any]) -> None:
        now = time.monotonic()
        with self._lock:
            zone_class_counts = observation.get("zone_class_counts", {})
            if not isinstance(zone_class_counts, dict):
                zone_class_counts = {}
            self._last_observation = {
                "pedestrians_waiting": max(0, int(observation.get("pedestrians_waiting", 0) or 0)),
                "pedestrians_crossing": max(0, int(observation.get("pedestrians_crossing", 0) or 0)),
                "vehicles_waiting": max(0, int(observation.get("vehicles_waiting", 0) or 0)),
                "zone_class_counts": deepcopy(zone_class_counts),
                "source_frame_number": observation.get("source_frame_number"),
                "source_timestamp_ms": observation.get("source_timestamp_ms"),
                "data_source": observation.get("data_source"),
            }
            self._last_observation_monotonic = now
            self._update_memory_locked(self._pedestrian_wait, self._last_observation["pedestrians_waiting"], now)
            self._update_memory_locked(self._vehicle_wait, self._last_observation["vehicles_waiting"], now)
            self._update_memory_locked(self._crossing, self._last_observation["pedestrians_crossing"], now)

    @staticmethod
    def _update_memory_locked(memory: _DemandMemory, count: int, now: float) -> None:
        if count > 0:
            if memory.first_seen_monotonic is None:
                memory.first_seen_monotonic = now
            memory.last_seen_monotonic = now
            memory.last_count = count
        else:
            memory.last_count = 0

    def signal_state(self, simulation_clock_s: float) -> dict[str, Any]:
        clock = max(0.0, float(simulation_clock_s))
        with self._lock:
            self._advance_phase_locked(clock)
            self._evaluate_rules_locked(clock, apply=True)
            return self._status_locked(clock)

    def status(self, simulation_clock_s: float) -> dict[str, Any]:
        clock = max(0.0, float(simulation_clock_s))
        with self._lock:
            self._advance_phase_locked(clock)
            self._evaluate_rules_locked(clock, apply=False)
            return self._status_locked(clock)

    def preview(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            config = self._load_config_locked()
            profile = self._active_profile_locked(config)
            phase_key = str(payload.get("phase_key") or PHASE_SEQUENCE[self._phase_index][0])
            if phase_key not in PHASE_KEYS:
                raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "preview phase_key is invalid.", status_code=422)
            values = {
                "pedestrians_waiting": max(0, int(payload.get("pedestrians_waiting", 0) or 0)),
                "pedestrians_crossing": max(0, int(payload.get("pedestrians_crossing", 0) or 0)),
                "vehicles_waiting": max(0, int(payload.get("vehicles_waiting", 0) or 0)),
                "pedestrian_wait_seconds": max(0.0, float(payload.get("pedestrian_wait_seconds", 0.0) or 0.0)),
                "vehicle_wait_seconds": max(0.0, float(payload.get("vehicle_wait_seconds", 0.0) or 0.0)),
                "crossing_dwell_seconds": max(0.0, float(payload.get("crossing_dwell_seconds", 0.0) or 0.0)),
                "mobility_assistance": bool(payload.get("mobility_assistance", False)),
                "incident_person_fallen": bool(payload.get("incident_person_fallen", False)),
                "zone_class_counts": deepcopy(payload.get("zone_class_counts", {})) if isinstance(payload.get("zone_class_counts", {}), dict) else {},
            }
            phase = profile["phases"][phase_key]
            effective = float(phase["base_seconds"])
            statuses, winner = self._evaluate_scenario_candidates_locked(config, profile, phase_key, values, clock=0.0, fresh=True, mutate=False)
            if winner:
                action = winner["action"]
                adjustment = float(action["adjustment_seconds"])
                if action["type"] == "extend_current_phase":
                    effective += adjustment
                elif action["type"] in {"reduce_current_phase", "request_next_phase"}:
                    effective -= adjustment if action["type"] == "reduce_current_phase" else effective
                effective = min(float(phase["max_seconds"]), max(float(phase["min_seconds"]), effective))
            return {
                "phase_key": phase_key,
                "phase": dict(PHASE_SEQUENCE)[phase_key],
                "base_duration_seconds": float(phase["base_seconds"]),
                "effective_duration_seconds": round(effective, 1),
                "winning_scenario_id": winner["id"] if winner else None,
                "rules": statuses,
                "scenarios": statuses,
                "would_enter_incident_hold": bool(winner and winner["action"]["type"] == "incident_hold"),
                "prototype_only": True,
            }

    def history(self, limit: int = 200) -> dict[str, Any]:
        limit = max(1, min(int(limit), 2000))
        with self._lock:
            events = self._read_history_locked(limit)
            return {"events": events, "count": len(events), "history_path": self._relative_history_path(), "prototype_only": True}

    def clear_history(self) -> dict[str, Any]:
        with self._lock:
            removed = len(self._read_history_locked(2000))
            try:
                if self._history_path.exists():
                    self._history_path.unlink()
            except OSError as exc:
                raise AppError(ErrorCode.SETTINGS_WRITE_FAILED, "Failed to clear signal decision history.", status_code=500) from exc
            return {"cleared": True, "removed_events": removed, "history_path": self._relative_history_path()}

    def _load_config_locked(self) -> dict[str, Any]:
        if self._config_cache is not None:
            return self._config_cache
        if not self._config_path.is_file():
            self._config_cache = self._validate_config(self.defaults())
            return self._config_cache
        try:
            raw = read_json(self._config_path)
        except (OSError, json.JSONDecodeError) as exc:
            raise AppError(ErrorCode.SETTINGS_READ_FAILED, "Failed to read the signal-rule configuration.", status_code=500) from exc
        self._config_cache = self._validate_config(raw)
        return self._config_cache

    @classmethod
    def _validate_config(cls, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "Signal-rule configuration must be an object.", status_code=422)
        config = deepcopy(payload)
        if int(config.get("schema_version", 0)) != 1:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "Unsupported signal-rule schema_version.", status_code=422)
        mode = str(config.get("mode", "adaptive"))
        if mode not in ALLOWED_MODES:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "mode must be fixed, adaptive, or test.", status_code=422)
        config["mode"] = mode
        config["dry_run"] = bool(config.get("dry_run", False))
        profiles = config.get("profiles")
        active_profile = str(config.get("active_profile", ""))
        if not isinstance(profiles, dict) or not profiles or active_profile not in profiles:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "active_profile must identify an existing profile.", status_code=422)
        if len(profiles) > 20:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "A maximum of 20 signal profiles is supported.", status_code=422)

        normalized_profiles: dict[str, Any] = {}
        for profile_name, raw_profile in profiles.items():
            if not isinstance(profile_name, str) or not 1 <= len(profile_name.strip()) <= 64:
                raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "Profile names must contain 1-64 characters.", status_code=422)
            if not isinstance(raw_profile, dict):
                raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Profile {profile_name} is invalid.", status_code=422)
            phases = raw_profile.get("phases")
            if not isinstance(phases, dict) or set(phases) != set(PHASE_KEYS):
                raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Profile {profile_name} must define all signal phases.", status_code=422)
            normalized_phases: dict[str, Any] = {}
            base_cycle = 0.0
            for phase_key in PHASE_KEYS:
                raw_phase = phases[phase_key]
                if not isinstance(raw_phase, dict):
                    raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Phase {phase_key} is invalid.", status_code=422)
                try:
                    base = float(raw_phase["base_seconds"])
                    minimum = float(raw_phase["min_seconds"])
                    maximum = float(raw_phase["max_seconds"])
                except (KeyError, TypeError, ValueError) as exc:
                    raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Phase {phase_key} timing is invalid.", status_code=422) from exc
                if minimum < PROTECTED_MINIMUMS[phase_key] or not minimum <= base <= maximum or maximum > 120.0:
                    raise AppError(
                        ErrorCode.TRAFFIC_RULE_INVALID,
                        f"Phase {phase_key} must satisfy protected minimum <= min <= base <= max <= 120 seconds.",
                        status_code=422,
                        details={"protected_minimum": PROTECTED_MINIMUMS[phase_key]},
                    )
                normalized_phases[phase_key] = {
                    "base_seconds": round(base, 1),
                    "min_seconds": round(minimum, 1),
                    "max_seconds": round(maximum, 1),
                }
                base_cycle += base
            max_cycle = float(raw_profile.get("max_cycle_seconds", 90.0))
            stale = float(raw_profile.get("stale_data_seconds", 4.0))
            memory = float(raw_profile.get("demand_memory_seconds", 3.0))
            if max_cycle < base_cycle or max_cycle > 300.0 or not 1.0 <= stale <= 30.0 or not 0.0 <= memory <= 30.0:
                raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Profile {profile_name} controller limits are invalid.", status_code=422)

            rules = raw_profile.get("rules", {})
            normalized_rules: dict[str, Any] = {}
            if not isinstance(rules, dict):
                raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Profile {profile_name} legacy rules must be an object.", status_code=422)
            for rule_id, raw_rule in rules.items():
                if not isinstance(rule_id, str) or not 1 <= len(rule_id) <= 64 or not isinstance(raw_rule, dict):
                    raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "Legacy rule identifiers are invalid.", status_code=422)
                trigger = str(raw_rule.get("trigger", ""))
                action = str(raw_rule.get("action", ""))
                targets = raw_rule.get("target_phases", [])
                if trigger not in ALLOWED_LEGACY_TRIGGERS or action not in ALLOWED_ACTIONS:
                    raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Legacy rule {rule_id} trigger/action is invalid.", status_code=422)
                if not isinstance(targets, list) or not targets or any(target not in PHASE_KEYS for target in targets):
                    raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Legacy rule {rule_id} target phases are invalid.", status_code=422)
                try:
                    threshold = float(raw_rule.get("threshold", 1.0))
                    persistence = float(raw_rule.get("persistence_seconds", 0.0))
                    adjustment = float(raw_rule.get("adjustment_seconds", 0.0))
                    priority = int(raw_rule.get("priority", 0))
                    cooldown = float(raw_rule.get("cooldown_seconds", 0.0))
                except (TypeError, ValueError) as exc:
                    raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Legacy rule {rule_id} numeric values are invalid.", status_code=422) from exc
                if threshold < 0 or persistence < 0 or adjustment < 0 or adjustment > 60.0 or cooldown < 0 or not 0 <= priority <= 10000:
                    raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Legacy rule {rule_id} values are outside supported limits.", status_code=422)
                normalized_rules[rule_id] = {
                    "label": str(raw_rule.get("label") or rule_id.replace("_", " ").title())[:120],
                    "enabled": bool(raw_rule.get("enabled", True)),
                    "trigger": trigger,
                    "threshold": round(threshold, 2),
                    "persistence_seconds": round(persistence, 2),
                    "action": action,
                    "adjustment_seconds": round(adjustment, 1),
                    "target_phases": list(dict.fromkeys(targets)),
                    "priority": priority,
                    "cooldown_seconds": round(cooldown, 1),
                }

            raw_scenarios = raw_profile.get("scenarios")
            if raw_scenarios is None:
                raw_scenarios = _legacy_rules_to_scenarios(normalized_rules)
            if not isinstance(raw_scenarios, list) or len(raw_scenarios) > 64:
                raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Profile {profile_name} scenarios must be a list with at most 64 entries.", status_code=422)
            normalized_scenarios: list[dict[str, Any]] = []
            seen_ids: set[str] = set()
            seen_ranks: set[int] = set()
            for raw_scenario in raw_scenarios:
                scenario = cls._validate_scenario(raw_scenario, seen_ids)
                rank = int(scenario["rank"])
                if rank in seen_ranks:
                    raise AppError(
                        ErrorCode.TRAFFIC_RULE_INVALID,
                        f"Profile {profile_name} has duplicate scenario rank {rank}; ranks must be unique so arbitration has one unambiguous top scenario.",
                        status_code=422,
                    )
                seen_ranks.add(rank)
                normalized_scenarios.append(scenario)

            normalized_profiles[profile_name.strip()] = {
                "description": str(raw_profile.get("description", ""))[:300],
                "phases": normalized_phases,
                "max_cycle_seconds": round(max_cycle, 1),
                "stale_data_seconds": round(stale, 1),
                "demand_memory_seconds": round(memory, 1),
                "rules": normalized_rules,
                "scenarios": normalized_scenarios,
            }
        config["profiles"] = normalized_profiles
        config["active_profile"] = active_profile
        return config

    @classmethod
    def _validate_scenario(cls, raw: Any, seen_ids: set[str]) -> dict[str, Any]:
        if not isinstance(raw, dict):
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "Each signal scenario must be an object.", status_code=422)
        scenario_id = str(raw.get("id", "")).strip()
        if not 1 <= len(scenario_id) <= 64 or not all(char.isalnum() or char in "._-" for char in scenario_id):
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "Scenario id must contain 1-64 letters, numbers, dots, dashes, or underscores.", status_code=422)
        if scenario_id in seen_ids:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Duplicate scenario id: {scenario_id}", status_code=422)
        seen_ids.add(scenario_id)
        try:
            rank = int(raw.get("rank", 100))
            persistence = float(raw.get("persistence_seconds", 0.0) or 0.0)
            cooldown = float(raw.get("cooldown_seconds", 0.0) or 0.0)
        except (TypeError, ValueError) as exc:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Scenario {scenario_id} timing/rank values are invalid.", status_code=422) from exc
        if not 1 <= rank <= 10000 or not 0.0 <= persistence <= 120.0 or not 0.0 <= cooldown <= 600.0:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Scenario {scenario_id} rank/persistence/cooldown is outside supported limits.", status_code=422)
        match = str(raw.get("match", "all"))
        if match not in ALLOWED_MATCH:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Scenario {scenario_id} match must be all or any.", status_code=422)
        conditions = raw.get("conditions")
        if not isinstance(conditions, list) or not 1 <= len(conditions) <= 8:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Scenario {scenario_id} must define 1-8 conditions.", status_code=422)
        normalized_conditions = [cls._validate_condition(scenario_id, condition) for condition in conditions]
        action = cls._validate_action(scenario_id, raw.get("action"))
        return {
            "id": scenario_id,
            "label": str(raw.get("label") or scenario_id.replace("_", " ").title())[:120],
            "enabled": bool(raw.get("enabled", True)),
            "rank": rank,
            "match": match,
            "conditions": normalized_conditions,
            "persistence_seconds": round(persistence, 2),
            "cooldown_seconds": round(cooldown, 1),
            "action": action,
        }

    @classmethod
    def _validate_condition(cls, scenario_id: str, raw: Any) -> dict[str, Any]:
        if not isinstance(raw, dict):
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Scenario {scenario_id} condition must be an object.", status_code=422)
        source = str(raw.get("source", "metric"))
        operator = str(raw.get("operator", "gte"))
        if source not in ALLOWED_CONDITION_SOURCES or operator not in ALLOWED_OPERATORS:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Scenario {scenario_id} condition source/operator is invalid.", status_code=422)
        try:
            threshold = float(raw.get("threshold", 0.0) or 0.0)
        except (TypeError, ValueError) as exc:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Scenario {scenario_id} condition threshold is invalid.", status_code=422) from exc
        if not -100000.0 <= threshold <= 100000.0:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Scenario {scenario_id} condition threshold is outside supported limits.", status_code=422)
        if source == "metric":
            metric = str(raw.get("metric", ""))
            if metric not in ALLOWED_METRICS:
                raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Scenario {scenario_id} metric condition is invalid.", status_code=422)
            return {"source": source, "metric": metric, "operator": operator, "threshold": round(threshold, 2)}
        zone_id = str(raw.get("zone_id", "")).strip()
        class_name = str(raw.get("class_name", "")).strip()
        if not 1 <= len(zone_id) <= 64 or not 1 <= len(class_name) <= 64:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Scenario {scenario_id} zone/class condition requires zone_id and class_name.", status_code=422)
        return {
            "source": source,
            "zone_id": zone_id,
            "class_name": class_name,
            "operator": operator,
            "threshold": round(threshold, 2),
        }

    @classmethod
    def _validate_action(cls, scenario_id: str, raw: Any) -> dict[str, Any]:
        if not isinstance(raw, dict):
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Scenario {scenario_id} action must be an object.", status_code=422)
        action_type = str(raw.get("type", "hold_current_phase"))
        if action_type not in ALLOWED_ACTIONS:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Scenario {scenario_id} action type is invalid.", status_code=422)
        try:
            adjustment = float(raw.get("adjustment_seconds", 0.0) or 0.0)
        except (TypeError, ValueError) as exc:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Scenario {scenario_id} adjustment is invalid.", status_code=422) from exc
        if not 0.0 <= adjustment <= 60.0:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Scenario {scenario_id} adjustment must be between 0 and 60 seconds.", status_code=422)
        targets = raw.get("target_phases", [])
        if not isinstance(targets, list) or not targets or any(target not in PHASE_KEYS for target in targets):
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Scenario {scenario_id} target phases are invalid.", status_code=422)
        request_service = raw.get("request_service")
        if request_service == "":
            request_service = None
        if request_service not in ALLOWED_REQUEST_SERVICES:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Scenario {scenario_id} request_service is invalid.", status_code=422)
        if action_type == "request_next_phase" and request_service is None:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Scenario {scenario_id} request_next_phase requires pedestrian or vehicle service.", status_code=422)
        return {
            "type": action_type,
            "adjustment_seconds": round(adjustment, 1),
            "target_phases": list(dict.fromkeys(targets)),
            "request_service": request_service,
        }

    def _active_profile_locked(self, config: dict[str, Any]) -> dict[str, Any]:
        return config["profiles"][config["active_profile"]]

    def _initialize_phase_locked(self, clock: float) -> None:
        config = self._load_config_locked()
        profile = self._active_profile_locked(config)
        phase_key = PHASE_SEQUENCE[self._phase_index][0]
        phase = profile["phases"][phase_key]
        self._phase_started_clock = clock
        self._phase_base_seconds = float(phase["base_seconds"])
        self._phase_duration_seconds = self._phase_base_seconds
        self._applied_rule_ids.clear()
        self._last_active_rules = []
        self._winning_scenario_id = None
        self._winning_scenario_label = None

    def _advance_phase_locked(self, clock: float) -> None:
        if clock + 1e-9 < self._last_clock_s:
            self._reset_runtime_locked(0.0)
        self._last_clock_s = clock
        if self._reinitialize_pending:
            self._reinitialize_pending = False
            self._cycle_started_clock = clock
            self._initialize_phase_locked(clock)
            self._record_event_locked("policy_reinitialized", {"phase_key": PHASE_SEQUENCE[self._phase_index][0]})
            return
        if self._incident_hold:
            return
        if self._resume_after_incident:
            self._resume_after_incident = False
            self._cycle_started_clock = clock
            self._initialize_phase_locked(clock)
            self._record_event_locked("incident_recovery", {"phase_key": PHASE_SEQUENCE[self._phase_index][0]})
            return
        guard = 0
        while clock - self._phase_started_clock >= self._phase_duration_seconds and guard < 12:
            next_clock = self._phase_started_clock + self._phase_duration_seconds
            previous_key = PHASE_SEQUENCE[self._phase_index][0]
            self._phase_index = (self._phase_index + 1) % len(PHASE_SEQUENCE)
            if self._phase_index == 0:
                self._cycle_started_clock = next_clock
                self._pending_request = None
            self._initialize_phase_locked(next_clock)
            current_key = PHASE_SEQUENCE[self._phase_index][0]
            self._record_event_locked("phase_changed", {"from": previous_key, "to": current_key})
            guard += 1

    def _observation_values_locked(self, profile: dict[str, Any]) -> tuple[dict[str, Any], bool, str | None]:
        now = time.monotonic()
        fresh = self._last_observation_monotonic is not None and now - self._last_observation_monotonic <= float(profile["stale_data_seconds"])
        memory_window = float(profile["demand_memory_seconds"])

        def memory_count(memory: _DemandMemory, current: int) -> int:
            if current > 0:
                return current
            if memory.last_seen_monotonic is not None and now - memory.last_seen_monotonic <= memory_window:
                return max(1, memory.last_count)
            return 0

        base = deepcopy(self._last_observation)
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

    @staticmethod
    def _memory_age(memory: _DemandMemory, now: float, memory_window: float) -> float:
        if memory.first_seen_monotonic is None:
            return 0.0
        if memory.last_seen_monotonic is not None and now - memory.last_seen_monotonic <= memory_window:
            return max(0.0, now - memory.first_seen_monotonic)
        return 0.0

    def _condition_value_locked(self, config: dict[str, Any], condition: dict[str, Any], values: dict[str, Any]) -> tuple[bool, float, str]:
        if condition["source"] == "metric":
            metric = condition["metric"]
            if metric in TEST_ONLY_METRICS and config["mode"] != "test":
                return False, 0.0, "manual/simulation Test-mode source only"
            raw = values.get(metric, 0)
            value = 1.0 if raw is True else 0.0 if raw is False else float(raw or 0.0)
            return True, value, metric.replace("_", " ")
        zone_counts = values.get("zone_class_counts", {})
        if not isinstance(zone_counts, dict) or condition["zone_id"] not in zone_counts:
            return False, 0.0, f"zone {condition['zone_id']} is not present in the current observation"
        class_counts = zone_counts.get(condition["zone_id"], {})
        if not isinstance(class_counts, dict):
            class_counts = {}
        class_name = condition["class_name"]
        if class_name == "*":
            value = float(sum(max(0, int(item or 0)) for item in class_counts.values()))
            label = f"all classes in {condition['zone_id']}"
        else:
            value = float(max(0, int(class_counts.get(class_name, 0) or 0)))
            label = f"{class_name} in {condition['zone_id']}"
        return True, value, label

    def _scenario_match_locked(self, config: dict[str, Any], scenario: dict[str, Any], values: dict[str, Any]) -> tuple[bool, bool, list[dict[str, Any]], str]:
        details: list[dict[str, Any]] = []
        available_results: list[bool] = []
        unavailable = 0
        for condition in scenario["conditions"]:
            available, value, label = self._condition_value_locked(config, condition, values)
            matched = available and _compare(condition["operator"], value, float(condition["threshold"]))
            details.append(
                {
                    "source": condition["source"],
                    "label": label,
                    "operator": condition["operator"],
                    "threshold": condition["threshold"],
                    "observed": round(value, 2),
                    "matched": matched,
                    "available": available,
                }
            )
            if available:
                available_results.append(matched)
            else:
                unavailable += 1
        if scenario["match"] == "all":
            if unavailable:
                return False, False, details, "one or more required conditions are unavailable"
            matched = all(available_results)
        else:
            matched = any(available_results)
            if not matched and unavailable and not available_results:
                return False, False, details, "all scenario conditions are unavailable"
        return True, matched, details, "conditions matched" if matched else "conditions did not match"

    def _evaluate_scenario_candidates_locked(
        self,
        config: dict[str, Any],
        profile: dict[str, Any],
        phase_key: str,
        values: dict[str, Any],
        *,
        clock: float,
        fresh: bool,
        mutate: bool,
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        statuses: list[dict[str, Any]] = []
        candidates: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for scenario in sorted(profile["scenarios"], key=lambda item: (int(item["rank"]), str(item["id"]))):
            state = "inactive"
            reason = "conditions did not match"
            condition_details: list[dict[str, Any]] = []
            condition_matched = False
            eligible = False
            if not scenario["enabled"]:
                reason = "scenario disabled"
                self._rule_condition_since.pop(scenario["id"], None) if mutate else None
            elif config["mode"] == "fixed":
                state = "suppressed"
                reason = "Fixed mode does not execute adaptive scenarios"
            elif not fresh:
                state = "suppressed"
                reason = "adaptive observations are stale or unavailable"
            else:
                available, condition_matched, condition_details, reason = self._scenario_match_locked(config, scenario, values)
                if not available:
                    state = "unavailable"
                elif condition_matched:
                    if mutate:
                        since = self._rule_condition_since.setdefault(scenario["id"], clock)
                    else:
                        since = clock - float(scenario["persistence_seconds"])
                    stable_for = max(0.0, clock - since)
                    persistence = float(scenario["persistence_seconds"])
                    if stable_for + 1e-9 < persistence:
                        state = "inactive"
                        reason = f"condition stabilizing ({stable_for:.1f}/{persistence:.1f}s)"
                    elif phase_key not in scenario["action"]["target_phases"]:
                        state = "suppressed"
                        reason = f"triggered, but action is not enabled during {phase_key}"
                    elif scenario["id"] in self._applied_rule_ids:
                        state = "triggered"
                        reason = "already applied for the current phase; remains the ranked active scenario"
                        eligible = True
                    else:
                        last = self._rule_last_applied_clock.get(scenario["id"])
                        cooldown = float(scenario["cooldown_seconds"])
                        if last is not None and clock - last < cooldown and scenario["action"]["type"] != "hold_current_phase":
                            state = "suppressed"
                            reason = f"cooldown active ({cooldown - (clock - last):.1f}s remaining)"
                        else:
                            state = "triggered"
                            reason = "triggered and eligible for rank arbitration"
                            eligible = True
                elif mutate:
                    self._rule_condition_since.pop(scenario["id"], None)
            status = {
                "scenario_id": scenario["id"],
                "rule_id": scenario["id"],
                "label": scenario["label"],
                "rank": scenario["rank"],
                "priority": 10001 - int(scenario["rank"]),
                "state": state,
                "reason": reason,
                "trigger": "scenario",
                "threshold": None,
                "stable_for_seconds": round(max(0.0, clock - self._rule_condition_since.get(scenario["id"], clock)), 1) if mutate else 0.0,
                "condition_match": scenario["match"],
                "conditions": condition_details,
                "action": deepcopy(scenario["action"]),
                "eligible": eligible,
                "matched": condition_matched,
            }
            statuses.append(status)
            if eligible:
                candidates.append((scenario, status))
        winner = candidates[0][0] if candidates else None
        winner_id = winner["id"] if winner else None
        for _, status in candidates:
            if status["scenario_id"] == winner_id:
                status["state"] = "winner"
                status["reason"] = "highest-ranked eligible triggered scenario"
            else:
                status["state"] = "suppressed"
                status["reason"] = f"higher-ranked scenario {winner_id} won arbitration"
        return statuses, winner

    def _evaluate_rules_locked(self, clock: float, *, apply: bool) -> None:
        config = self._load_config_locked()
        profile = self._active_profile_locked(config)
        phase_key = PHASE_SEQUENCE[self._phase_index][0]
        values, fresh, fallback_reason = self._observation_values_locked(profile)
        if config["mode"] == "fixed":
            fresh = False
            fallback_reason = "Fixed mode uses the configured normal timings only."
        statuses, winner = self._evaluate_scenario_candidates_locked(config, profile, phase_key, values, clock=clock, fresh=fresh, mutate=True)
        self._last_rule_status = statuses
        self._winning_scenario_id = winner["id"] if winner else None
        self._winning_scenario_label = winner["label"] if winner else None
        self._last_active_rules = [winner["id"]] if winner else []
        if winner and apply and not config["dry_run"]:
            elapsed = max(0.0, clock - self._phase_started_clock)
            phase_limits = profile["phases"][phase_key]
            self._apply_scenario_locked(winner, clock, elapsed, phase_limits, profile, phase_key)
        if not fresh and fallback_reason:
            self._winning_scenario_id = None
            self._winning_scenario_label = None
            self._last_active_rules = []

    def _cycle_phase_cap_locked(self, profile: dict[str, Any], phase_key: str) -> float:
        index = next(i for i, (key, _) in enumerate(PHASE_SEQUENCE) if key == phase_key)
        elapsed_before_phase = max(0.0, self._phase_started_clock - self._cycle_started_clock)
        later_base = sum(float(profile["phases"][key]["base_seconds"]) for key, _ in PHASE_SEQUENCE[index + 1 :])
        remaining_for_current = float(profile["max_cycle_seconds"]) - elapsed_before_phase - later_base
        return max(float(profile["phases"][phase_key]["min_seconds"]), remaining_for_current)

    def _apply_scenario_locked(
        self,
        scenario: dict[str, Any],
        clock: float,
        elapsed: float,
        phase_limits: dict[str, Any],
        profile: dict[str, Any],
        phase_key: str,
    ) -> None:
        scenario_id = scenario["id"]
        action = scenario["action"]
        action_type = action["type"]
        adjustment = float(action["adjustment_seconds"])
        previous = self._phase_duration_seconds
        if action["request_service"]:
            self._pending_request = action["request_service"]
        if action_type == "incident_hold":
            if not self._incident_hold:
                self._incident_hold = True
                self._record_event_locked("incident_hold_started", {"scenario_id": scenario_id})
            self._rule_last_applied_clock[scenario_id] = clock
            return
        if action_type != "hold_current_phase" and scenario_id in self._applied_rule_ids:
            return
        if action_type == "hold_current_phase":
            reserve = adjustment
            if self._phase_duration_seconds - elapsed < reserve:
                phase_cap = min(float(phase_limits["max_seconds"]), self._cycle_phase_cap_locked(profile, phase_key))
                self._phase_duration_seconds = min(phase_cap, max(self._phase_duration_seconds, elapsed + reserve))
        elif action_type == "extend_current_phase":
            self._phase_duration_seconds += adjustment
        elif action_type == "reduce_current_phase":
            self._phase_duration_seconds -= adjustment
        elif action_type == "request_next_phase":
            # Request service sooner while still traversing the protected sequence.
            self._phase_duration_seconds = elapsed + 0.2
        phase_cap = min(float(phase_limits["max_seconds"]), self._cycle_phase_cap_locked(profile, phase_key))
        self._phase_duration_seconds = max(float(phase_limits["min_seconds"]), min(phase_cap, self._phase_duration_seconds))
        self._phase_duration_seconds = max(self._phase_duration_seconds, elapsed + 0.2)
        self._rule_last_applied_clock[scenario_id] = clock
        if action_type != "hold_current_phase":
            self._applied_rule_ids.add(scenario_id)
        if abs(self._phase_duration_seconds - previous) > 0.05 or action_type == "request_next_phase":
            self._record_scenario_applied_locked(scenario, previous, self._phase_duration_seconds, clock)

    def _record_scenario_applied_locked(self, scenario: dict[str, Any], previous: float, effective: float, clock: float) -> None:
        self._record_event_locked(
            "rule_applied",
            {
                "rule_id": scenario["id"],
                "scenario_id": scenario["id"],
                "scenario_label": scenario["label"],
                "rank": scenario["rank"],
                "action": scenario["action"]["type"],
                "phase_key": PHASE_SEQUENCE[self._phase_index][0],
                "previous_duration_seconds": round(previous, 1),
                "effective_duration_seconds": round(effective, 1),
                "simulation_clock_seconds": round(clock, 1),
            },
        )

    def _status_locked(self, clock: float) -> dict[str, Any]:
        config = self._load_config_locked()
        profile = self._active_profile_locked(config)
        phase_key, phase = PHASE_SEQUENCE[self._phase_index]
        values, fresh, fallback_reason = self._observation_values_locked(profile)
        if config["mode"] == "fixed":
            fresh = False
            fallback_reason = "Fixed mode uses the configured normal timings only."
        elapsed = max(0.0, clock - self._phase_started_clock)
        remaining = 0.0 if self._incident_hold else max(0.0, self._phase_duration_seconds - elapsed)
        next_index = (self._phase_index + 1) % len(PHASE_SEQUENCE)
        next_key, next_phase = PHASE_SEQUENCE[next_index]
        cycle_base = sum(float(profile["phases"][key]["base_seconds"]) for key in PHASE_KEYS)
        effective_phase = "all_red" if self._incident_hold else phase
        return {
            "phase_key": "incident_all_red" if self._incident_hold else phase_key,
            "phase": effective_phase,
            "base_duration_seconds": self._phase_base_seconds,
            "effective_duration_seconds": round(self._phase_duration_seconds, 1),
            "elapsed_seconds": round(elapsed, 1),
            "seconds_remaining": round(remaining, 1),
            "next_phase_key": next_key,
            "next_phase": next_phase,
            "vehicle_go": effective_phase == "vehicle_green",
            "pedestrian_walk": effective_phase == "pedestrian_green",
            "pedestrian_clear": effective_phase == "pedestrian_flashing",
            "mode": config["mode"],
            "dry_run": config["dry_run"],
            "active_profile": config["active_profile"],
            "base_cycle_seconds": round(cycle_base, 1),
            "max_cycle_seconds": profile["max_cycle_seconds"],
            "data_fresh": fresh,
            "fallback_reason": fallback_reason,
            "pending_request": self._pending_request,
            "incident_hold": self._incident_hold,
            "winning_scenario_id": self._winning_scenario_id,
            "winning_scenario_label": self._winning_scenario_label,
            "active_rules": list(self._last_active_rules),
            "active_scenarios": list(self._last_active_rules),
            "rule_status": deepcopy(self._last_rule_status),
            "scenario_status": deepcopy(self._last_rule_status),
            "observations": deepcopy(values),
            "test_inputs": deepcopy(self._test_inputs),
            "prototype_only": True,
        }

    def _record_event_locked(self, event_type: str, details: dict[str, Any]) -> None:
        event = {"timestamp_ms": int(time.time() * 1000), "event_type": event_type, "details": details}
        try:
            self._history_path.parent.mkdir(parents=True, exist_ok=True)
            with self._history_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, separators=(",", ":")) + "\n")
        except OSError:
            logger.warning("Signal decision history write failed", exc_info=True)

    def _read_history_locked(self, limit: int) -> list[dict[str, Any]]:
        if not self._history_path.is_file():
            return []
        try:
            lines = self._history_path.read_text(encoding="utf-8").splitlines()[-limit:]
        except OSError as exc:
            raise AppError(ErrorCode.SETTINGS_READ_FAILED, "Failed to read signal decision history.", status_code=500) from exc
        events: list[dict[str, Any]] = []
        for line in lines:
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                events.append(payload)
        return events

    def _relative_history_path(self) -> str:
        try:
            return str(self._history_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
        except ValueError:
            return str(self._history_path)


signal_rules_service = SignalRulesService()
