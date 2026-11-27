from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "pc-studio" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.signal_rules import signal_rules_service  # noqa: E402
from app.services.simulation_experiments import SimulationExperimentService, _ModeSimulation  # noqa: E402




def scenario_config() -> dict:
    config = deepcopy(signal_rules_service.get_config())
    config["mode"] = "adaptive"
    profile = config["profiles"]["Normal"]
    profile["scenarios"] = [
        {
            "id": "whole_scene_car_demand",
            "label": "Whole scene car demand",
            "enabled": True,
            "rank": 1,
            "match": "all",
            "conditions": [
                {"source": "zone_class_count", "zone_id": "whole_scene", "class_name": "car", "operator": "gte", "threshold": 1}
            ],
            "persistence_seconds": 0.0,
            "cooldown_seconds": 0.0,
            "action": {
                "type": "extend_current_phase",
                "adjustment_seconds": 2.0,
                "target_phases": ["vehicle_green"],
                "request_service": "vehicle",
            },
        }
    ]
    return config


def experiment_zones() -> list[dict]:
    return [
        {
            "id": "whole_scene",
            "label": "Whole scene",
            "type": "counting_region",
            "polygon": [[0, 0], [1279, 0], [1279, 719], [0, 719]],
        }
    ]

def comparable(result: dict) -> dict:
    return {
        "scenario": result["scenario"],
        "fixed": result["fixed"],
        "adaptive": result["adaptive"],
        "comparison": result["comparison"],
    }


