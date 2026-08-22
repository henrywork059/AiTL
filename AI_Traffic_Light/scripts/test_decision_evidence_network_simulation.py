from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import types

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "pc-studio" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

# Reuse V030's isolated runtime stubs/config/fake controller. Importing the
# module does not execute its main() regression.
from test_vehicle_class_aware_network_simulation import (  # noqa: E402
    NetworkSimulationExperimentService,
    _FakeController,
    _network_config,
    _policy_config,
    _zones,
)
from app.services.decision_evidence import (  # noqa: E402
    EVIDENCE_SCHEMA_VERSION,
    build_network_decision_evidence,
    export_network_decision_evidence_csv,
)
from app.services.network_policy_arbiter import arbitrate_network_policy  # noqa: E402
from app.services.network_simulation_experiments import (  # noqa: E402
    _BenchmarkSignalRulesService,
    _NetworkModeSimulation,
)


def _timed_outcome(outcome: dict, *, previous: float = 20.0) -> dict:
    delta = float(outcome.get("timing_delta_seconds", 0.0) or 0.0)
    return {
        **outcome,
        "previous_duration_seconds": previous,
        "effective_duration_seconds": round(previous + delta, 1),
    }


_EVIDENCE_CONTROLLERS: list["_EvidenceController"] = []


class _EvidenceController(_FakeController):
    def __init__(self, config_path: Path, history_path: Path) -> None:
        super().__init__(config_path, history_path)
        self.signal_state_calls = 0
        self.snapshot_state_calls = 0
        _EVIDENCE_CONTROLLERS.append(self)

    @staticmethod
    def _decorate_state(controller: "_EvidenceController", state: dict) -> dict:
        if controller.mode == "adaptive" and state.get("phase_key") == "vehicle_green":
            state.update(
                {
                    "winning_scenario_id": "test_queue_extend",
                    "active_rules": ["test_queue_extend"],
                    "base_duration_seconds": 12.0,
                    "effective_duration_seconds": 15.0,
                    "observations": dict(getattr(controller, "observation", {})),
                    "scenario_status": [
                        {
                            "scenario_id": "test_queue_extend",
                            "state": "winner",
                            "reason": "test ranked scenario winner",
                            "action": {"type": "extend_current_phase"},
                        }
                    ],
                }
            )
        return state

    def signal_state(self, clock_s: float) -> dict:
        self.signal_state_calls += 1
        return self._decorate_state(self, dict(super().signal_state(clock_s)))

    def snapshot_state(self, clock_s: float) -> dict:
        self.snapshot_state_calls += 1
        # Bypass this class' mutating/evaluating signal_state wrapper so the
        # network runtime can prove post-advisory reads use snapshot semantics.
        return self._decorate_state(self, dict(_FakeController.signal_state(self, clock_s)))

    def apply_network_coordination(self, **kwargs) -> dict:
        return _timed_outcome(super().apply_network_coordination(**kwargs))

    def apply_pedestrian_service_guard(self, **kwargs) -> dict:
        return _timed_outcome(super().apply_pedestrian_service_guard(**kwargs))

    def apply_vehicle_class_priority(self, **kwargs) -> dict:
        return _timed_outcome(super().apply_vehicle_class_priority(**kwargs))

    def apply_emergency_priority(self, **_kwargs) -> dict:
        return {
            "applied": False,
            "decision": "defer",
            "action": "emergency_progression_pending",
            "reason": "evidence timing propagation regression",
            "timing_delta_seconds": 0.0,
            "previous_duration_seconds": 20.0,
            "effective_duration_seconds": 20.0,
        }


def _evidence_factory(config_path: Path, history_path: Path):
    return _EvidenceController(config_path, history_path)



