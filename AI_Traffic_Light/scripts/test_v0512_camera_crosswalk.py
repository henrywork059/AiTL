"""Focused camera-to-crosswalk inference adapter and independent-controller tests."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/pc-studio/backend"))
from app.services.crosswalk_observations import crosswalk_observation  # noqa: E402
from app.services.crosswalk_signals import CrosswalkSignalService  # noqa: E402
from app.services.crosswalks import CrosswalkService  # noqa: E402
from app.services.signal_rules import SignalRulesService  # noqa: E402


POLYGON = [[0, 0], [1280, 0], [1280, 720], [0, 720]]


def crossing(crosswalk_id, a, b=None, *, sides=("a", "b")):
    return {
        "id": crosswalk_id, "label": crosswalk_id, "location": "",
        "camera_side_a_id": a, "camera_side_b_id": b,
        "regions": [{
            "id": "region_1", "label": "Region 1",
            "vertices": POLYGON,
            "vertices_by_side": {side: POLYGON for side in sides},
        }],
    }


def detected(classes, source, timestamp, number=1, model="demo"):
    return {
        "source_id": source, "model_id": model, "error": None,
        "frame": {
            "source_id": source, "timestamp_ms": timestamp,
            "source_frame_number": number, "image_width": 1280, "image_height": 720,
            "detections": [
                {"class_name": label, "box_xyxy": [40 + index * 50, 20, 80 + index * 50, 90]}
                for index, label in enumerate(classes)
            ],
        },
    }


def main() -> None:
    now = int(time.time() * 1000)
    cross_a = crossing("cross_1", "sim_a", "sim_b")
    cross_b = crossing("cross_2", "sim_c", sides=("a",))
    views = {
        "sim_a": detected(["car", "car"], "sim_a", now),
        "sim_b": detected(["car", "car", "car", "car"], "sim_b", now),
        "sim_c": detected(["person"], "sim_c", now),
    }
    combined, signature, meta = crosswalk_observation(cross_a, views, model_id="demo", now_ms=now)
    assert combined is not None and len(signature) == 2
    assert combined["zone_class_counts"]["region_1"]["car"] == 3
    assert combined["zone_class_counts"]["cross_1:region_1"]["car"] == 3
    assert meta["camera_coverage"] == "complete"
    separate, _, _ = crosswalk_observation(cross_b, views, model_id="demo", now_ms=now)
    assert separate["zone_class_counts"]["region_1"]["person"] == 1
    assert "car" not in separate["zone_class_counts"]["region_1"]

    one, _, meta = crosswalk_observation(cross_a, {"sim_a": views["sim_a"]}, model_id="demo", now_ms=now)
    assert one["zone_class_counts"]["region_1"]["car"] == 2
    assert meta["camera_coverage"] == "partial"
    zero, _, meta = crosswalk_observation(cross_a, {"sim_a": detected([], "sim_a", now)}, model_id="demo", now_ms=now)
    assert zero["zone_class_counts"]["region_1"] == {}
    assert meta["observation_provenance"] == "camera_ai"

    old = detected(["car"], "sim_a", now - 5100)
    unavailable, _, meta = crosswalk_observation(cross_a, {"sim_a": old}, model_id="demo", now_ms=now)
    assert unavailable is None and meta["observation_provenance"] == "unavailable"
    switched, _, _ = crosswalk_observation(cross_a, views, model_id="replacement", now_ms=now)
    assert switched is None
    skew = dict(views)
    skew["sim_a"] = detected(["car"], "sim_a", now - 3000)
    only_newer, _, _ = crosswalk_observation(cross_a, skew, model_id="demo", now_ms=now)
    assert only_newer["zone_class_counts"]["region_1"]["car"] == 4

    one_side = crossing("cross_3", "sim_a", "sim_b", sides=("a",))
    only_a, _, _ = crosswalk_observation(one_side, views, model_id="demo", now_ms=now)
    assert only_a["zone_class_counts"]["region_1"]["car"] == 2

    with TemporaryDirectory(prefix="aitl-crosswalk-ai-") as directory:
        root = Path(directory)
        crosswalks = CrosswalkService(config_path=root / "crosswalks.json")
        crosswalks.save({"schema_version": 1, "crosswalks": [cross_a, cross_b]})
        rules = SignalRulesService(config_path=root / "signal_rules.json", history_path=root / "shared.jsonl")
        config = deepcopy(rules.get_config())
        config["mode"] = "adaptive"
        config["profiles"]["Normal"]["scenarios"] = [{
            "id": "vehicle_class", "label": "Vehicle class",
            "enabled": True, "rank": 1, "match": "all",
            "conditions": [{"source": "zone_class_count", "zone_id": "cross_1:region_1",
                            "class_name": "car", "operator": "gte", "threshold": 2.5}],
            "persistence_seconds": 0, "cooldown_seconds": 0,
            "action": {"type": "extend_current_phase", "adjustment_seconds": 5,
                       "target_phases": ["vehicle_green"], "request_service": None},
        }]
        rules.save_config(config)
        clock = [100.0]
        service = CrosswalkSignalService(
            crosswalks=crosswalks, shared_rules=rules, clock=lambda: clock[0],
            history_root=root / "history",
        )
        service.ingest_camera_results(views, simulation_enabled=True, model_id="demo")
        network = service.status(simulation_enabled=True)
        assert network["crosswalks"]["cross_1"]["observation_provenance"] == "camera_ai"
        assert network["crosswalks"]["cross_1"]["signal"]["winning_scenario_id"] == "vehicle_class"
        assert network["crosswalks"]["cross_2"]["signal"]["winning_scenario_id"] is None
        assert network["crosswalks"]["cross_2"]["region_class_counts"]["region_1"]["person"] == 1
        # No frame from one crossing should be used as another crossing's observations.
        service.ingest_camera_results({}, simulation_enabled=True, model_id="demo")
        cleared = service.status(simulation_enabled=True)
        assert cleared["crosswalks"]["cross_1"]["observation_provenance"] == "unavailable"
        assert cleared["crosswalks"]["cross_1"]["signal"]["data_fresh"] is False
        assert cleared["crosswalks"]["cross_2"]["signal"]["data_fresh"] is False
        # A real camera can drive a software-only virtual signal, never physical lamps.
        service.ingest_camera_results(views, simulation_enabled=False, virtual_preview=True, model_id="demo")
        preview = service.status(simulation_enabled=False)
        assert preview["virtual_preview_enabled"] is True
        assert preview["crosswalks"]["cross_1"]["status"] == "virtual"
        service.ingest_camera_results({}, simulation_enabled=False, virtual_preview=False, model_id="demo")
        stopped = service.status(simulation_enabled=False)
        assert all(item["signal"] is None for item in stopped["crosswalks"].values())

    print("[PASS] Side A/B matching, two-view averaging, single-view and zero observations")
    print("[PASS] old/missing/model-switched inputs withdrawn, class rules isolated by crosswalk")
    print("[PASS] simulated and ESP-camera virtual preview; no physical signal control")


if __name__ == "__main__":
    main()
