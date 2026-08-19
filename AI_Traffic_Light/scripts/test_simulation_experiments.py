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
from app.services.simulation_experiments import SimulationExperimentService  # noqa: E402




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