def _synthetic_raw_result() -> dict:
    return {
        "run_id": "netexp_test",
        "scenario": {"comparison": ["cooperative"]},
        "cooperative": {
            "intersections": {
                "A": {
                    "scenario_evidence_events": [
                        {
                            "scenario_id": "queue_extend",
                            "t": 4.0,
                            "phase": "vehicle_green",
                            "phase_key": "vehicle_green",
                            "action": "extend_current_phase",
                            "applied": True,
                            "reason": "highest-ranked eligible triggered scenario",
                            "observations": {
                                "vehicles_waiting": 5,
                                "pedestrians_waiting": 0,
                                "pedestrians_crossing": 0,
                                "zone_class_counts": {"queue_a": {"bus": 2, "car": 3}},
                            },
                            "previous_duration_seconds": 15.0,
                            "effective_duration_seconds": 18.0,
                            "timing_delta_seconds": 3.0,
                            "previous_duration_seconds": 15.0,
                            "effective_duration_seconds": 18.0,
                            "provenance": "simulation_signal_controller",
                        }
                    ]
                }
            },
            "coordination_events": [
                {
                    "coordination_id": "coord_A_B_5000",
                    "t": 5.0,
                    "link_id": "A_to_B",
                    "source_intersection_id": "A",
                    "destination_intersection_id": "B",
                    "provenance": "synthetic_predicted_arrivals",
                    "destination_phase_before": "vehicle_green",
                    "destination_phase_key_before": "vehicle_green",
                    "incoming_vehicle_count": 2,
                    "earliest_arrival_eta_seconds": 6.0,
                    "action": "extend_vehicle_green",
                    "applied": True,
                    "reason": "predicted arrivals",
                    "timing_delta_seconds": 2.0,
                    "previous_duration_seconds": 12.0,
                    "effective_duration_seconds": 14.0,
                }
            ],
            "pedestrian_awareness_events": [
                {
                    "pedestrian_awareness_id": "pedaware_B_6000",
                    "t": 6.0,
                    "role": "destination",
                    "intersection_id": "B",
                    "provenance": "synthetic_pedestrian_demand",
                    "phase_before": "vehicle_green",
                    "phase_key_before": "vehicle_green",
                    "waiting_count": 3,
                    "oldest_wait_seconds": 30.0,
                    "crossing_count": 0,
                    "action": "request_pedestrian_service",
                    "applied": True,
                    "reason": "maximum wait reached",
                    "timing_delta_seconds": -2.0,
                    "previous_duration_seconds": 12.0,
                    "effective_duration_seconds": 10.0,
                },
                {
                    "pedestrian_awareness_id": "pedaware_B_6500",
                    "t": 6.5,
                    "role": "destination",
                    "intersection_id": "B",
                    "provenance": "synthetic_pedestrian_demand",
                    "phase_before": "vehicle_green",
                    "phase_key_before": "vehicle_green",
                    "waiting_count": 3,
                    "oldest_wait_seconds": 30.5,
                    "crossing_count": 0,
                    "action": "pedestrian_service_pending",
                    "applied": False,
                    "reason": "protected minimum reached",
                    "timing_delta_seconds": 0.0,
                    "previous_duration_seconds": 10.0,
                    "effective_duration_seconds": 10.0,
                }
            ],
            "vehicle_class_priority_events": [
                {
                    "vehicle_class_priority_id": "classprio_A_7000",
                    "t": 7.0,
                    "role": "source",
                    "intersection_id": "A",
                    "class_name": "bus",
                    "waiting_count": 2,
                    "oldest_wait_seconds": 9.0,
                    "priority_weight": 2.0,
                    "weighted_waiting": 4.0,
                    "min_waiting": 1,
                    "provenance": "synthetic_vehicle_class_demand",
                    "phase_before": "vehicle_green",
                    "phase_key_before": "vehicle_green",
                    "action": "extend_vehicle_green",
                    "applied": True,
                    "reason": "configured bus priority",
                    "timing_delta_seconds": 1.0,
                    "previous_duration_seconds": 14.0,
                    "effective_duration_seconds": 15.0,
                }
            ],
            "emergency_priority_events": [
                {
                    "emergency_priority_id": "emgprio_A_8000",
                    "emergency_event_id": "emergency_1",
                    "t": 8.0,
                    "role": "source_priority",
                    "intersection_id": "A",
                    "link_id": "A_to_B",
                    "vehicle_type": "ambulance",
                    "provenance": "simulated_configured_emergency_event",
                    "phase_before": "pedestrian_flashing",
                    "phase_key_before": "pedestrian_flashing",
                    "eta_seconds": 0.0,
                    "decision": "deny",
                    "action": "protect_active_pedestrian_crossing",
                    "applied": False,
                    "reason": "active pedestrian crossing blocks emergency timing change",
                    "timing_delta_seconds": 0.0,
                    "previous_duration_seconds": 9.0,
                    "effective_duration_seconds": 9.0,
                }
            ],
            "emergency_lifecycle_events": [
                {
                    "emergency_event_id": "emergency_1",
                    "t": 9.0,
                    "event_type": "activated",
                    "status": "source_waiting",
                    "vehicle_type": "ambulance",
                    "source_intersection_id": "A",
                    "destination_intersection_id": "B",
                    "link_id": "A_to_B",
                    "provenance": "simulated_configured_emergency_event",
                }
            ],
        },
    }


