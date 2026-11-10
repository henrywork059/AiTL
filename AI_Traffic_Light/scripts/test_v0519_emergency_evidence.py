"""Deterministic source-frame confirmation regressions; software-only signals."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/pc-studio/backend"))

from app.services.crosswalks import CrosswalkService  # noqa: E402
from app.services.crosswalk_signals import CrosswalkSignalService  # noqa: E402
from app.services.signal_rules import SignalRulesService  # noqa: E402

POLYGON = [[0, 0], [1280, 0], [1280, 720], [0, 720]]


def frame(source: str, number: int, timestamp: int, classes: list[str], model: str = "demo") -> dict:
    return {
        "source_id": source, "model_id": model, "error": None,
        "frame": {
            "source_id": source, "timestamp_ms": timestamp, "source_frame_number": number,
            "image_width": 1280, "image_height": 720,
            "detections": [
                {"class_name": name, "box_xyxy": [100 + i * 60, 100, 140 + i * 60, 200]}
                for i, name in enumerate(classes)
            ],
        },
    }


def setup(root: Path, clock: list[float]) -> CrosswalkSignalService:
    crosses = CrosswalkService(config_path=root / "crosswalks.json")
    crosswalk = {
        "id": "cross_a", "label": "A", "location": "",
        "camera_side_a_id": "sim_a", "camera_side_b_id": "sim_b",
        "regions": [{
            "id": "region_1", "label": "Road", "camera_side": None,
            "vertices": POLYGON, "vertices_by_side": {"a": POLYGON, "b": POLYGON},
        }],
    }
    target = {"id": "cross_b", "label": "B", "location": "", "regions": []}
    link = {
        "id": "route", "source_crosswalk_id": "cross_a", "destination_crosswalk_id": "cross_b",
        "source_edge": "1", "destination_edge": "3", "emergency_route": "source_to_destination",
        "movement_conflicts": ["vehicle_vehicle"],
    }
    crosses.save({"schema_version": 1, "crosswalks": [crosswalk, target],
                  "network": {"positions": {}, "links": [link]}})
    rules = SignalRulesService(config_path=root / "rules.json", history_path=root / "global.jsonl")
    config = rules.get_config()
    config["mode"] = "fixed"
    rules.save_config(config)
    return CrosswalkSignalService(crosswalks=crosses, shared_rules=rules,
                                  clock=lambda: clock[0], history_root=root / "history")


def ingest(service: CrosswalkSignalService, a: dict | None, b: dict | None, model: str = "demo") -> dict:
    results = {item["source_id"]: item for item in (a, b) if item is not None}
    service.ingest_camera_results(results, simulation_enabled=True, model_id=model)
    return service.status(simulation_enabled=True)


def main() -> None:
    with TemporaryDirectory(prefix="aitl-v0519-") as temp:
        root = Path(temp)
        clock = [100.0]
        service = setup(root, clock)
        t0 = int(time.time() * 1000) - 3000
        positive_a1 = frame("sim_a", 1, t0, ["ambulance"])

        # Polling the same ambulance frame while the unrelated camera advances
        # must not manufacture a second longitudinal observation.
        state = ingest(service, positive_a1, frame("sim_b", 1, t0, []))
        state = ingest(service, positive_a1, frame("sim_b", 2, t0 + 1100, []))
        assert state["crosswalks"]["cross_b"]["emergency_priority"] is None, state

        # Distinct synchronized views of one event still span zero time.
        service = setup(root, clock)
        state = ingest(service, frame("sim_a", 1, t0, ["ambulance"]),
                       frame("sim_b", 1, t0, ["ambulance"]))
        assert state["crosswalks"]["cross_b"]["emergency_priority"] is None, state

        # A new source frame at least one second later may confirm the request.
        state = ingest(service, frame("sim_a", 2, t0 + 1100, ["ambulance"]),
                       frame("sim_b", 2, t0 + 1100, ["ambulance"]))
        priority = state["crosswalks"]["cross_b"]["emergency_priority"]
        assert priority and priority["source_crosswalk_id"] == "cross_a", state
        assert state["hardware_actuation_enabled"] is False
        assert state["crosswalks"]["cross_b"]["signal"]["effective_duration_seconds"] <= 30

        # Requests expire at the existing 30-second bound.
        clock[0] += 31
        state = service.status(simulation_enabled=True)
        assert state["crosswalks"]["cross_b"]["emergency_priority"] is None, state

        # A fresh negative frame resets an earlier positive; one later positive
        # alone must not complete the old confirmation window.
        service = setup(root, clock)
        ingest(service, frame("sim_a", 1, t0, ["ambulance"]), frame("sim_b", 1, t0, []))
        state = ingest(service, frame("sim_a", 2, t0 + 1100, []), frame("sim_b", 2, t0 + 1100, []))
        assert state["crosswalks"]["cross_b"]["emergency_priority"] is None, state
        state = ingest(service, frame("sim_a", 3, t0 + 1200, ["ambulance"]), frame("sim_b", 3, t0 + 1200, []))
        assert state["crosswalks"]["cross_b"]["emergency_priority"] is None, state
        state = ingest(service, frame("sim_a", 4, t0 + 2300, ["ambulance"]), frame("sim_b", 4, t0 + 2300, []))
        assert state["crosswalks"]["cross_b"]["emergency_priority"], state

        # A camera reconnect can reset its frame number while timestamps advance.
        service = setup(root, clock)
        ingest(service, frame("sim_a", 48, t0, ["ambulance"]), frame("sim_b", 48, t0, []))
        state = ingest(service, frame("sim_a", 1, t0 + 1100, ["ambulance"]),
                       frame("sim_b", 1, t0 + 1100, []))
        assert state["crosswalks"]["cross_b"]["emergency_priority"], state

        # A new negative frame after reconnect must clear previous positive evidence.
        service = setup(root, clock)
        ingest(service, frame("sim_a", 48, t0, ["ambulance"]), frame("sim_b", 48, t0, []))
        ingest(service, frame("sim_a", 1, t0 + 1100, []), frame("sim_b", 1, t0 + 1100, []))
        state = ingest(service, frame("sim_a", 2, t0 + 1200, ["ambulance"]),
                       frame("sim_b", 2, t0 + 1200, []))
        assert state["crosswalks"]["cross_b"]["emergency_priority"] is None, state

        # A larger frame number cannot override an older/replayed timestamp.
        service = setup(root, clock)
        ingest(service, frame("sim_a", 2, t0 + 1100, ["ambulance"]),
               frame("sim_b", 2, t0 + 1100, []))
        state = ingest(service, frame("sim_a", 99, t0 + 1000, ["ambulance"]),
                       frame("sim_b", 99, t0 + 1000, []))
        assert state["crosswalks"]["cross_b"]["emergency_priority"] is None, state

        # Missing or stale camera data and a model switch clear evidence.
        service = setup(root, clock)
        ingest(service, frame("sim_a", 1, t0, ["ambulance"]), frame("sim_b", 1, t0, []))
        state = ingest(service, None, frame("sim_b", 2, t0 + 1200, []))
        assert state["crosswalks"]["cross_b"]["emergency_priority"] is None, state

        service = setup(root, clock)
        ingest(service, frame("sim_a", 1, t0, ["ambulance"]), frame("sim_b", 1, t0, []))
        state = ingest(service, frame("sim_a", 2, t0 - 10000, ["ambulance"]),
                       frame("sim_b", 2, t0 + 1200, []))
        assert state["crosswalks"]["cross_b"]["emergency_priority"] is None, state

        service = setup(root, clock)
        ingest(service, frame("sim_a", 1, t0, ["ambulance"]), frame("sim_b", 1, t0, []))
        state = ingest(service, frame("sim_a", 2, t0 + 1200, ["ambulance"], "new"),
                       frame("sim_b", 2, t0 + 1200, [], "new"), model="new")
        assert state["crosswalks"]["cross_b"]["emergency_priority"] is None, state

    print("[PASS] repeated frames and unrelated camera updates cannot confirm emergency priority")
    print("[PASS] synchronized views do not satisfy the time gap; distinct fresh frames can")
    print("[PASS] negative, missing and model-switched evidence is cleared; hardware remains disabled")
    print("[PASS] reconnect frame resets allow fresh evidence; negative resets clear positives; replay blocked")


if __name__ == "__main__":
    main()