def main() -> int:
    with TemporaryDirectory(prefix="aitl_experiment_test_") as temporary:
        service = SimulationExperimentService(
            storage_root=Path(temporary) / "experiments",
            config_provider=signal_rules_service.get_config,
        )
        # The optional normalized metric path must not change the original
        # production benchmark result or its existing metric schema.
        args=dict(mode="fixed",density="normal",seed=42,duration_seconds=30,
                  sample_interval_seconds=1,policy_config=signal_rules_service.get_config(),
                  zones=[],temp_root=Path(temporary))
        ordinary=_ModeSimulation(**args).run()
        measured=_ModeSimulation(**args,normalized_gate_evidence=True).run()
        common=measured.pop("normalized_gate_evidence")
        assert ordinary==measured
        assert common["engine"]=="production_legacy_experiment"
        assert len(common["timeline"])==150
        assert not common["geometry_demand_matched_to_native"]
        assert not common["normalized_report_metrics"]["production_experiment_parity"]
        assert common["normalized_report_metrics"]["duration_seconds"]==30.
        for kind,waits in common["waiting_episodes"].items():
            assert waits["observed_agent_seconds"]==common["summary"][kind+"_wait_agent_s"]
        first = service.run(
            duration_seconds=90,
            density="busy",
            seed=25025,
            sample_interval_seconds=1,
            profile="Normal",
            label="regression",
        )
        second = service.run(
            duration_seconds=90,
            density="busy",
            seed=25025,
            sample_interval_seconds=1,
            profile="Normal",
            label="regression-repeat",
        )

        assert comparable(first) == comparable(second), "Same seed/config must produce repeatable benchmark telemetry."
        assert first["fixed"]["mode"] == "fixed"
        assert first["adaptive"]["mode"] == "adaptive"
        assert len(first["fixed"]["timeline"]) >= 80
        assert len(first["adaptive"]["timeline"]) >= 80
        assert first["adaptive"]["metrics"]["signal"]["rule_application_count"] > 0, "Busy adaptive run should exercise at least one rule."
        assert first["fixed"]["metrics"]["signal"]["rule_application_count"] == 0

        for mode in ("fixed", "adaptive"):
            metrics = first[mode]["metrics"]
            assert metrics["waiting"]["vehicle"]["p95_seconds"] >= metrics["waiting"]["vehicle"]["median_seconds"]
            assert metrics["waiting"]["pedestrian"]["p95_seconds"] >= metrics["waiting"]["pedestrian"]["median_seconds"]
            assert metrics["queues"]["vehicle"]["max"] >= metrics["queues"]["vehicle"]["average"]
            assert 0 <= metrics["queues"]["vehicle"]["occupied_share_percent"] <= 100
            assert 0 <= metrics["signal"]["clearance_share_percent"] <= 100
            assert metrics["throughput"]["combined_services"] == metrics["throughput"]["vehicle_passages"] + metrics["throughput"]["pedestrian_crossings"]

        zone_service = SimulationExperimentService(
            storage_root=Path(temporary) / "zone_experiments",
            config_provider=scenario_config,
            zones_provider=experiment_zones,
        )
        zone_run = zone_service.run(
            duration_seconds=45,
            density="normal",
            seed=25026,
            sample_interval_seconds=1,
            profile="Normal",
            label="zone-scenario",
        )
        assert zone_run["scenario"]["zones"][0]["id"] == "whole_scene"
        assert zone_run["adaptive"]["metrics"]["signal"]["rule_applications"].get("whole_scene_car_demand", 0) > 0
        assert zone_run["fixed"]["metrics"]["signal"]["rule_application_count"] == 0

        live_service=SimulationExperimentService(storage_root=Path(temporary)/"live_slots",
            config_provider=signal_rules_service.get_config,zones_provider=lambda:[])
        live_args=dict(duration_seconds=30,density="normal",seed=42,sample_interval_seconds=1,
                       profile="Normal",demand_model="live_slots")
        live_first=live_service.run(**live_args)
        live_second=live_service.run(**live_args)
        assert comparable(live_first)==comparable(live_second)
        assert live_first["scenario"]["movement_step_seconds"]==.05
        assert live_first["scenario"]["demand_model"]=="live_slots"
        assert not live_first["scenario"]["native_demand_matched"]
        assert live_service.get(live_first["run_id"])["scenario"]==live_first["scenario"]
        assert "fixed_vehicle_queue" in live_service.export_csv(live_first["run_id"])
        assert "demand_model" not in first["scenario"]

        protected_args={**live_args,"demand_model":"protected_slots","duration_seconds":90}
        protected_first=live_service.run(**protected_args)
        protected_second=live_service.run(**protected_args)
        assert comparable(protected_first)==comparable(protected_second)
        digest=protected_first["scenario"]["demand_digest"]
        assert len(digest)==64
        for mode in ("fixed","adaptive"):
            arm=protected_first[mode]
            assert arm["protected_demand"]["digest"]==digest
            import hashlib, json
            assert hashlib.sha256(json.dumps(arm["protected_demand"]["manifest"],sort_keys=True,separators=(",",":")).encode()).hexdigest()==digest
            metrics=arm["metrics"]
            assert abs(sum(metrics["signal"]["applied_phase_time_seconds"].values())-90)<1e-6
            trace=arm["admission_trace"]
            assert trace["step_seconds"]==.05
            cursor=1
            holds=0
            totals={}
            for span in trace["spans"]:
                assert span["first_tick"]==cursor and span["last_tick"]>=cursor
                n=span["last_tick"]-cursor+1
                cursor+=n
                totals[span["applied"]]=totals.get(span["applied"],0)+n
                assert span["applied"] in {span["requested"],"all_red"}
                if span["requested"] in {"vehicle_green","pedestrian_green"} and span["requested"]!=span["applied"]: holds+=n
            assert cursor==1801
            assert {k:round(n*.05,3) for k,n in totals.items()}==metrics["signal"]["applied_phase_time_seconds"]
            assert round(holds*.05,3)==metrics["signal"]["admission_hold_seconds"]
            assert not metrics["diagnostics"]["protected_overlap_detected"]
            common=arm["normalized_gate_evidence"]
            assert len(common["timeline"])==450
            assert all(row["applied_phase"] in {row["phase"],"all_red"} for row in common["timeline"])
            report=common["normalized_report_metrics"]
            assert report["duration_seconds"]==90. and not report["production_experiment_parity"]
            for kind,waits in common["waiting_episodes"].items():
                assert waits["observed_agent_seconds"]==common["summary"][kind+"_wait_agent_s"]
                assert report["waiting"][kind]["observed_agent_seconds"]==waits["observed_agent_seconds"]
        assert "fixed_applied_phase,adaptive_applied_phase" in live_service.export_csv(protected_first["run_id"])
        assert "fixed_applied_phase" not in live_service.export_csv(live_first["run_id"])
        assert live_service.get(protected_first["run_id"])==protected_first

        listing = service.list()
        assert listing["total"] == 2
        loaded = service.get(first["run_id"])
        assert loaded["run_id"] == first["run_id"]
        csv_text = service.export_csv(first["run_id"])
        assert "fixed_vehicle_queue" in csv_text and "adaptive_vehicle_queue" in csv_text
        deleted = service.delete(first["run_id"])
        assert deleted["deleted"] is True
        assert service.list()["total"] == 1

    print("Simulation experiment regression OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