def _assert_schema_projection() -> None:
    first = build_network_decision_evidence(_synthetic_raw_result())
    second = build_network_decision_evidence(_synthetic_raw_result())
    assert first == second
    assert first["schema_version"] == EVIDENCE_SCHEMA_VERSION == 1
    assert first["record_count"] == 7
    assert first["applied_count"] == 4
    assert first["categories"] == {
        "cooperation": 1,
        "emergency_lifecycle": 1,
        "emergency_priority": 1,
        "pedestrian": 2,
        "scenario": 1,
        "vehicle_class": 1,
    }
    records = first["records"]
    assert len({record["evidence_id"] for record in records}) == len(records)
    assert all("run_id" not in record for record in records), "volatile run metadata must not break repeatability"
    scenario = next(record for record in records if record["trigger_category"] == "scenario")
    assert scenario["context"]["local"]["vehicles_waiting"] == 5
    assert scenario["context"]["vehicle_class"]["zone_class_counts"]["queue_a"]["bus"] == 2
    pending_pedestrian = next(
        record
        for record in records
        if record["trigger_category"] == "pedestrian" and record["action"] == "pedestrian_service_pending"
    )
    assert pending_pedestrian["decision"] == "defer"
    timed_categories = {"scenario", "cooperation", "pedestrian", "vehicle_class", "emergency_priority"}
    for record in records:
        if record["trigger_category"] not in timed_categories:
            continue
        assert record["timing"]["previous_duration_seconds"] is not None
        assert record["timing"]["effective_duration_seconds"] is not None

    emergency = next(record for record in records if record["trigger_category"] == "emergency_priority")
    assert emergency["decision"] == "deny"
    assert emergency["context"]["pedestrian"]["protected"] is True
    assert emergency["provenance"] == "simulated_configured_emergency_event"
    csv_text = export_network_decision_evidence_csv(first)
    assert "evidence_id,mode,t_seconds,trigger_category" in csv_text
    assert "protect_active_pedestrian_crossing" in csv_text
    assert "synthetic_vehicle_class_demand" in csv_text


