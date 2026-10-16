"""Simulation-only crosswalk conflict arbitration and safe virtual hold regression."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/pc-studio/backend"))

from app.core.exceptions import AppError
from app.services.crosswalks import CrosswalkService
from app.services.crosswalk_signals import CrosswalkSignalService
from app.services.crosswalk_signal_coordinator import (
    CLEARANCE_SECONDS, coordinate_crosswalk_signals, movements_conflict,
)
from app.services.signal_rules import SignalRulesService

ALL = ["vehicle_vehicle", "vehicle_pedestrian", "pedestrian_vehicle", "pedestrian_pedestrian"]
POLYGON = [[0, 0], [1280, 0], [1280, 720], [0, 720]]


def crossing(identity: str, camera: str) -> dict:
    return {
        "id": identity, "label": identity, "location": "",
        "camera_side_a_id": camera, "camera_side_b_id": None,
        "regions": [{"id": "region_1", "label": "Road",
                     "vertices": POLYGON, "vertices_by_side": {"a": POLYGON}}],
    }


def frame(source: str, n: int, labels: list[str]) -> dict:
    return {
        "source_id": source, "model_id": "demo", "error": None,
        "frame": {
            "source_id": source, "timestamp_ms": int(time.time() * 1000),
            "source_frame_number": n, "image_width": 1280, "image_height": 720,
            "detections": [
                {"class_name": label, "box_xyxy": [100 + 60 * i, 100, 160 + 60 * i, 200]}
                for i, label in enumerate(labels)
            ],
        },
    }


def movement(state: dict) -> str | None:
    if state["phase"] in ("vehicle_green", "vehicle_yellow"):
        return "vehicle"
    if state["phase"] in ("pedestrian_green", "pedestrian_flashing"):
        return "pedestrian"
    return None


def main() -> None:
    a = {"phase": "vehicle_green", "vehicle_go": True, "pedestrian_walk": False}
    b = {"phase": "vehicle_green", "vehicle_go": True, "pedestrian_walk": False}
    link = {"source_crosswalk_id": "a", "destination_crosswalk_id": "b", "movement_conflicts": ALL}
    outputs, held, grants, released = coordinate_crosswalk_signals(
        {"a": a, "b": b}, [link], now=0.0, previous_grants={}, released={}
    )
    assert len(held) == 1 and not (outputs["a"]["vehicle_go"] and outputs["b"]["vehicle_go"])
    assert outputs[next(iter(held))]["phase"] == "all_red"
    assert outputs[next(iter(held))]["seconds_remaining"] == 0.0
    assert not coordinate_crosswalk_signals({"a": a, "b": b}, [], now=0.0, previous_grants={}, released={})[1]

    for am, bm in [("vehicle", "vehicle"), ("vehicle", "pedestrian"),
                   ("pedestrian", "vehicle"), ("pedestrian", "pedestrian")]:
        assert movements_conflict([link], "a", am, "b", bm)
        assert movements_conflict([link], "b", bm, "a", am)
    assert not movements_conflict([], "a", "vehicle", "b", "vehicle")

    # Never revoke previously granted pedestrian CLEAR to admit a vehicle.
    clearance = {
        "a": {"phase": "pedestrian_flashing", "vehicle_go": False,
              "pedestrian_walk": False, "pedestrian_clear": True},
        "b": {"phase": "vehicle_green", "vehicle_go": True,
              "pedestrian_walk": False, "pedestrian_clear": False},
    }
    protected, protected_holds, _, _ = coordinate_crosswalk_signals(
        clearance, [link], now=5.0, previous_grants={"a": "pedestrian"}, released={},
        emergency_targets={"b"},
    )
    assert protected["a"]["pedestrian_clear"] is True
    assert "b" in protected_holds and protected["b"]["vehicle_go"] is False

    # Blocked virtual output stays red until explicit clearance is elapsed.
    all_red_a = {"a": {"phase": "all_red", "vehicle_go": False, "pedestrian_walk": False}, "b": b}
    released_states, held, grants_after_release, recent = coordinate_crosswalk_signals(
        all_red_a, [link], now=1.0, previous_grants=grants, released=released
    )
    assert "b" in held
    cleared, cleared_holds, _, _ = coordinate_crosswalk_signals(
        all_red_a, [link], now=1.0 + CLEARANCE_SECONDS + 0.1,
        previous_grants=grants_after_release, released=recent,
    )
    assert "b" not in cleared_holds and cleared["b"]["vehicle_go"] is True
    assert not (released_states["a"]["vehicle_go"] and released_states["b"]["vehicle_go"])

    with TemporaryDirectory(prefix="aitl-conflicts-") as tmp:
        root = Path(tmp)
        crossings = CrosswalkService(config_path=root / "crosswalks.json")
        items = [crossing("cross_a", "sim_a"), crossing("cross_b", "sim_b")]
        link2 = {"id": "link_1", "source_crosswalk_id": "cross_a",
                 "destination_crosswalk_id": "cross_b", "source_edge": "1",
                 "destination_edge": "3", "movement_conflicts": ALL}
        def save(l: dict) -> dict:
            return crossings.save({
                "schema_version": 1, "crosswalks": items,
                "network": {"positions": {}, "links": [l]},
            })
        saved = save(link2)
        assert saved["network"]["links"][0]["movement_conflicts"] == sorted(ALL)
        for invalid in (["vehicle_vehicle", "vehicle_vehicle"], ["not_a_movement"]):
            try:
                save({**link2, "movement_conflicts": invalid})
            except AppError as error:
                assert error.status_code == 422
            else:
                raise AssertionError("Invalid movement conflict accepted")
        save(link2)

        rules = SignalRulesService(config_path=root / "rules.json", history_path=root / "legacy.jsonl")
        clock = [0.0]
        signals = CrosswalkSignalService(
            crosswalks=crossings, shared_rules=rules, clock=lambda: clock[0],
            history_root=root / "history",
        )
        observed = []
        for _ in range(130):
            current = signals.status(simulation_enabled=True)
            states = current["crosswalks"]
            alpha = movement(states["cross_a"]["signal"])
            beta = movement(states["cross_b"]["signal"])
            assert not (alpha and beta and movements_conflict([link2], "cross_a", alpha, "cross_b", beta)), current
            observed.append((alpha, beta))
            clock[0] += 1.0
        assert any(alpha == "vehicle" for alpha, _ in observed)
        assert any(beta == "vehicle" for _, beta in observed), "Held crosswalk never resumed"
        assert any(alpha is None and beta is not None for alpha, beta in observed)

        link2["emergency_route"] = "source_to_destination"
        save(link2)
        clock[0] += 1.0
        signals.ingest_camera_results({"sim_a": frame("sim_a", 1, ["ambulance"])},
                                      simulation_enabled=True, model_id="demo")
        clock[0] += 1.1
        signals.ingest_camera_results({"sim_a": frame("sim_a", 2, ["ambulance"])},
                                      simulation_enabled=True, model_id="demo")
        status = signals.status(simulation_enabled=True)
        assert status["coordination_enabled"] is True
        assert status["movement_conflicts_configured"] is True
        assert status["hardware_actuation_enabled"] is False
        assert status["crosswalks"]["cross_b"]["emergency_priority"] is not None
        alpha = movement(status["crosswalks"]["cross_a"]["signal"])
        beta = movement(status["crosswalks"]["cross_b"]["signal"])
        assert not (alpha and beta and movements_conflict([link2], "cross_a", alpha, "cross_b", beta))
        signals.status(simulation_enabled=False)
        assert signals.status(simulation_enabled=False)["crosswalks"]["cross_a"]["signal"] is None

    print("[PASS] link conflict validation and all virtual conflicting-green combinations")
    print("[PASS] coordinated local-clock holds, safe clearance and opt-in emergency priority")


if __name__ == "__main__":
    main()
