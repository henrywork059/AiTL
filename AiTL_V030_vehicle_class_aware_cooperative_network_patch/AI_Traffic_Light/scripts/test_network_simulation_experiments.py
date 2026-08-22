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


# This focused regression isolates the V027 network experiment service from the
# owner's runtime config/files. Production integration is covered by the normal
# complete-repository regression + live API smoke after patch application.
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
from app.services.network_simulation_experiments import NetworkSimulationExperimentService, _BenchmarkSignalRulesService, _arrival_plan


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
            {
                "id": "C",
                "label": "Unused C",
                "enabled": True,
                "source_ids": [],
                "zone_ids": [],
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
        self._coordination_vehicle_limits: dict[int, float] = {}

    def set_benchmark_clock(self, clock_s: float) -> None:
        self.clock = clock_s

    def observe(self, observation: dict) -> None:
        self.observation = dict(observation)

    def signal_state(self, clock_s: float) -> dict:
        # Fixed: 20 s cycle with 12 s vehicle service and 4 s pedestrian WALK.
        # Adaptive: extend vehicle service to 15 s only when vehicles are waiting.
        cycle = clock_s % 20.0
        cycle_index = int(clock_s // 20.0)
        vehicle_limit = 12.0
        active_rules = []
        if self.mode == "adaptive" and self.observation.get("vehicles_waiting", 0) > 0:
            vehicle_limit = 15.0
            active_rules = ["test_extend_vehicle"]
        vehicle_limit = max(vehicle_limit, self._coordination_vehicle_limits.get(cycle_index, 0.0))
        if cycle < vehicle_limit:
            phase = "vehicle_green"
            phase_key = "vehicle_green"
            vehicle_go = True
            pedestrian_walk = False
        elif 16.0 <= cycle < 20.0:
            phase = "pedestrian_green"
            phase_key = "pedestrian_green"
            vehicle_go = False
            pedestrian_walk = True
        else:
            phase = "all_red"
            phase_key = "all_red_to_pedestrian"
            vehicle_go = False
            pedestrian_walk = False
        return {
            "phase": phase,
            "phase_key": phase_key,
            "vehicle_go": vehicle_go,
            "pedestrian_walk": pedestrian_walk,
            "active_rules": active_rules,
        }

    def apply_network_coordination(
        self,
        *,
        clock_s: float,
        incoming_vehicle_count: int,
        earliest_arrival_eta_seconds: float | None,
        lookahead_seconds: float,
        max_extension_seconds: float,
        local_pedestrians_waiting: int,
        **_context,
    ) -> dict:
        if incoming_vehicle_count <= 0 or earliest_arrival_eta_seconds is None:
            return {"applied": False, "action": "none", "reason": "no incoming", "timing_delta_seconds": 0.0}
        if earliest_arrival_eta_seconds > lookahead_seconds:
            return {"applied": False, "action": "none", "reason": "outside lookahead", "timing_delta_seconds": 0.0}
        cycle = clock_s % 20.0
        cycle_index = int(clock_s // 20.0)
        current_limit = max(15.0, self._coordination_vehicle_limits.get(cycle_index, 0.0))
        if cycle < current_limit:
            target = min(17.0, cycle + earliest_arrival_eta_seconds + 2.0, 15.0 + max_extension_seconds)
            new_limit = max(current_limit, target)
            applied = new_limit > current_limit + 0.05
            self._coordination_vehicle_limits[cycle_index] = new_limit
            return {
                "applied": applied,
                "action": "extend_vehicle_green" if applied else "vehicle_green_already_sufficient",
                "reason": "fake bounded cooperation",
                "timing_delta_seconds": round(new_limit - current_limit, 1),
            }
        if local_pedestrians_waiting > 0:
            return {
                "applied": False,
                "action": "protect_pedestrian_service",
                "reason": "fake pedestrian guard",
                "timing_delta_seconds": 0.0,
            }
        return {
            "applied": False,
            "action": "vehicle_progression_pending",
            "reason": "fake protected progression",
            "timing_delta_seconds": 0.0,
        }


def _factory(config_path: Path, history_path: Path):
    return _FakeController(config_path, history_path)


def _exercise_real_coordination_method() -> None:
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
            "vehicle_green": {"min_seconds": 5.0, "base_seconds": 15.0, "max_seconds": 25.0},
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
    controller._cycle_phase_cap_locked = lambda _profile, _phase_key: 25.0
    controller._record_event_locked = lambda event_type, details: events.append((event_type, details))

    extension = controller.apply_network_coordination(
        clock_s=10.0,
        incoming_vehicle_count=2,
        earliest_arrival_eta_seconds=7.0,
        lookahead_seconds=12.0,
        max_extension_seconds=5.0,
        local_pedestrians_waiting=0,
        link_id="A_to_B",
        source_intersection_id="A",
        destination_intersection_id="B",
    )
    assert extension["applied"] is True
    assert extension["action"] == "extend_vehicle_green"
    assert controller._phase_duration_seconds == 19.0
    assert controller._phase_duration_seconds <= controller._phase_base_seconds + 5.0
    assert events[-1][0] == "network_coordination_applied"

    controller._phase_index = 3  # pedestrian_green
    controller._phase_started_clock = 20.0
    controller._phase_base_seconds = 10.0
    controller._phase_duration_seconds = 10.0
    protected = controller.apply_network_coordination(
        clock_s=25.0,
        incoming_vehicle_count=1,
        earliest_arrival_eta_seconds=2.0,
        lookahead_seconds=12.0,
        max_extension_seconds=5.0,
        local_pedestrians_waiting=3,
        link_id="A_to_B",
        source_intersection_id="A",
        destination_intersection_id="B",
    )
    assert protected["applied"] is False
    assert protected["action"] == "protect_pedestrian_service"
    assert controller._phase_duration_seconds == 10.0

    controller._phase_index = 2  # all_red_to_pedestrian
    controller._phase_started_clock = 30.0
    controller._phase_base_seconds = 4.0
    controller._phase_duration_seconds = 4.0
    controller._pending_request = None
    progression = controller.apply_network_coordination(
        clock_s=32.0,
        incoming_vehicle_count=1,
        earliest_arrival_eta_seconds=2.0,
        lookahead_seconds=12.0,
        max_extension_seconds=5.0,
        local_pedestrians_waiting=0,
        link_id="A_to_B",
        source_intersection_id="A",
        destination_intersection_id="B",
    )
    assert progression["applied"] is True
    assert progression["action"] == "request_protected_vehicle_progression"
    assert controller._phase_duration_seconds >= profile["phases"]["all_red_to_pedestrian"]["min_seconds"]
    assert controller._pending_request == "vehicle"


def main() -> int:
    _exercise_real_coordination_method()
    plan_a = _arrival_plan(duration_seconds=120, density="normal", seed=27027, transfer_share_percent=70)
    plan_b = _arrival_plan(duration_seconds=120, density="normal", seed=27027, transfer_share_percent=70)
    assert plan_a == plan_b, "same seed/config must generate the same exogenous arrival plan"
    assert len(plan_a["source_vehicle_arrivals"]) > 0

    with tempfile.TemporaryDirectory(prefix="aitl_v027_network_test_") as temporary:
        service = NetworkSimulationExperimentService(
            storage_root=Path(temporary),
            config_provider=_policy_config,
            network_provider=_network_config,
            zones_provider=_zones,
            controller_factory=_factory,
        )
        kwargs = {
            "duration_seconds": 120,
            "density": "normal",
            "seed": 27027,
            "sample_interval_seconds": 2,
            "profile": None,
            "label": "V027 cooperative network regression",
            "link_id": "A_to_B",
            "transfer_share_percent": 70,
            "cooperation_lookahead_seconds": 12.0,
            "cooperation_max_extension_seconds": 5.0,
            "cooperation_min_incoming_vehicles": 1,
        }
        first = service.run(**kwargs)
        second = service.run(**kwargs)

        assert first["scenario"]["kind"] == "two_intersection_network"
        assert first["scenario"]["link"]["id"] == "A_to_B"
        assert first["scenario"]["link"]["travel_time_seconds"] == 7.5
        assert first["scenario"]["source_intersection"]["id"] == "A"
        assert first["scenario"]["destination_intersection"]["id"] == "B"
        assert first["scenario"]["comparison"][:5] == ["fixed", "adaptive", "cooperative", "pedestrian_aware_cooperative", "class_aware_cooperative"]
        assert first["scenario"]["comparison"][5:] == ["emergency_baseline_cooperative", "emergency_priority_cooperative"]
        assert first["scenario"]["cooperative_control_active"] is True
        assert first["scenario"]["cooperation"]["lookahead_seconds"] == 12.0
        assert first["scenario"]["arrival_plan"]["source_vehicle_count"] > 0
        assert len(first["scenario"]["arrival_plan"]["fingerprint_sha256"]) == 64
        assert first["fixed"]["cooperative_control_active"] is False
        assert first["adaptive"]["cooperative_control_active"] is False
        assert first["cooperative"]["cooperative_control_active"] is True
        assert first["fixed"]["observation_provenance"] == "simulation"
        assert first["fixed"]["transfer_provenance"] == "synthetic_network_simulation"
        assert set(first["fixed"]["intersections"]) == {"A", "B"}
        assert set(first["adaptive"]["intersections"]) == {"A", "B"}
        assert set(first["cooperative"]["intersections"]) == {"A", "B"}

        fixed_network = first["fixed"]["network_metrics"]
        adaptive_network = first["adaptive"]["network_metrics"]
        cooperative_network = first["cooperative"]["network_metrics"]
        assert fixed_network["transfers_departed"] > 0
        assert fixed_network["transfers_arrived"] > 0
        assert adaptive_network["transfers_departed"] > 0
        assert adaptive_network["transfers_arrived"] > 0
        assert cooperative_network["transfers_departed"] > 0
        assert cooperative_network["transfers_arrived"] > 0
        assert cooperative_network["coordination"]["triggered"] > 0
        assert cooperative_network["coordination"]["applied"] > 0
        assert cooperative_network["coordination"]["green_extensions"] > 0
        assert first["cooperative"]["coordination_events"]
        first_coordination = first["cooperative"]["coordination_events"][0]
        assert first_coordination["coordination_id"].startswith("coord_A_B_")
        assert first_coordination["link_id"] == "A_to_B"
        assert first_coordination["source_intersection_id"] == "A"
        assert first_coordination["destination_intersection_id"] == "B"
        assert first_coordination["provenance"] == "synthetic_predicted_arrivals"
        assert first["cooperative"]["coordination_provenance"] == "synthetic_predicted_arrivals"
        assert fixed_network["configured_link_travel_time_seconds"] == 7.5
        arrived_events = [event for event in first["fixed"]["transfer_events"] if event["arrived_at_s"] is not None]
        assert arrived_events
        for event in arrived_events[:10]:
            assert round(event["arrived_at_s"] - event["departed_at_s"], 1) == 7.5
        assert first["fixed"]["timeline"], "network run must contain bounded timeline samples"
        assert first["adaptive"]["timeline"]
        assert first["cooperative"]["timeline"]
        assert first["comparisons"]["adaptive_vs_fixed"] == first["comparison"]
        assert "cooperative" in first["comparisons"]["cooperative_vs_adaptive"]["total_vehicle_wait"]
        assert "cooperative_direction" in first["comparisons"]["cooperative_vs_adaptive"]["total_vehicle_wait"]

        # Excluding run metadata, same seed/config must be exactly repeatable.
        assert first["scenario"] == second["scenario"]
        assert first["fixed"] == second["fixed"]
        assert first["adaptive"] == second["adaptive"]
        assert first["cooperative"] == second["cooperative"]
        assert first["comparison"] == second["comparison"]
        assert first["comparisons"] == second["comparisons"]

        listing = service.list()
        assert listing["total"] == 2
        assert listing["cooperative_control_active"] is True
        reopened = service.get(first["run_id"])
        assert reopened["run_id"] == first["run_id"]
        csv_text = service.export_csv(first["run_id"])
        assert "fixed_source_phase" in csv_text
        assert "adaptive_destination_vehicle_queue" in csv_text
        assert "fixed_source_vehicles_served" in csv_text
        assert "adaptive_destination_active_rules" in csv_text
        assert "cooperative_destination_vehicle_queue" in csv_text
        assert "cooperative_coordination_action" in csv_text

        # Thin FastAPI route integration: standard envelope/request id + CSV header.
        single_experiments = types.ModuleType("app.services.simulation_experiments")
        single_experiments.simulation_experiment_service = types.SimpleNamespace()
        sys.modules["app.services.simulation_experiments"] = single_experiments
        api_response_module = types.ModuleType("app.core.api_response")
        api_response_module.ok = lambda data, request_id=None, meta=None: {
            "ok": True,
            "data": data,
            "meta": {**(meta or {}), **({"request_id": request_id} if request_id else {})},
        }
        sys.modules["app.core.api_response"] = api_response_module
        from fastapi import FastAPI, Request
        from fastapi.testclient import TestClient
        from app.routes import experiments as experiment_routes

        experiment_routes.network_simulation_experiment_service = service
        app = FastAPI()

        @app.middleware("http")
        async def _request_id(request: Request, call_next):
            request.state.request_id = "v027-test-request"
            return await call_next(request)

        app.include_router(experiment_routes.router, prefix="/api/traffic")
        with TestClient(app) as client:
            api_response = client.post(
                "/api/traffic/network-experiments",
                json={
                    "duration_seconds": 120,
                    "density": "normal",
                    "seed": 27027,
                    "sample_interval_seconds": 2,
                    "profile": None,
                    "label": "route integration",
                    "link_id": "A_to_B",
                    "transfer_share_percent": 70,
                    "cooperation_lookahead_seconds": 12.0,
                    "cooperation_max_extension_seconds": 5.0,
                    "cooperation_min_incoming_vehicles": 1,
                },
            )
            assert api_response.status_code == 200
            envelope = api_response.json()
            assert envelope["ok"] is True
            assert envelope["meta"]["request_id"] == "v027-test-request"
            api_run_id = envelope["data"]["run_id"]
            csv_response = client.get(f"/api/traffic/network-experiments/{api_run_id}/export.csv")
            assert csv_response.status_code == 200
            assert csv_response.headers["x-request-id"] == "v027-test-request"
            assert "fixed_source_vehicles_served" in csv_response.text
            assert "cooperative_coordination_action" in csv_response.text

        try:
            service.run(**{**kwargs, "cooperation_lookahead_seconds": 0.5})
        except _AppError as exc:
            assert exc.code == ErrorCode.TRAFFIC_RULE_INVALID
            assert exc.status_code == 422
        else:
            raise AssertionError("network experiment must reject invalid cooperation lookahead")

        deleted = service.delete(first["run_id"])
        assert deleted == {"deleted": True, "run_id": first["run_id"]}

        bad_network = _network_config()
        bad_network["links"] = []
        bad_service = NetworkSimulationExperimentService(
            storage_root=Path(temporary) / "bad",
            config_provider=_policy_config,
            network_provider=lambda: bad_network,
            zones_provider=_zones,
            controller_factory=_factory,
        )
        try:
            bad_service.run(**kwargs)
        except _AppError as exc:
            assert exc.code == ErrorCode.TRAFFIC_NETWORK_INVALID
            assert exc.status_code == 422
        else:
            raise AssertionError("network experiment must reject missing enabled link")

    print("V027 cooperation regression retained under V028 OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
