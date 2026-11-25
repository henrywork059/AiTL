"""Source-qualified flow, occupancy, waiting candidates, replay and historical attribution."""
import csv
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/pc-studio/backend"))
from app.services.object_tracking import ObjectTrackingService
from app.services.observation_identity import ObservationIdentity
from app.services.traffic_flow import TrafficFlowService
from app.services.traffic_history import TrafficHistoryService
from app.services.traffic_logic import evaluate_traffic_state
from app.services.traffic_observations import observation_for_junction
from test_object_tracking_flow import ZONES, det, frame


def main():
    zones = [*ZONES, {"id": "queue", "type": "vehicle_queue", "label": "Queue",
                      "polygon": [[300, 180], [490, 180], [490, 620], [300, 620]]}]
    now = [1000]
    valid = [True]
    assignment = {"a": "j1", "b": "j2", "c": "j2"}
    def resolve(source):
        return {"intersection_id": assignment.get(source, "fallback"),
                "source_mapping_matched": source in assignment}

    with TemporaryDirectory() as directory:
        path = Path(directory) / "flow.jsonl"
        historical = {"event_id": "legacy", "timestamp_ms": 10, "event_type": "line_crossing",
                      "class_name": "car", "track_id": "legacy_track", "line_id": "vehicle_line"}
        path.write_text(json.dumps(historical) + "\n", encoding="utf-8")
        flow = TrafficFlowService(flow_path=path)
        tracker = ObjectTrackingService(flow_service=flow, intersection_resolver=resolve,
                                        clock_ms=lambda: now[0],
                                        observation_validator=lambda observation: valid[0])

        def submit(source, number, timestamp, x, *, provenance="simulation"):
            now[0] = timestamp
            data = frame(number, timestamp, [] if x is None else [det("same-id", "car", x, 400)])
            data["source_id"] = source
            identity = ObservationIdentity(source, number, timestamp, 1280, 720, provenance, 1, 0, 0)
            result = tracker.update(data, zones, observation=identity)
            state = evaluate_traffic_state(result, zones)
            return result, state, identity

        a1, s1, _ = submit("a", 1, 1000, 350)
        assert s1["traffic_observation"]["queue"]["queue"]["stationary_candidates"] == 0
        a2, s2, _ = submit("a", 2, 2000, 352)
        assert s2["traffic_observation"]["queue"]["queue"]["stationary_candidates"] == 1
        _, s3, _ = submit("a", 3, 3000, 450)
        assert s3["traffic_observation"]["queue"]["queue"]["stationary_candidates"] == 0
        submit("a", 4, 4000, 550)
        submit("a", 5, 5000, 650)
        b1, _, _ = submit("b", 1, 6000, 350, provenance="esp32_stream")
        assert b1["detections"][0]["track_id"] != a2["detections"][0]["track_id"]
        submit("b", 2, 7000, 450, provenance="esp32_stream")
        submit("b", 3, 8000, 550, provenance="esp32_stream")
        submit("b", 4, 9000, 650, provenance="esp32_stream")
        before = flow.status()["stored_events"]
        replay, replay_state, _ = submit("a", 5, 5000, 650)
        assert not replay_state["traffic_observation"]["available"]
        assert "track_id" not in replay["detections"][0]
        assert flow.status()["stored_events"] == before

        # Overlapping views remain separate source rows even within one junction.
        submit("c", 1, 10000, 450)
        submit("c", 2, 11000, 550)
        groups = {(g["source_id"], g["intersection_id"], g["provenance"]): g
                  for g in flow.query(zones=zones, minutes=0)["by_source"]}
        assert groups[("a", "j1", "simulation")]["summary"]["unique_vehicle_passages"] == 1
        assert groups[("b", "j2", "esp32_stream")]["summary"]["unique_vehicle_passages"] == 1
        assert groups[("c", "j2", "simulation")]["summary"]["unique_vehicle_passages"] == 1
        assert groups[(None, None, "unknown")]["event_count"] == 1
        data = flow.query(zones=zones, minutes=0)
        exits = [e for e in data["events"] if e.get("source_id") == "a"
                 and e["event_type"] == "region_exit" and e.get("region_id") == "vehicle_region"]
        assert len(exits) == 1 and exits[0]["dwell_ms"] == 2000
        assert exits[0]["intersection_id"] == "j1"

        assignment["a"] = "j3"
        _, empty, _ = submit("a", 6, 12000, None)
        q = empty["traffic_observation"]
        assert q["available"] and q["intersection_id"] == "j3"
        assert q["occupancy"]["queue"]["total"] == 0
        assert q["queue"]["queue"]["sampled_presence"] == 0
        assert observation_for_junction(q, "j3", "a", now_ms=17000)["available"]
        for junction, source, stamp in [("j1", "a", 12000), ("j3", "b", 12000), ("j3", "a", 17001)]:
            unavailable = observation_for_junction(q, junction, source, now_ms=stamp)
            assert not unavailable["available"] and unavailable["occupancy"] is None
        assert evaluate_traffic_state(None, zones)["traffic_observation"]["occupancy"] is None
        valid[0] = False
        _, retired, _ = submit("a", 7, 13000, 450)
        assert not retired["traffic_observation"]["available"]
        persisted = TrafficFlowService(flow_path=path).query(zones=zones, minutes=0)
        assert persisted["events"][0]["intersection_id"] is None
        assert persisted["events"][0]["provenance"] == "unknown"
        assert persisted["events"][1]["intersection_id"] == "j1"
        assert "source_id" not in json.loads(path.read_text(encoding="utf-8").splitlines()[0])
        history = TrafficHistoryService(history_path=Path(directory) / "history.jsonl")
        legacy_state = dict(s2)
        legacy_state.pop("traffic_observation")
        assert history.record_state(legacy_state, force=True)
        assert history.record_state(s2, force=True)
        assert history.record_state(empty, force=True)
        assert not history.record_state(retired, force=True)
        points = history.query(zones=zones, minutes=0)["points"]
        assert [(p["source_id"], p["intersection_id"], p["provenance"]) for p in points] == [
            (None, None, "unknown"), ("a", "j1", "simulation"), ("a", "j3", "simulation")
        ]
        assert history.record_state(empty) is False
        header = next(csv.reader(flow.export_csv(zones=zones, minutes=0).splitlines()))
        assert header == ["event_id", "timestamp_ms", "source_frame_number", "track_id",
                          "class_id", "class_name", "event_type", "line_id", "line_label",
                          "region_id", "region_label", "region_type", "direction", "dwell_ms", "x", "y"]

    print("[PASS] source/junction flow, historical attribution, dwell, replay, stationarity, fresh zero and retired/unavailable data")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
