from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
from threading import RLock
import types

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "pc-studio" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


class _AppError(Exception):
    def __init__(self, code, message=None, *, status_code=400, details=None):
        self.code = code
        self.message = message or str(code)
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


exceptions = types.ModuleType("app.core.exceptions")
exceptions.AppError = _AppError
sys.modules["app.core.exceptions"] = exceptions

json_store = types.ModuleType("app.core.json_store")
json_store.read_json = lambda path: json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json_atomic(path, payload, *, indent=2):
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=indent) + "\n", encoding="utf-8")


json_store.write_json_atomic = _write_json_atomic
sys.modules["app.core.json_store"] = json_store

logging_config = types.ModuleType("app.core.logging_config")
import logging

logging_config.get_logger = lambda name: logging.getLogger(name)
sys.modules["app.core.logging_config"] = logging_config

signal_rules = types.ModuleType("app.services.signal_rules")


class _SignalRulesService:
    pass


class _SignalRulesSingleton:
    def get_config(self):
        return _policy_config()


signal_rules.PHASE_SEQUENCE = (
    ("vehicle_green", "vehicle_green"),
    ("vehicle_yellow", "vehicle_yellow"),
    ("all_red_to_pedestrian", "all_red"),
    ("pedestrian_green", "pedestrian_green"),
    ("pedestrian_flashing", "pedestrian_flashing"),
    ("all_red_to_vehicle", "all_red"),
)
signal_rules.SignalRulesService = _SignalRulesService
signal_rules.signal_rules_service = _SignalRulesSingleton()
sys.modules["app.services.signal_rules"] = signal_rules

intersection_network = types.ModuleType("app.services.intersection_network")
intersection_network.intersection_network_service = types.SimpleNamespace(get=lambda: _network_config())
sys.modules["app.services.intersection_network"] = intersection_network

zones = types.ModuleType("app.services.zones")
zones.zone_service = types.SimpleNamespace(zones=lambda: _zones())
sys.modules["app.services.zones"] = zones

from app.core.error_codes import ErrorCode
from app.services.network_simulation_experiments import (
    NetworkSimulationExperimentService,
    REGULAR_VEHICLE_CLASSES,
    _BenchmarkSignalRulesService,
    _arrival_plan,
    _normalize_vehicle_class,
)


def _policy_config() -> dict:
    return {
        "mode": "adaptive",
        "dry_run": False,
        "active_profile": "Normal",
        "profiles": {
            "Normal": {
                "stale_data_seconds": 5,
                "demand_memory_seconds": 5,
            }
        },
    }


def _network_config() -> dict:
    return {
        "schema_version": 1,
        "active_intersection_id": "A",
        "intersections": [
            {
                "id": "A",
                "label": "Upstream A",
                "enabled": True,
                "source_ids": ["cam_a"],
                "zone_ids": ["queue_a", "ped_a"],
                "signal_profile": "Normal",
            },
            {
                "id": "B",
                "label": "Downstream B",
                "enabled": True,
                "source_ids": ["cam_b"],
                "zone_ids": ["queue_b", "ped_b"],
                "signal_profile": "Normal",
            },
        ],
        "links": [
            {
                "id": "A_to_B",
                "enabled": True,
                "source_intersection_id": "A",
                "destination_intersection_id": "B",
                "source_approach": "eastbound_out",
                "destination_approach": "westbound_in",
                "travel_time_seconds": 7.5,
            }
        ],
    }


def _zones() -> list[dict]:
    return [
        {"id": "queue_a", "type": "vehicle_queue"},
        {"id": "ped_a", "type": "pedestrian_waiting"},
        {"id": "queue_b", "type": "vehicle_queue"},
        {"id": "ped_b", "type": "pedestrian_waiting"},
    ]


