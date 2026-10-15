"""V0510 signal scenario: near-end pedestrian protection and emergency request preview."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/pc-studio/backend"))
from app.services.signal_rules import SignalRulesService  # noqa: E402


def main() -> None:
    with TemporaryDirectory(prefix="aitl-v0510-signal-") as temp:
        folder = Path(temp)
        service = SignalRulesService(config_path=folder / "signals.json", history_path=folder / "history.jsonl")
        config = deepcopy(service.get_config())
        config["mode"] = "test"
        config["profiles"]["Normal"]["scenarios"] = [{
            "id": "slow_crossing_check", "label": "Slow pedestrian crossing",
            "enabled": True, "rank": 1, "match": "all", "persistence_seconds": 0,
            "cooldown_seconds": 0,
            "conditions": [
                {"source": "metric", "metric": "pedestrians_crossing", "operator": "gte", "threshold": 1},
                {"source": "metric", "metric": "phase_remaining_seconds", "operator": "lte", "threshold": 3},
            ],
            "action": {
                "type": "hold_current_phase", "adjustment_seconds": 5,
                "target_phases": ["pedestrian_flashing"], "request_service": None,
            },
        }]
        service.save_config(config)
        service.set_test_inputs({"pedestrians_crossing": 1})
        service.reset_runtime(0.0)
        start = service.signal_state(26.0)
        assert start["phase"] == "pedestrian_flashing", start
        assert start["winning_scenario_id"] is None, start
        later = service.signal_state(30.0)
        assert later["phase"] == "pedestrian_flashing" and later["seconds_remaining"] >= 4.9, later
        assert later["winning_scenario_id"] == "slow_crossing_check", later
        assert later["vehicle_go"] is False, later

        config = deepcopy(service.get_config())
        config["profiles"]["Normal"]["scenarios"] = [{
            "id": "emergency_priority_check", "label": "Emergency request",
            "enabled": True, "rank": 1, "match": "all", "persistence_seconds": 0,
            "cooldown_seconds": 0,
            "conditions": [
                {"source": "zone_class_count", "zone_id": "region_1", "class_name": "ambulance", "operator": "gte", "threshold": 1},
            ],
            "action": {
                "type": "request_next_phase", "adjustment_seconds": 0,
                "target_phases": ["pedestrian_green"], "request_service": "vehicle",
            },
        }]
        service.save_config(config)
        before = service.signal_state(30.1)
        no_ambulance = service.preview({"phase_key": "pedestrian_green", "zone_class_counts": {"region_1": {"car": 4}}})
        ambulance = service.preview({"phase_key": "pedestrian_green", "zone_class_counts": {"region_1": {"ambulance": 1}}})
        assert no_ambulance["winning_scenario_id"] is None
        assert ambulance["winning_scenario_id"] == "emergency_priority_check"
        # Preview is read-only: no abrupt signal phase transition or conflicting green.
        after = service.status(30.1)
        assert before["phase"] == after["phase"] and before["vehicle_go"] == after["vehicle_go"]

    print("[PASS] near-end crossing rule preserves pedestrian clearance")
    print("[PASS] ambulance rule is class-specific and preview does not command signals")


if __name__ == "__main__":
    main()