def _assert_cross_layer_pedestrian_lock() -> None:
    class _Runtime:
        def __init__(self, intersection_id: str) -> None:
            self.intersection_id = intersection_id
            self.coordination_calls = 0
            self.class_calls = 0

        def pedestrian_context(self, _clock_s: float) -> dict:
            return {"waiting_count": 2, "oldest_wait_seconds": 31.0, "crossing_count": 0}

        def vehicle_class_context(self, class_name: str, _clock_s: float) -> dict:
            return {"class_name": class_name, "waiting_count": 3, "oldest_wait_seconds": 12.0}

        def apply_coordination(self, **_kwargs) -> dict:
            self.coordination_calls += 1
            raise AssertionError("ordinary cooperation must be suppressed by the pedestrian max-wait lock")

        def apply_vehicle_class_priority(self, **_kwargs) -> dict:
            self.class_calls += 1
            raise AssertionError("ordinary class priority must be suppressed by the pedestrian max-wait lock")

    simulation = object.__new__(_NetworkModeSimulation)
    simulation.mode = "class_aware_cooperative"
    simulation.pedestrian_max_wait_seconds = 30.0
    simulation.cooperation_lookahead_seconds = 12.0
    simulation.cooperation_max_extension_seconds = 5.0
    simulation.cooperation_min_incoming_vehicles = 1
    simulation.vehicle_class_priority_enabled = True
    simulation.vehicle_class_priority_class = "bus"
    simulation.vehicle_class_priority_weight = 2.0
    simulation.vehicle_class_priority_min_waiting = 1
    simulation.vehicle_class_priority_max_extension_seconds = 4.0
    simulation.link = {"id": "A_to_B"}
    simulation.source = types.SimpleNamespace(intersection_id="A")
    simulation.destination = _Runtime("B")
    simulation.coordination_evaluations = 0
    simulation.coordination_triggered = 0
    simulation.coordination_applied = 0
    simulation.coordination_green_extensions = 0
    simulation.coordination_progression_requests = 0
    simulation.coordination_pedestrian_protections = 0
    simulation.coordination_seconds_added = 0.0
    simulation.coordination_seconds_reduced = 0.0
    simulation.coordination_events = []
    simulation._latest_coordination = {}
    simulation.vehicle_class_priority_evaluations = 0
    simulation.vehicle_class_priority_triggered = 0
    simulation.vehicle_class_priority_applied = 0
    simulation.vehicle_class_priority_pedestrian_protections = 0
    simulation.vehicle_class_priority_seconds_added = 0.0
    simulation.vehicle_class_priority_seconds_reduced = 0.0
    simulation.vehicle_class_priority_events = []
    simulation._latest_vehicle_class_priority = {"source": {}, "destination": {}}
    simulation._cooperation_advisory = lambda _clock_s: {
        "incoming_vehicle_count": 3,
        "earliest_arrival_eta_seconds": 4.0,
        "lookahead_seconds": 12.0,
        "max_extension_seconds": 5.0,
        "link_id": "A_to_B",
        "source_intersection_id": "A",
        "destination_intersection_id": "B",
    }
    signal = {
        "phase": "vehicle_green",
        "phase_key": "vehicle_green",
        "effective_duration_seconds": 12.0,
    }
    arbitration = arbitrate_network_policy(
        incident_hold=False,
        phase_key="vehicle_green",
        pedestrian_waiting=2,
        pedestrian_crossing=0,
        oldest_pedestrian_wait_seconds=31.0,
        pedestrian_max_wait_seconds=30.0,
        emergency_priority_active=False,
        vehicle_class_priority_active=True,
        cooperation_active=True,
    )
    assert arbitration.owner == "pedestrian_max_wait"
    assert arbitration.conflict is True

    simulation._evaluate_cooperation(31.0, signal, arbitration=arbitration)
    cooperation = simulation.coordination_events[-1]
    assert cooperation["action"] == "defer_for_pedestrian_max_wait"
    assert cooperation["applied"] is False
    assert cooperation["previous_duration_seconds"] == 12.0
    assert cooperation["effective_duration_seconds"] == 12.0
    assert simulation.destination.coordination_calls == 0

    simulation._evaluate_vehicle_class_priority(
        31.0, simulation.destination, signal, role="destination", arbitration=arbitration
    )
    class_event = simulation.vehicle_class_priority_events[-1]
    assert class_event["action"] == "defer_for_pedestrian_max_wait"
    assert class_event["applied"] is False
    assert class_event["previous_duration_seconds"] == 12.0
    assert class_event["effective_duration_seconds"] == 12.0
    assert simulation.destination.class_calls == 0

    projected = build_network_decision_evidence(
        {
            "scenario": {"comparison": ["class_aware_cooperative"]},
            "class_aware_cooperative": {
                "intersections": {},
                "coordination_events": [cooperation],
                "pedestrian_awareness_events": [],
                "vehicle_class_priority_events": [class_event],
                "emergency_priority_events": [],
                "emergency_lifecycle_events": [],
            },
        }
    )
    suppression_records = [
        record for record in projected["records"] if record["action"] == "defer_for_pedestrian_max_wait"
    ]
    assert len(suppression_records) == 2
    assert all(record["decision"] == "defer" for record in suppression_records)
    assert all(record["context"]["pedestrian"]["protected"] is True for record in suppression_records)
    assert all(record["context"]["pedestrian"]["max_wait_lock"] is True for record in suppression_records)
    assert all(record["context"]["arbitration"]["owner"] == "pedestrian_max_wait" for record in suppression_records)
    assert all(record["context"]["arbitration"]["conflict"] is True for record in suppression_records)
    assert all(record["timing"]["previous_duration_seconds"] == 12.0 for record in suppression_records)
    assert all(record["timing"]["effective_duration_seconds"] == 12.0 for record in suppression_records)

    # Once pedestrian WALK/CLEAR begins, max-wait is no longer an overlay
    # candidate because the requested protected service has begun.
    released = arbitrate_network_policy(
        incident_hold=False,
        phase_key="pedestrian_green",
        pedestrian_waiting=2,
        pedestrian_crossing=0,
        oldest_pedestrian_wait_seconds=31.0,
        pedestrian_max_wait_seconds=30.0,
        emergency_priority_active=False,
        vehicle_class_priority_active=False,
        cooperation_active=False,
    )
    assert released.owner == "normal_timing"