class _FakeController:
    def __init__(self, config_path: Path, history_path: Path) -> None:
        config = json.loads(Path(config_path).read_text(encoding="utf-8"))
        self.mode = config["mode"]
        self.history_path = Path(history_path)
        self.observation = {}
        self.clock = 0.0
        self._class_vehicle_limits: dict[int, float] = {}

    def set_benchmark_clock(self, clock_s: float) -> None:
        self.clock = clock_s

    def observe(self, observation: dict) -> None:
        self.observation = dict(observation)

    def signal_state(self, clock_s: float) -> dict:
        cycle = clock_s % 24.0
        cycle_index = int(clock_s // 24.0)
        vehicle_limit = 12.0 if self.mode == "fixed" else 15.0
        vehicle_limit = max(vehicle_limit, self._class_vehicle_limits.get(cycle_index, 0.0))
        if cycle < vehicle_limit:
            return {
                "phase": "vehicle_green",
                "phase_key": "vehicle_green",
                "vehicle_go": True,
                "pedestrian_walk": False,
                "active_rules": [],
            }
        if 18.0 <= cycle < 22.0:
            return {
                "phase": "pedestrian_green",
                "phase_key": "pedestrian_green",
                "vehicle_go": False,
                "pedestrian_walk": True,
                "active_rules": [],
            }
        return {
            "phase": "all_red",
            "phase_key": "all_red_to_pedestrian",
            "vehicle_go": False,
            "pedestrian_walk": False,
            "active_rules": [],
        }

    def apply_network_coordination(self, **_kwargs) -> dict:
        return {"applied": False, "action": "no_op", "reason": "isolated class-aware regression", "timing_delta_seconds": 0.0}

    def apply_pedestrian_service_guard(self, **_kwargs) -> dict:
        return {"applied": False, "action": "no_op", "reason": "isolated class-aware regression", "timing_delta_seconds": 0.0}

    def apply_vehicle_class_priority(
        self,
        *,
        clock_s: float,
        class_name: str,
        waiting_count: int,
        priority_weight: float,
        max_extension_seconds: float,
        **_kwargs,
    ) -> dict:
        if waiting_count <= 0 or priority_weight <= 1.0:
            return {"applied": False, "action": "none", "reason": "neutral", "timing_delta_seconds": 0.0}
        cycle = clock_s % 24.0
        cycle_index = int(clock_s // 24.0)
        if cycle >= 15.0:
            return {
                "applied": False,
                "action": "class_vehicle_service_pending",
                "reason": "fake protected progression",
                "timing_delta_seconds": 0.0,
            }
        previous = max(15.0, self._class_vehicle_limits.get(cycle_index, 0.0))
        target = min(19.0, previous + min(max_extension_seconds, max(0.5, (priority_weight - 1.0) * waiting_count)))
        self._class_vehicle_limits[cycle_index] = target
        return {
            "applied": target > previous + 0.05,
            "action": "extend_vehicle_green_for_class",
            "reason": f"fake bounded {class_name} class priority",
            "timing_delta_seconds": round(target - previous, 1),
        }


def _factory(config_path: Path, history_path: Path):
    return _FakeController(config_path, history_path)


def _exercise_real_class_method() -> None:
    controller = object.__new__(_BenchmarkSignalRulesService)
    controller._lock = RLock()
    controller._incident_hold = False
    controller._pending_request = None
    controller._phase_started_clock = 0.0
    controller._phase_base_seconds = 15.0
    controller._phase_duration_seconds = 15.0
    controller._phase_index = 0
    events: list[tuple[str, dict]] = []
    profile = {
        "phases": {
            "vehicle_green": {"min_seconds": 5.0, "base_seconds": 15.0, "max_seconds": 24.0},
            "vehicle_yellow": {"min_seconds": 2.0, "base_seconds": 3.0, "max_seconds": 5.0},
            "all_red_to_pedestrian": {"min_seconds": 1.0, "base_seconds": 4.0, "max_seconds": 5.0},
            "pedestrian_green": {"min_seconds": 4.0, "base_seconds": 10.0, "max_seconds": 15.0},
            "pedestrian_flashing": {"min_seconds": 3.0, "base_seconds": 6.0, "max_seconds": 10.0},
            "all_red_to_vehicle": {"min_seconds": 1.0, "base_seconds": 2.0, "max_seconds": 5.0},
        },
        "max_cycle_seconds": 80.0,
    }
    controller._load_config_locked = lambda: {"mode": "adaptive"}
    controller._active_profile_locked = lambda _config: profile
    controller._cycle_phase_cap_locked = lambda _profile, _phase_key: 24.0
    controller._record_event_locked = lambda event_type, details: events.append((event_type, details))

    extended = controller.apply_vehicle_class_priority(
        clock_s=10.0,
        class_name="bus",
        waiting_count=2,
        oldest_wait_seconds=8.0,
        priority_weight=2.0,
        max_extension_seconds=4.0,
        local_pedestrians_waiting=0,
        local_pedestrians_crossing=0,
        intersection_id="A",
    )
    assert extended["applied"] is True
    assert extended["action"] == "extend_vehicle_green_for_class"
    assert 15.0 < controller._phase_duration_seconds <= 19.0
    assert events[-1][0] == "vehicle_class_priority_applied"
    assert events[-1][1]["provenance"] == "synthetic_vehicle_class_demand"

    neutral_before = controller._phase_duration_seconds
    neutral = controller.apply_vehicle_class_priority(
        clock_s=11.0,
        class_name="bus",
        waiting_count=3,
        oldest_wait_seconds=9.0,
        priority_weight=1.0,
        max_extension_seconds=4.0,
        local_pedestrians_waiting=0,
        local_pedestrians_crossing=0,
        intersection_id="A",
    )
    assert neutral["applied"] is False
    assert neutral["action"] == "neutral_class_weight"
    assert controller._phase_duration_seconds == neutral_before

    controller._phase_index = 3
    controller._phase_started_clock = 20.0
    controller._phase_base_seconds = 10.0
    controller._phase_duration_seconds = 10.0
    protected = controller.apply_vehicle_class_priority(
        clock_s=25.0,
        class_name="truck",
        waiting_count=2,
        oldest_wait_seconds=12.0,
        priority_weight=2.5,
        max_extension_seconds=4.0,
        local_pedestrians_waiting=1,
        local_pedestrians_crossing=1,
        intersection_id="A",
    )
    assert protected["applied"] is False
    assert protected["action"] == "protect_pedestrian_service"
    assert controller._phase_duration_seconds == 10.0

    controller._phase_index = 2
    controller._phase_started_clock = 30.0
    controller._phase_base_seconds = 4.0
    controller._phase_duration_seconds = 4.0
    progressed = controller.apply_vehicle_class_priority(
        clock_s=32.0,
        class_name="bus",
        waiting_count=1,
        oldest_wait_seconds=5.0,
        priority_weight=2.0,
        max_extension_seconds=4.0,
        local_pedestrians_waiting=0,
        local_pedestrians_crossing=0,
        intersection_id="A",
    )
    assert progressed["applied"] is True
    assert progressed["action"] == "request_protected_vehicle_service_for_class"
    assert controller._phase_duration_seconds >= profile["phases"]["all_red_to_pedestrian"]["min_seconds"]


def main() -> int:
    assert _normalize_vehicle_class("motorbike") == "motorcycle"
    assert _normalize_vehicle_class("lorry") == "truck"
    assert _normalize_vehicle_class("unlisted-class") == "other"
    _exercise_real_class_method()

    plan_a = _arrival_plan(
        duration_seconds=240,
        density="busy",
        seed=30030,
        transfer_share_percent=70,
        vehicle_class_profile="mixed_urban",
    )
    plan_b = _arrival_plan(
        duration_seconds=240,
        density="busy",
        seed=30030,
        transfer_share_percent=70,
        vehicle_class_profile="mixed_urban",
    )
    assert plan_a == plan_b
    classes = {event.class_name for event in plan_a["source_vehicle_arrivals"] + plan_a["destination_vehicle_arrivals"]}
    assert "bus" in classes
    assert len(classes) >= 3
    assert classes.issubset(set(REGULAR_VEHICLE_CLASSES))

    with tempfile.TemporaryDirectory(prefix="aitl_v030_class_test_") as temporary:
        service = NetworkSimulationExperimentService(
            storage_root=Path(temporary),
            config_provider=_policy_config,
            network_provider=_network_config,
            zones_provider=_zones,
            controller_factory=_factory,
        )
        kwargs = {
            "duration_seconds": 240,
            "density": "busy",
            "seed": 30030,
            "sample_interval_seconds": 2,
            "profile": None,
            "label": "V030 vehicle class regression",
            "link_id": "A_to_B",
            "transfer_share_percent": 70,
            "cooperation_lookahead_seconds": 12.0,
            "cooperation_max_extension_seconds": 5.0,
            "cooperation_min_incoming_vehicles": 1,
            "pedestrian_max_wait_seconds": 30.0,
            "pedestrian_crossing_clearance_seconds": 6.0,
            "pedestrian_clearance_reserve_seconds": 3.0,
            "vehicle_class_profile": "mixed_urban",
            "vehicle_class_priority_enabled": True,
            "vehicle_class_priority_class": "bus",
            "vehicle_class_priority_weight": 2.0,
            "vehicle_class_priority_min_waiting": 1,
            "vehicle_class_priority_max_extension_seconds": 4.0,
            "emergency_event_enabled": False,
        }
        first = service.run(**kwargs)
        second = service.run(**kwargs)

        assert first["scenario"]["comparison"] == [
            "fixed", "adaptive", "cooperative", "pedestrian_aware_cooperative", "class_aware_cooperative",
            "emergency_baseline_cooperative", "emergency_priority_cooperative",
        ]
        assert first["scenario"]["vehicle_classes"]["regular_taxonomy"] == list(REGULAR_VEHICLE_CLASSES)
        assert first["scenario"]["vehicle_classes"]["unknown_fallback"] == "other"
        assert first["scenario"]["vehicle_classes"]["profile"] == "mixed_urban"
        assert first["scenario"]["vehicle_classes"]["provenance"] == "synthetic_vehicle_class_demand"
        assert first["scenario"]["vehicle_class_priority"]["class_name"] == "bus"
        assert first["scenario"]["vehicle_class_priority"]["priority_weight"] == 2.0
        assert first["scenario"]["arrival_plan"]["source_vehicle_class_counts"]["bus"] > 0
        assert first["class_aware_cooperative"]["vehicle_class_aware_control_active"] is True
        assert first["pedestrian_aware_cooperative"]["vehicle_class_aware_control_active"] is False
        assert first["class_aware_cooperative"]["vehicle_class_priority_provenance"] == "synthetic_vehicle_class_demand"
        assert first["class_aware_cooperative"]["vehicle_class_priority_metrics"]["triggered"] > 0
        assert first["class_aware_cooperative"]["vehicle_class_priority_metrics"]["applied"] > 0
        assert first["class_aware_cooperative"]["vehicle_class_priority_events"]
        bus_network = first["class_aware_cooperative"]["network_metrics"]["vehicle_classes"]["bus"]
        assert bus_network["external_arrivals"] > 0
        assert "waiting" in bus_network and "queue_peak" in bus_network
        source_bus = first["class_aware_cooperative"]["intersections"]["A"]["metrics"]["vehicle_classes"]["bus"]
        assert source_bus["external_arrivals"] > 0
        assert "served" in source_bus and "queue" in source_bus
        selected = first["comparisons"]["class_aware_cooperative_vs_pedestrian_aware_cooperative"]["selected_class"]
        assert selected["class_name"] == "bus"
        assert selected["baseline_label"] == "pedestrian_aware_cooperative"
        assert selected["candidate_label"] == "class_aware_cooperative"

        comparable_first = {key: value for key, value in first.items() if key not in {"run_id", "created_at_ms"}}
        comparable_second = {key: value for key, value in second.items() if key not in {"run_id", "created_at_ms"}}
        assert comparable_first == comparable_second

        csv_text = service.export_csv(first["run_id"])
        header = csv_text.splitlines()[0]
        assert "class_aware_cooperative_source_phase" in header
        assert "class_aware_cooperative_vehicle_class_priority_source_action" in header
        assert "class_aware_cooperative_vehicle_class_priority_destination_weighted_waiting" in header

        disabled = service.run(**{**kwargs, "vehicle_class_priority_enabled": False, "label": "V030 disabled class priority"})
        assert disabled["class_aware_cooperative"]["vehicle_class_aware_control_active"] is False
        assert disabled["class_aware_cooperative"]["vehicle_class_priority_events"] == []
        assert disabled["class_aware_cooperative"]["network_metrics"] == disabled["pedestrian_aware_cooperative"]["network_metrics"]

        listed = service.list(10)
        assert listed["total"] >= 3
        assert service.get(first["run_id"])["run_id"] == first["run_id"]
        assert service.delete(first["run_id"])["deleted"] is True

        try:
            service.run(**{**kwargs, "vehicle_class_profile": "invalid"})
            raise AssertionError("invalid class profile should fail")
        except _AppError as exc:
            assert exc.code == ErrorCode.TRAFFIC_RULE_INVALID
            assert exc.status_code == 422

    print("V030 vehicle-class-aware cooperative network simulation regression OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
