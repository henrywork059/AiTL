"""Selected-source tracking scope, replay protection and expiry regressions."""
from dataclasses import replace
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/pc-studio/backend"))
from app.services.object_tracking import ObjectTrackingService
from app.services.observation_identity import ObservationIdentity
from app.services.tracking_scope import TrackingContinuity, TrackingScope, MAX_TRACKING_SOURCES
from app.services.traffic_flow import TrafficFlowService
from test_object_tracking_flow import ZONES, det, frame


def main():
    now = [1000]
    assignments = {"a": "j1", "b": "j2"}
    resolve = lambda source: {"intersection_id": assignments.get(source, "fallback"),
                              "source_mapping_matched": source in assignments}
    with TemporaryDirectory() as directory:
        flow = TrafficFlowService(flow_path=Path(directory) / "flow.jsonl")
        tracker = ObjectTrackingService(flow_service=flow, intersection_resolver=resolve, clock_ms=lambda: now[0])

        def submit(source, number, stamp, x, *, epoch=0, generation=1, width=1280, provenance="esp32_stream"):
            data = frame(number, stamp, [det("same-id", "car", x, 400)])
            data.update(source_id=source, image_width=width)
            obs = ObservationIdentity(source, number, stamp, width, 720, provenance, generation, epoch, 0)
            return tracker.update(data, ZONES, observation=obs), obs

        a, obs_a = submit("a", 1, 1000, 350)
        now[0] = 1100
        a2, obs_a2 = submit("a", 2, 1100, 450)
        assert a["detections"][0]["track_id"] == a2["detections"][0]["track_id"]
        repeat, _ = submit("a", 2, 1100, 450)
        assert repeat["detections"][0]["track_age_frames"] == 2
        before = flow.status()["stored_events"]
        b, obs_b = submit("b", 2, 1100, 650)
        assert b["detections"][0]["track_id"] != a2["detections"][0]["track_id"]
        assert tracker.status_for_observation(obs_a2)["active_track_count"] == 0
        replay, _ = submit("a", 2, 1100, 450)
        assert "track_id" not in replay["detections"][0]
        assert replay["tracking"]["active_track_count"] == 0
        assert flow.status()["stored_events"] == before
        now[0] = 1200
        a3, obs_a3 = submit("a", 3, 1200, 450)
        assert a3["detections"][0]["track_id"] != a2["detections"][0]["track_id"]
        print("[PASS] source isolation, cached A/B/A replay and no duplicate flow event")

        assignments["a"] = "j3"
        assert tracker.status_for_observation(obs_a3)["active_track_count"] == 0
        now[0] = 1300
        moved, obs_moved = submit("a", 4, 1300, 450)
        assert moved["detections"][0]["track_id"] != a3["detections"][0]["track_id"]
        now[0] = 1400
        restarted, _ = submit("a", 5, 1400, 450, epoch=1)
        assert restarted["detections"][0]["track_id"] != moved["detections"][0]["track_id"]
        now[0] = 1500
        resized, _ = submit("a", 6, 1500, 225, epoch=1, width=640)
        assert resized["detections"][0]["track_id"] != restarted["detections"][0]["track_id"]
        now[0] = 1501
        sim, _ = submit("a", 7, 1501, 225, epoch=1, width=640, provenance="simulation")
        assert sim["detections"][0]["track_id"] != resized["detections"][0]["track_id"]
        print("[PASS] reassignment, retirement, dimensions and provenance retire continuity")

        now[0] = 6502
        assert tracker.status()["active_track_count"] == 0
        old, _ = submit("a", 7, 1501, 225, epoch=1, width=640, provenance="simulation")
        assert "track_id" not in old["detections"][0]
        fresh, _ = submit("a", 8, 6502, 225, epoch=1, width=640)
        assert fresh["detections"][0]["track_id"] != sim["detections"][0]["track_id"]
        tracker.reset_active()
        repeated, _ = submit("a", 8, 6502, 225, epoch=1, width=640)
        assert "track_id" not in repeated["detections"][0]
        assert tracker.status_for_observation(None)["active_track_count"] == 0
        print("[PASS] expiry, reset, stale and missing observation")

    continuity = TrackingContinuity()
    scope = TrackingScope("a", None, 1280, 720)
    assert continuity.classify(scope, 1, 100) == "reset"
    assert continuity.classify(scope, 2, 1) == "reset"
    assert continuity.classify(scope, 5002, 2) == "advance"
    assert continuity.classify(scope, 10003, 3) == "reset"
    for index in range(MAX_TRACKING_SOURCES + 10):
        assert continuity.classify(replace(scope, source_id=f"source{index}"), 20000, 1) == "reset"
    assert len(continuity._watermarks) == MAX_TRACKING_SOURCES
    print("[PASS] frame-number reset, gap boundary and bounded watermarks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