def _assert_service_request_priority_state() -> None:
    controller = object.__new__(_BenchmarkSignalRulesService)
    controller._phase_index = 1  # vehicle_yellow: neither service is active
    controller._pending_request = None
    controller._service_request_sequence = 0
    controller._service_request_service = None
    controller._service_request_priority = 0
    controller._service_request_source = None
    controller._service_request_reason = None
    controller._service_request_started_at_s = None
    controller._service_request_id = None
    recorded: list[tuple[str, dict]] = []
    controller._record_event_locked = lambda event_type, details: recorded.append((event_type, dict(details)))

    assert controller._request_service_locked(
        "pedestrian",
        clock_s=10.0,
        source="pedestrian_max_wait",
        priority=700,
        reason="test higher-priority pedestrian request",
    ) is True
    assert controller._pending_request == "pedestrian"
    assert controller._service_request_priority == 700

    assert controller._request_service_locked(
        "vehicle",
        clock_s=10.5,
        source="network_cooperation",
        priority=500,
        reason="test lower-priority vehicle request",
    ) is False
    assert controller._pending_request == "pedestrian"
    assert controller._service_request_source == "pedestrian_max_wait"
    assert any(event_type == "service_request_suppressed" for event_type, _ in recorded)

    controller._clear_service_request_locked(clock_s=12.0, reason="test protected service began")
    assert controller._pending_request is None
    assert controller._service_request_service is None
    assert any(event_type == "service_request_satisfied" for event_type, _ in recorded)


