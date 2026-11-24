"""Emergency evidence and clearance history regressions (software only)."""
from itertools import product
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/pc-studio/backend"))

from app.services.crosswalk_signal_coordinator import (
    coordinate_crosswalk_signals as run, movement_of, movements_conflict,
)
from app.services.emergency_evidence import confirmed_emergency
from test_v0519_emergency_evidence import setup, frame, ingest


def test_coordinator():
    link = {"source_crosswalk_id": "a", "destination_crosswalk_id": "b",
            "movement_conflicts": ["vehicle_vehicle"]}
    ped = {"phase": "pedestrian_green", "pedestrian_walk": True, "vehicle_go": False}
    car = {"phase": "vehicle_green", "vehicle_go": True, "pedestrian_walk": False}
    red = {"phase": "all_red", "vehicle_go": False, "pedestrian_walk": False}
    clear = {"phase": "pedestrian_flashing", "pedestrian_clear": True,
             "pedestrian_walk": False, "vehicle_go": False}
    invalid = {"phase": "all_red", "vehicle_go": True}
    out, held, grants, history = run({"a": ped, "b": car}, [link], now=1,
                                    previous_grants={"a": "vehicle"}, released={})
    assert out["a"]["pedestrian_walk"] and not out["b"]["vehicle_go"]
    assert "b" in held and history["a"] == ("vehicle", 1)
    out, held, grants, history = run({"a": ped, "b": car}, [link], now=2.99,
                                    previous_grants=grants, released=history)
    assert "b" in held
    out, held, _, _ = run({"a": ped, "b": car}, [link], now=3,
                           previous_grants=grants, released=history)
    assert "b" not in held and out["b"]["vehicle_go"]
    assert not run({"a": invalid}, [], now=0, previous_grants={}, released={})[0]["a"]["vehicle_go"]
    conflicts = ["vehicle_vehicle", "vehicle_pedestrian", "pedestrian_vehicle", "pedestrian_pedestrian"]
    all_link = {**link, "movement_conflicts": conflicts}
    out, held, _, _ = run({"a": clear, "b": car}, [all_link], now=0,
                          previous_grants={"a": "pedestrian"}, released={}, emergency_targets={"b"})
    assert out["a"]["pedestrian_clear"] and "b" in held
    out, held, _, _ = run({"a": car}, [all_link], now=0, previous_grants={"a": "vehicle"}, released={})
    assert "a" in held and not out["a"]["vehicle_go"]
    _, held, _, history = run({"a": red, "b": car}, [all_link], now=1,
                               previous_grants={"a": "pedestrian"}, released={"a": ("vehicle", 0)})
    assert history["a"] == ("both", 1) and "b" in held
    for a, b, conflict in product([car, ped, clear, red], [car, ped, clear, red], conflicts):
        links = [{**link, "movement_conflicts": [conflict]}]
        out, *_ = run({"a": a, "b": b}, links, now=0, previous_grants={}, released={})
        am, bm = map(movement_of, (out["a"], out["b"]))
        assert not (am and bm and movements_conflict(links, "a", am, "b", bm))
    print("[PASS] release history, invalid standalone lamp, protected CLEAR, unavailable neighbor and 64 pairs")


def test_evidence():
    def ev(*rows):
        return {"model_id": "m", "positive": {r: r[2] for r in rows}}
    assert confirmed_emergency(ev(("a", 1, 7000, "m"), ("a", 2, 8100, "m")), 10000, 5000)
    assert not confirmed_emergency(ev(("a", 1, 7000, "m"), ("a", 1, 8100, "m")), 10000, 5000)
    assert not confirmed_emergency(ev(("a", 1, 7000, "m"), ("b", 2, 8100, "m")), 10000, 5000)
    assert not confirmed_emergency(ev(("a", 1, 4000, "m"), ("a", 2, 8100, "m")), 10000, 5000)
    assert not confirmed_emergency(ev(("a", 1, 7000, "m"), ("a", 2, 11000, "m")), 10000, 5000)
    assert not confirmed_emergency(ev(("a", 1, 7000, "m"), ("a", 2, 8100, "other")), 10000, 5000)
    assert not confirmed_emergency(None, 10000, 5000)
    print("[PASS] seven distinct/fresh emergency evidence cases")


def test_service():
    with TemporaryDirectory() as folder:
        clock = [100.0]
        service = setup(Path(folder), clock)
        t0 = int(time.time() * 1000) - 3000
        ingest(service, frame("sim_a", 1, t0, ["ambulance"]), frame("sim_b", 1, t0, []))
        state = ingest(service, frame("sim_a", 2, t0 + 1100, ["ambulance"]),
                       frame("sim_b", 2, t0 + 1100, []))
        assert state["crosswalks"]["cross_b"]["emergency_priority"]
        state = ingest(service, frame("sim_a", 3, t0 + 1200, []),
                       frame("sim_b", 3, t0 + 1200, []))
        assert state["crosswalks"]["cross_b"]["emergency_priority"] is None
        assert not state["crosswalks"]["cross_b"]["signal"]["emergency_priority_active"]
        assert not state["hardware_actuation_enabled"]
        # A missing view withdraws a newly confirmed request too.
        ingest(service, frame("sim_a", 4, t0 + 1300, ["ambulance"]),
               frame("sim_b", 4, t0 + 1300, []))
        state = ingest(service, frame("sim_a", 5, t0 + 2400, ["ambulance"]),
                       frame("sim_b", 5, t0 + 2400, []))
        assert state["crosswalks"]["cross_b"]["emergency_priority"]
        state = ingest(service, None, frame("sim_b", 6, t0 + 2500, []))
        assert state["crosswalks"]["cross_b"]["emergency_priority"] is None
        print("[PASS] negative and missing evidence withdraw active virtual priority")


if __name__ == "__main__":
    test_coordinator()
    test_evidence()
    test_service()
