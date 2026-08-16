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
ALLOWED_TRIGGERS = {
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

DEFAULT_PROFILE: dict[str, Any] = {
    "description": "Balanced adaptive classroom/prototype signal policy.",
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
    "rules": {
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
    },
}

DEFAULT_CONFIG: dict[str, Any] = {
    "schema_version": 1,
    "mode": "adaptive",
    "dry_run": False,
    "active_profile": "Normal",
    "profiles": {
        "Normal": deepcopy(DEFAULT_PROFILE),
        "Pedestrian Priority": {
            **deepcopy(DEFAULT_PROFILE),
            "description": "Prototype preset that serves pedestrian demand sooner.",
        },
        "Vehicle Priority": {
            **deepcopy(DEFAULT_PROFILE),
            "description": "Prototype preset that permits a larger bounded vehicle-green response.",
        },
        "Accessibility": {
            **deepcopy(DEFAULT_PROFILE),
            "description": "Prototype preset emphasizing extended pedestrian service and mobility assistance.",
        },
    },
}
DEFAULT_CONFIG["profiles"]["Pedestrian Priority"]["rules"]["heavy_pedestrian_demand"]["threshold"] = 3.0
DEFAULT_CONFIG["profiles"]["Pedestrian Priority"]["rules"]["max_pedestrian_wait"]["threshold"] = 20.0
DEFAULT_CONFIG["profiles"]["Vehicle Priority"]["phases"]["vehicle_green"]["max_seconds"] = 35.0
DEFAULT_CONFIG["profiles"]["Vehicle Priority"]["rules"]["heavy_vehicle_queue"]["adjustment_seconds"] = 7.0
DEFAULT_CONFIG["profiles"]["Accessibility"]["rules"]["mobility_assistance"]["adjustment_seconds"] = 9.0
DEFAULT_CONFIG["profiles"]["Accessibility"]["phases"]["pedestrian_flashing"]["max_seconds"] = 24.0


@dataclass
class _DemandMemory:
    first_seen_monotonic: float | None = None
    last_seen_monotonic: float | None = None
    last_count: int = 0


class SignalRulesService:
    """Persist and evaluate bounded signal-timing rules for the local simulation only."""

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
        self._pending_request: str | None = None
        self._incident_hold = False
        self._resume_after_incident = False
        self._reinitialize_pending = False
        self._cycle_started_clock = 0.0
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
                self._config_path.parent.mkdir(parents=True, exist_ok=True)
                temporary = self._config_path.with_suffix(".tmp")
                temporary.write_text(json.dumps(validated, indent=2) + "\n", encoding="utf-8")
                temporary.replace(self._config_path)
                self._config_cache = validated
                if validated["mode"] != "test":
                    # Manual accessibility/incident inputs are Test-mode sources only.
                    self._test_inputs["mobility_assistance"] = False
                    self._test_inputs["incident_person_fallen"] = False
                    self._incident_hold = False
                    self._resume_after_incident = False
                # Apply new policy values at the next simulator clock without replaying
                # elapsed time from zero. Preserve the current protected phase while
                # restarting its timing window under the saved configuration.
                self._applied_rule_ids.clear()
                self._rule_condition_since.clear()
                self._rule_last_applied_clock.clear()
                self._last_rule_status = []
                self._last_active_rules = []
                self._pending_request = None
                self._reinitialize_pending = True
                self._record_event_locked("config_saved", {"active_profile": validated["active_profile"], "mode": validated["mode"]})
        except OSError as exc:
            logger.exception("Signal-rule configuration save failed")
            raise AppError(
                ErrorCode.SETTINGS_WRITE_FAILED,
                "Failed to save the signal-rule configuration.",
                status_code=500,
            ) from exc
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
            config = self._load_config_locked()
            if self._test_inputs["incident_person_fallen"] and config["mode"] == "test" and not self._incident_hold:
                self._incident_hold = True
                self._record_event_locked("incident_hold_started", {"source": "manual_test_input"})
            return deepcopy(self._test_inputs)

    def clear_incident(self) -> dict[str, Any]:
        with self._lock:
            self._test_inputs["incident_person_fallen"] = False
            if self._incident_hold:
                self._record_event_locked("incident_hold_cleared", {"source": "manual_test_input"})
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
        self._pending_request = None
        self._incident_hold = False
        self._resume_after_incident = False
        self._reinitialize_pending = False
        self._cycle_started_clock = max(0.0, float(simulation_clock_s))
        self._pedestrian_wait = _DemandMemory()
        self._vehicle_wait = _DemandMemory()
        self._crossing = _DemandMemory()
        self._initialize_phase_locked(self._phase_started_clock)

    def observe(self, observation: dict[str, Any]) -> None:
        now = time.monotonic()
        with self._lock:
            self._last_observation = {
                "pedestrians_waiting": max(0, int(observation.get("pedestrians_waiting", 0) or 0)),
                "pedestrians_crossing": max(0, int(observation.get("pedestrians_crossing", 0) or 0)),
                "vehicles_waiting": max(0, int(observation.get("vehicles_waiting", 0) or 0)),
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
            observations = {
                "pedestrians_waiting": max(0, int(payload.get("pedestrians_waiting", 0) or 0)),
                "pedestrians_crossing": max(0, int(payload.get("pedestrians_crossing", 0) or 0)),
                "vehicles_waiting": max(0, int(payload.get("vehicles_waiting", 0) or 0)),
                "mobility_assistance": bool(payload.get("mobility_assistance", False)),
                "incident_person_fallen": bool(payload.get("incident_person_fallen", False)),
                "pedestrian_wait_seconds": max(0.0, float(payload.get("pedestrian_wait_seconds", 0.0) or 0.0)),
                "vehicle_wait_seconds": max(0.0, float(payload.get("vehicle_wait_seconds", 0.0) or 0.0)),
                "crossing_dwell_seconds": max(0.0, float(payload.get("crossing_dwell_seconds", 0.0) or 0.0)),
            }
            phase = profile["phases"][phase_key]
            effective = float(phase["base_seconds"])
            statuses: list[dict[str, Any]] = []
            for rule_id, rule in sorted(profile["rules"].items(), key=lambda item: int(item[1]["priority"]), reverse=True):
                condition = self._rule_condition_for_values(rule, observations)
                state = "active" if condition and phase_key in rule["target_phases"] else "inactive"
                reason = "trigger matched" if condition else "trigger did not match"
                if rule["trigger"] in {"mobility_assistance", "incident_person_fallen"} and config["mode"] != "test":
                    state = "unavailable"
                    reason = "manual/simulation test source only; no compatible live detector is configured"
                elif condition and phase_key not in rule["target_phases"]:
                    state = "suppressed"
                    reason = f"not applicable during {phase_key}"
                if state == "active" and rule["action"] in {"extend_current_phase", "reduce_current_phase"}:
                    adjustment = float(rule["adjustment_seconds"])
                    if rule["action"] == "reduce_current_phase":
                        effective -= adjustment
                    else:
                        effective += adjustment
                    effective = min(float(phase["max_seconds"]), max(float(phase["min_seconds"]), effective))
                statuses.append({"rule_id": rule_id, "label": rule["label"], "state": state, "reason": reason})
            return {
                "phase_key": phase_key,
                "phase": dict(PHASE_SEQUENCE)[phase_key],
                "base_duration_seconds": float(phase["base_seconds"]),
                "effective_duration_seconds": round(effective, 1),
                "rules": statuses,
                "would_enter_incident_hold": bool(observations["incident_person_fallen"] and config["mode"] == "test"),
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
            raw = json.loads(self._config_path.read_text(encoding="utf-8"))
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
            rules = raw_profile.get("rules")
            if not isinstance(rules, dict) or not rules:
                raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Profile {profile_name} must define at least one rule.", status_code=422)
            normalized_rules: dict[str, Any] = {}
            for rule_id, raw_rule in rules.items():
                if not isinstance(rule_id, str) or not 1 <= len(rule_id) <= 64 or not isinstance(raw_rule, dict):
                    raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "Rule identifiers are invalid.", status_code=422)
                trigger = str(raw_rule.get("trigger", ""))
                action = str(raw_rule.get("action", ""))
                targets = raw_rule.get("target_phases", [])
                if trigger not in ALLOWED_TRIGGERS or action not in ALLOWED_ACTIONS:
                    raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Rule {rule_id} trigger/action is invalid.", status_code=422)
                if not isinstance(targets, list) or not targets or any(target not in PHASE_KEYS for target in targets):
                    raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Rule {rule_id} target phases are invalid.", status_code=422)
                try:
                    threshold = float(raw_rule.get("threshold", 1.0))
                    persistence = float(raw_rule.get("persistence_seconds", 0.0))
                    adjustment = float(raw_rule.get("adjustment_seconds", 0.0))
                    priority = int(raw_rule.get("priority", 0))
                    cooldown = float(raw_rule.get("cooldown_seconds", 0.0))
                except (TypeError, ValueError) as exc:
                    raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Rule {rule_id} numeric values are invalid.", status_code=422) from exc
                if threshold < 0 or persistence < 0 or adjustment < 0 or adjustment > 60.0 or cooldown < 0 or not 0 <= priority <= 10000:
                    raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, f"Rule {rule_id} values are outside supported limits.", status_code=422)
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
            normalized_profiles[profile_name.strip()] = {
                "description": str(raw_profile.get("description", ""))[:300],
                "phases": normalized_phases,
                "max_cycle_seconds": round(max_cycle, 1),
                "stale_data_seconds": round(stale, 1),
                "demand_memory_seconds": round(memory, 1),
                "rules": normalized_rules,
            }
        config["profiles"] = normalized_profiles
        config["active_profile"] = active_profile
        return config

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

    def _advance_phase_locked(self, clock: float) -> None:
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

        base = dict(self._last_observation)
        base.setdefault("pedestrians_waiting", 0)
        base.setdefault("pedestrians_crossing", 0)
        base.setdefault("vehicles_waiting", 0)
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

    @staticmethod
    def _rule_condition_for_values(rule: dict[str, Any], values: dict[str, Any]) -> bool:
        trigger = rule["trigger"]
        threshold = float(rule["threshold"])
        if trigger == "low_vehicle_demand":
            return int(values.get("vehicles_waiting", 0)) <= threshold and int(values.get("pedestrians_waiting", 0)) > 0
        if trigger in {"mobility_assistance", "incident_person_fallen"}:
            return bool(values.get(trigger, False))
        return float(values.get(trigger, 0.0) or 0.0) >= threshold

    def _evaluate_rules_locked(self, clock: float, *, apply: bool) -> None:
        config = self._load_config_locked()
        profile = self._active_profile_locked(config)
        phase_key = PHASE_SEQUENCE[self._phase_index][0]
        values, fresh, fallback_reason = self._observation_values_locked(profile)
        statuses: list[dict[str, Any]] = []
        active_rule_ids: list[str] = []
        if config["mode"] == "fixed":
            fresh = False
            fallback_reason = "Fixed mode uses the configured normal timings only."
        sorted_rules = sorted(profile["rules"].items(), key=lambda item: int(item[1]["priority"]), reverse=True)
        elapsed = max(0.0, clock - self._phase_started_clock)
        phase_limits = profile["phases"][phase_key]
        for rule_id, rule in sorted_rules:
            state = "inactive"
            reason = "trigger did not match"
            available = True
            if not rule["enabled"]:
                state, reason = "inactive", "rule disabled"
                available = False
            elif rule["trigger"] in {"mobility_assistance", "incident_person_fallen"} and config["mode"] != "test":
                state, reason = "unavailable", "manual/simulation test source only; no compatible live detector is configured"
                available = False
            elif config["mode"] == "fixed":
                state, reason = "suppressed", "fixed mode"
                available = False
            elif not fresh:
                state, reason = "suppressed", fallback_reason or "stale observations"
                available = False
            condition = self._rule_condition_for_values(rule, values) if available else False
            if condition:
                since = self._rule_condition_since.setdefault(rule_id, clock)
            else:
                self._rule_condition_since.pop(rule_id, None)
                since = clock
            stable_for = max(0.0, clock - since)
            persistence = float(rule["persistence_seconds"])
            if available and rule_id in self._applied_rule_ids:
                state = "active"
                reason = "applied for the current phase; bounded timing effect is retained"
                active_rule_ids.append(rule_id)
            elif available and condition and stable_for < persistence:
                state = "inactive"
                reason = f"condition stabilizing ({stable_for:.1f}/{persistence:.1f}s)"
            elif available and condition and phase_key not in rule["target_phases"]:
                state = "suppressed"
                reason = f"trigger matched but rule does not apply during {phase_key}"
                if rule["action"] in {"request_next_phase", "reduce_current_phase"} and rule["trigger"] in {"pedestrians_waiting", "pedestrian_wait_seconds", "low_vehicle_demand"}:
                    self._pending_request = "pedestrian"
            elif available and condition:
                cooldown = float(rule["cooldown_seconds"])
                last = self._rule_last_applied_clock.get(rule_id)
                if last is not None and clock - last < cooldown and rule["action"] != "hold_current_phase":
                    state = "suppressed"
                    reason = f"cooldown active ({cooldown - (clock - last):.1f}s remaining)"
                else:
                    state = "active"
                    reason = "trigger matched"
                    active_rule_ids.append(rule_id)
                    if apply and not config["dry_run"]:
                        self._apply_rule_locked(rule_id, rule, clock, elapsed, phase_limits, profile, phase_key)
            statuses.append({
                "rule_id": rule_id,
                "label": rule["label"],
                "state": state,
                "reason": reason,
                "priority": rule["priority"],
                "trigger": rule["trigger"],
                "threshold": rule["threshold"],
                "stable_for_seconds": round(stable_for, 1),
            })
        self._last_rule_status = statuses
        self._last_active_rules = active_rule_ids

    def _cycle_phase_cap_locked(self, profile: dict[str, Any], phase_key: str) -> float:
        """Return the largest current-phase duration that still leaves base service for later phases."""
        index = next(i for i, (key, _) in enumerate(PHASE_SEQUENCE) if key == phase_key)
        elapsed_before_phase = max(0.0, self._phase_started_clock - self._cycle_started_clock)
        later_base = sum(float(profile["phases"][key]["base_seconds"]) for key, _ in PHASE_SEQUENCE[index + 1 :])
        remaining_for_current = float(profile["max_cycle_seconds"]) - elapsed_before_phase - later_base
        return max(float(profile["phases"][phase_key]["min_seconds"]), remaining_for_current)

    def _apply_rule_locked(
        self,
        rule_id: str,
        rule: dict[str, Any],
        clock: float,
        elapsed: float,
        phase_limits: dict[str, Any],
        profile: dict[str, Any],
        phase_key: str,
    ) -> None:
        action = rule["action"]
        adjustment = float(rule["adjustment_seconds"])
        previous = self._phase_duration_seconds
        if action == "incident_hold":
            if not self._incident_hold:
                self._incident_hold = True
                self._record_event_locked("incident_hold_started", {"rule_id": rule_id})
            return
        if action == "hold_current_phase":
            reserve = adjustment
            if self._phase_duration_seconds - elapsed < reserve:
                phase_cap = min(float(phase_limits["max_seconds"]), self._cycle_phase_cap_locked(profile, phase_key))
                self._phase_duration_seconds = min(phase_cap, max(self._phase_duration_seconds, elapsed + reserve))
            if self._phase_duration_seconds > previous + 0.05:
                self._record_rule_applied_locked(rule_id, previous, self._phase_duration_seconds, clock)
            return
        if rule_id in self._applied_rule_ids:
            return
        if action == "extend_current_phase":
            self._phase_duration_seconds += adjustment
        elif action == "reduce_current_phase":
            self._phase_duration_seconds -= adjustment
            self._pending_request = "pedestrian" if rule["trigger"] in {"pedestrians_waiting", "pedestrian_wait_seconds", "low_vehicle_demand"} else self._pending_request
        elif action == "request_next_phase":
            self._pending_request = "pedestrian" if rule["trigger"] in {"pedestrians_waiting", "pedestrian_wait_seconds"} else "vehicle"
        phase_cap = min(float(phase_limits["max_seconds"]), self._cycle_phase_cap_locked(profile, phase_key))
        self._phase_duration_seconds = max(float(phase_limits["min_seconds"]), min(phase_cap, self._phase_duration_seconds))
        # Never shorten a phase below time already served plus a small transition margin.
        self._phase_duration_seconds = max(self._phase_duration_seconds, elapsed + 0.2)
        self._applied_rule_ids.add(rule_id)
        self._rule_last_applied_clock[rule_id] = clock
        if abs(self._phase_duration_seconds - previous) > 0.05 or action == "request_next_phase":
            self._record_rule_applied_locked(rule_id, previous, self._phase_duration_seconds, clock)

    def _record_rule_applied_locked(self, rule_id: str, previous: float, effective: float, clock: float) -> None:
        self._record_event_locked(
            "rule_applied",
            {
                "rule_id": rule_id,
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
            "active_rules": list(self._last_active_rules),
            "rule_status": deepcopy(self._last_rule_status),
            "observations": deepcopy(values),
            "test_inputs": deepcopy(self._test_inputs),
            "prototype_only": True,
        }

    def _record_event_locked(self, event_type: str, details: dict[str, Any]) -> None:
        event = {
            "timestamp_ms": int(time.time() * 1000),
            "event_type": event_type,
            "details": details,
        }
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
