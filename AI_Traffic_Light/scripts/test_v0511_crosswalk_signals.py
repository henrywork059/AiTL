"""Independent crosswalk simulation controller regression."""
from pathlib import Path
import sys
import tempfile
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/pc-studio/backend"))
from app.services.crosswalks import CrosswalkService
from app.services.signal_rules import SignalRulesService
from app.services.crosswalk_signals import CrosswalkSignalService

def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        config_path = root / "signal_rules.json"
        config_path.write_text(json.dumps(SignalRulesService().defaults()), encoding="utf-8")
        rules = SignalRulesService(config_path=config_path, history_path=root / "global.jsonl")
        crossings = CrosswalkService(config_path=root / "crosswalks.json")
        crossings.save({"schema_version": 1, "crosswalks": [
            {"id": "a", "label": "A", "location": "", "camera_side_a_id": None, "camera_side_b_id": None, "regions": []},
            {"id": "b", "label": "B", "location": "", "camera_side_a_id": None, "camera_side_b_id": None, "regions": []},
        ], "network": {"positions": {}, "links": [{
            "id": "link_1", "source_crosswalk_id": "a", "destination_crosswalk_id": "b",
            "source_edge": "1", "destination_edge": "2",
        }]}})
        clock = [100.0]
        service = CrosswalkSignalService(crosswalks=crossings, shared_rules=rules, clock=lambda: clock[0], history_root=root / "events")
        current = service.status(simulation_enabled=True)
        assert set(current["crosswalks"]) == {"a", "b"}
        assert current["crosswalks"]["a"]["neighbors"] == ["b"]
        assert current["coordination_enabled"] is False
        controller_a = service._controllers["a"]
        controller_b = service._controllers["b"]
        assert controller_a is not controller_b
        controller_a.set_test_inputs({"vehicles_waiting": 20})
        assert controller_b.status(0)["test_inputs"]["vehicles_waiting"] == 0
        clock[0] += 5
        later = service.status(simulation_enabled=True)
        assert later["crosswalks"]["a"]["signal"]["elapsed_seconds"] > current["crosswalks"]["a"]["signal"]["elapsed_seconds"]
        assert later["crosswalks"]["b"]["signal"]["phase"] in ("vehicle_green","vehicle_yellow","all_red","pedestrian_green","pedestrian_flashing")
        service.status(simulation_enabled=False)
        assert not service._controllers
        assert all(item["signal"] is None for item in service.status(simulation_enabled=False)["crosswalks"].values())
    print("[PASS] crosswalk signal instances independent, topology read-only, stop clears controllers")

if __name__ == "__main__":
    main()
