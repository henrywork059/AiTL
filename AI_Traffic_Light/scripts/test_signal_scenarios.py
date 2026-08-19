from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pc-studio" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.signal_rules import SignalRulesService  # noqa: E402


def zone_scenario(*, scenario_id: str, rank: int, zone_id: str, class_name: str, threshold: int, adjustment: float) -> dict:
    return {
        "id": scenario_id,
        "label": scenario_id.replace("_", " ").title(),
        "enabled": True,
        "rank": rank,
        "match": "all",
        "conditions": [
            {
                "source": "zone_class_count",
                "zone_id": zone_id,
                "class_name": class_name,
                "operator": "gt",
                "threshold": threshold,
            }
        ],
        "persistence_seconds": 0.0,
        "cooldown_seconds": 0.0,
        "action": {
            "type": "extend_current_phase",
            "adjustment_seconds": adjustment,
            "target_phases": ["vehicle_green"],
            "request_service": "vehicle",
        },
    }


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        service = SignalRulesService(config_path=root / "signal_rules.json", history_path=root / "history.jsonl")
        config = deepcopy(service.get_config())
        profile = config["profiles"][config["active_profile"]]

        assert profile["scenarios"], "legacy/default rules should migrate into editable scenarios"
        assert profile["scenarios"][0]["rank"] < profile["scenarios"][-1]["rank"]

        config["mode"] = "adaptive"
        profile["scenarios"] = [
            zone_scenario(scenario_id="rank_2_cars", rank=2, zone_id="queue_a", class_name="car", threshold=2, adjustment=2.0),
            zone_scenario(scenario_id="rank_1_cars", rank=1, zone_id="queue_a", class_name="car", threshold=2, adjustment=5.0),
        ]
        service.save_config(config)
        service.signal_state(10.0)  # apply save-time re-anchor
        service.observe(
            {
                "pedestrians_waiting": 0,
                "pedestrians_crossing": 0,
                "vehicles_waiting": 0,
                "zone_class_counts": {"queue_a": {"car": 4, "bus": 1}},
            }
        )
        state = service.signal_state(10.1)
        assert state["winning_scenario_id"] == "rank_1_cars"
        assert state["active_rules"] == ["rank_1_cars"]
        assert state["effective_duration_seconds"] == 17.0
        statuses = {item["scenario_id"]: item for item in state["scenario_status"]}
        assert statuses["rank_1_cars"]["state"] == "winner"
        assert statuses["rank_2_cars"]["state"] == "suppressed"
        assert statuses["rank_1_cars"]["conditions"][0]["observed"] == 4.0

        # A higher-ranked scenario whose zone disappeared must not block the next
        # eligible scenario.
        config = deepcopy(service.get_config())
        profile = config["profiles"][config["active_profile"]]
        profile["scenarios"] = [
            zone_scenario(scenario_id="missing_zone", rank=1, zone_id="deleted_zone", class_name="car", threshold=0, adjustment=8.0),
            zone_scenario(scenario_id="available_zone", rank=2, zone_id="queue_a", class_name="car", threshold=0, adjustment=3.0),
        ]
        service.save_config(config)
        service.signal_state(20.0)
        service.observe({"zone_class_counts": {"queue_a": {"car": 2}}})
        state = service.signal_state(20.1)
        assert state["winning_scenario_id"] == "available_zone"
        statuses = {item["scenario_id"]: item for item in state["scenario_status"]}
        assert statuses["missing_zone"]["state"] == "unavailable"

        # ALL/ANY condition semantics are explicit and deterministic.
        config = deepcopy(service.get_config())
        profile = config["profiles"][config["active_profile"]]
        profile["scenarios"] = [
            {
                "id": "ped_and_vehicle",
                "label": "Pedestrian and vehicle demand",
                "enabled": True,
                "rank": 1,
                "match": "all",
                "conditions": [
                    {"source": "zone_class_count", "zone_id": "wait_a", "class_name": "person", "operator": "gte", "threshold": 3},
                    {"source": "zone_class_count", "zone_id": "queue_a", "class_name": "car", "operator": "gte", "threshold": 2},
                ],
                "persistence_seconds": 0,
                "cooldown_seconds": 0,
                "action": {
                    "type": "reduce_current_phase",
                    "adjustment_seconds": 3,
                    "target_phases": ["vehicle_green"],
                    "request_service": "pedestrian",
                },
            }
        ]
        service.save_config(config)
        service.signal_state(30.0)
        service.observe({"zone_class_counts": {"wait_a": {"person": 3}, "queue_a": {"car": 2}}})
        state = service.signal_state(30.1)
        assert state["winning_scenario_id"] == "ped_and_vehicle"
        assert state["effective_duration_seconds"] == 9.0
        assert state["pending_request"] == "pedestrian"

        preview = service.preview(
            {
                "phase_key": "vehicle_green",
                "zone_class_counts": {"wait_a": {"person": 3}, "queue_a": {"car": 2}},
            }
        )
        assert preview["winning_scenario_id"] == "ped_and_vehicle"
        assert preview["prototype_only"] is True

        duplicate_rank = deepcopy(service.get_config())
        duplicate_profile = duplicate_rank["profiles"][duplicate_rank["active_profile"]]
        duplicate_profile["scenarios"] = [
            zone_scenario(scenario_id="rank_a", rank=1, zone_id="queue_a", class_name="car", threshold=0, adjustment=1.0),
            zone_scenario(scenario_id="rank_b", rank=1, zone_id="queue_a", class_name="bus", threshold=0, adjustment=1.0),
        ]
        try:
            service.save_config(duplicate_rank)
        except Exception as exc:
            assert "duplicate scenario rank" in str(exc).lower()
        else:
            raise AssertionError("duplicate scenario ranks must be rejected")

    print("signal scenario tests passed")


if __name__ == "__main__":
    main()
