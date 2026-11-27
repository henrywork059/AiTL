"""Deterministic virtual-signal freshness and protected sequence checks."""
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/pc-studio/backend"))

from app.services import signal_rules as module
from app.services.crosswalk_observations import crosswalk_observation
from test_v0512_camera_crosswalk import crossing, detected


def main():
    clock = [100.0, 1000.0]
    fake_time = SimpleNamespace(monotonic=lambda: clock[0], time=lambda: clock[1])

    def advance(seconds):
        clock[0] += seconds
        clock[1] += seconds

    def observation(timestamp=None, source="live_zone_evaluation", classes=None):
        return {
            "data_source": source,
            "source_timestamp_ms": int(clock[1] * 1000) if timestamp is None else timestamp,
            "zone_class_counts": {"queue": {"car": 3} if classes is None else classes},
        }

    with tempfile.TemporaryDirectory() as directory, patch.object(module, "time", fake_time):
        root = Path(directory)
        service = module.SignalRulesService(config_path=root / "rules.json", history_path=root / "events.jsonl")
        config = deepcopy(service.get_config())
        config["mode"] = "adaptive"
        config["dry_run"] = False
        profile = config["profiles"][config["active_profile"]]
        profile["stale_data_seconds"] = 4.0
        profile["scenarios"] = [{
            "id": "car_demand", "label": "Car demand", "enabled": True, "rank": 1, "match": "all",
            "conditions": [{"source": "zone_class_count", "zone_id": "queue", "class_name": "car",
                            "operator": "gte", "threshold": 2}],
            "persistence_seconds": 2.0, "cooldown_seconds": 0.0,
            "action": {"type": "extend_current_phase", "adjustment_seconds": 5,
                       "target_phases": ["vehicle_green"], "request_service": "vehicle"},
        }]
        service.save_config(config)
        service.signal_state(0.0)
        service.observe(observation(990000))
        assert not service.signal_state(0.0)["data_fresh"]
        sample = observation()
        service.observe(sample)
        assert service.signal_state(0.0)["winning_scenario_id"] is None
        advance(4.1)
        service.observe(sample)
        assert not service.signal_state(4.1)["data_fresh"]
        service.observe(observation())
        assert service.signal_state(4.1)["winning_scenario_id"] is None
        advance(2.1)
        service.observe(observation())
        assert service.signal_state(6.2)["winning_scenario_id"] == "car_demand"
        duration = service.signal_state(6.2)["effective_duration_seconds"]
        advance(0.1)
        service.observe({"data_source": "inference_unavailable:INFERENCE_FAILED"})
        state = service.signal_state(6.3)
        assert not state["data_fresh"] and state["winning_scenario_id"] is None
        assert state["effective_duration_seconds"] == duration
        print("[PASS] source-age expiry, persistence restart and committed phase timing")

        # After the current phase finishes, exercise each protected transition
        # without observations. No conflicting WALK/vehicle permission is allowed.
        t = duration
        for key, phase in module.PHASE_SEQUENCE[1:] + module.PHASE_SEQUENCE[:1]:
            state = service.signal_state(t + 0.001)
            assert state["phase_key"] == key, (key, state["phase_key"])
            assert state["phase"] == phase
            assert not (state["vehicle_go"] and (state["pedestrian_walk"] or state["pedestrian_clear"]))
            assert state["effective_duration_seconds"] >= module.PROTECTED_MINIMUMS[key]
            assert not state["data_fresh"]
            t += state["effective_duration_seconds"]
        print("[PASS] protected amber, all-red, WALK and CLEAR sequence after loss")

        # Unknown class is not evidence of zero demand; known class in a
        # different region can establish a zero count for the target region.
        condition = {"source": "zone_class_count", "zone_id": "queue", "class_name": "ambulance"}
        assert not service._condition_value_locked(config, condition, observation())[0]
        known = observation(classes={})
        known["zone_class_counts"]["other"] = {"ambulance": 1}
        assert service._condition_value_locked(config, condition, known)[:2] == (True, 0.0)
        print("[PASS] unsupported class unavailable rather than zero")

        # A fresh observation after an unpolled timeout cannot inherit persistence.
        service.reset_runtime(0.0)
        service.observe(observation())
        service.signal_state(0.0)
        advance(4.1)
        service.observe(observation())
        assert service.signal_state(4.1)["winning_scenario_id"] is None
        print("[PASS] gap without polling resets persistence")

    now_ms = 20000
    cross = crossing("cross_1", "cam_a", "cam_b")
    views = {
        "cam_a": detected(["car"], "cam_a", now_ms - 1900),
        "cam_b": detected(["car"], "cam_b", now_ms),
    }
    fused, _, meta = crosswalk_observation(cross, views, model_id="demo", now_ms=now_ms)
    assert fused["source_timestamp_ms"] == now_ms - 1900
    assert meta["source_timestamp_ms"] == now_ms
    print("[PASS] fused policy observation uses oldest contributing receive time")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