def _assert_service_projection_and_backfill() -> None:
    with tempfile.TemporaryDirectory(prefix="aitl_v031_evidence_") as temporary:
        service = NetworkSimulationExperimentService(
            storage_root=Path(temporary),
            config_provider=_policy_config,
            network_provider=_network_config,
            zones_provider=_zones,
            controller_factory=_evidence_factory,
        )
        _EVIDENCE_CONTROLLERS.clear()
        result = service.run(
            duration_seconds=120,
            density="busy",
            seed=31031,
            sample_interval_seconds=2,
            profile=None,
            label="V031 decision evidence regression",
            link_id="A_to_B",
            transfer_share_percent=70,
            cooperation_lookahead_seconds=12.0,
            cooperation_max_extension_seconds=5.0,
            cooperation_min_incoming_vehicles=1,
            pedestrian_max_wait_seconds=25.0,
            pedestrian_crossing_clearance_seconds=6.0,
            pedestrian_clearance_reserve_seconds=3.0,
            vehicle_class_profile="mixed_urban",
            vehicle_class_priority_enabled=True,
            vehicle_class_priority_class="bus",
            vehicle_class_priority_weight=2.0,
            vehicle_class_priority_min_waiting=1,
            vehicle_class_priority_max_extension_seconds=4.0,
            emergency_event_enabled=True,
            emergency_event_at_seconds=15.0,
            emergency_vehicle_type="ambulance",
            emergency_priority_lookahead_seconds=12.0,
            emergency_priority_max_extension_seconds=5.0,
        )
        evidence = result["decision_evidence"]
        expected_ticks = int(120 / 0.5)
        assert _EVIDENCE_CONTROLLERS
        assert all(controller.signal_state_calls == expected_ticks for controller in _EVIDENCE_CONTROLLERS)
        assert any(controller.snapshot_state_calls > 0 for controller in _EVIDENCE_CONTROLLERS)
        assert evidence["schema_version"] == 1
        assert evidence["record_count"] > 0
        assert len({record["evidence_id"] for record in evidence["records"]}) == evidence["record_count"]
        assert evidence["categories"].get("scenario", 0) > 0
        assert evidence["categories"].get("cooperation", 0) > 0
        assert evidence["categories"].get("pedestrian", 0) > 0
        assert evidence["categories"].get("vehicle_class", 0) > 0
        assert evidence["categories"].get("emergency_lifecycle", 0) > 0
        assert evidence["categories"].get("emergency_priority", 0) > 0
        reconstructable = [
            record
            for record in evidence["records"]
            if record["trigger_category"] in {"cooperation", "pedestrian", "vehicle_class", "emergency_priority"}
        ]
        assert reconstructable
        assert any(record["timing"]["previous_duration_seconds"] is not None for record in reconstructable)
        assert any(record["timing"]["effective_duration_seconds"] is not None for record in reconstructable)
        assert service.evidence(result["run_id"]) == evidence
        csv_text = service.export_evidence_csv(result["run_id"])
        assert "source_ref" in csv_text
        assert "emergency_priority" in csv_text

        # Old V030-style stored results have no consolidated block. V031 must
        # project the stable schema on read without rewriting historical files.
        path = Path(temporary) / f"{result['run_id']}.json"
        stored = json.loads(path.read_text(encoding="utf-8"))
        stored.pop("decision_evidence", None)
        path.write_text(json.dumps(stored, indent=2) + "\n", encoding="utf-8")
        projected = service.evidence(result["run_id"])
        assert projected["schema_version"] == 1
        assert projected["record_count"] == evidence["record_count"]
        assert "decision_evidence" not in json.loads(path.read_text(encoding="utf-8"))

        # Thin route integration for the new JSON + CSV evidence surfaces.
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
            request.state.request_id = "v031-evidence-request"
            return await call_next(request)

        app.include_router(experiment_routes.router, prefix="/api/traffic")
        with TestClient(app) as client:
            evidence_response = client.get(f"/api/traffic/network-experiments/{result['run_id']}/evidence")
            assert evidence_response.status_code == 200
            envelope = evidence_response.json()
            assert envelope["ok"] is True
            assert envelope["meta"]["request_id"] == "v031-evidence-request"
            assert envelope["data"]["schema_version"] == 1
            csv_response = client.get(f"/api/traffic/network-experiments/{result['run_id']}/evidence.csv")
            assert csv_response.status_code == 200
            assert csv_response.headers["x-request-id"] == "v031-evidence-request"
            assert "decision_evidence.csv" in csv_response.headers["content-disposition"]
            assert "trigger_category" in csv_response.text


def main() -> int:
    _assert_schema_projection()
    _assert_cross_layer_pedestrian_lock()
    _assert_service_request_priority_state()
    _assert_service_projection_and_backfill()
    print("V031 persistent decision evidence regression OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
