"""Network coordinator fails closed for unavailable neighbors and invalid virtual lamps."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/pc-studio/backend"))
from app.services.crosswalk_signal_coordinator import coordinate_crosswalk_signals  # noqa: E402


def main() -> None:
    link = {"source_crosswalk_id": "a", "destination_crosswalk_id": "b",
            "movement_conflicts": ["vehicle_vehicle", "vehicle_pedestrian",
                                   "pedestrian_vehicle", "pedestrian_pedestrian"]}
    green = {"phase": "vehicle_green", "vehicle_go": True,
             "pedestrian_walk": False, "pedestrian_clear": False}
    # A vanished, conflict-linked controller must not leave A green.
    output, held, grants, recent = coordinate_crosswalk_signals(
        {"a": green}, [link], now=3.0, previous_grants={"a": "vehicle"}, released={})
    assert output["a"]["phase"] == "all_red" and not output["a"]["vehicle_go"]
    assert "a" in held and output["a"]["coordination_blocked_by"] == "b"
    assert "a" not in grants and recent["a"][0] == "vehicle"
    # A malformed phase/green combination must never bypass the interlock.
    invalid = {"phase": "all_red", "vehicle_go": True,
               "pedestrian_walk": False, "pedestrian_clear": False}
    output, _, grants, _ = coordinate_crosswalk_signals(
        {"a": invalid, "b": green}, [link], now=4.0, previous_grants={}, released={})
    assert output["a"]["phase"] == "all_red" and not output["a"]["vehicle_go"]
    assert "a" not in grants
    # Restored valid states continue to respect the original conflict rule.
    output, held, _, _ = coordinate_crosswalk_signals(
        {"a": green, "b": green}, [link], now=8.0, previous_grants={}, released={})
    assert not (output["a"]["vehicle_go"] and output["b"]["vehicle_go"]), (output, held)
    print("[PASS] absent neighbor and invalid virtual signal fail closed")


if __name__ == "__main__":
    main()
