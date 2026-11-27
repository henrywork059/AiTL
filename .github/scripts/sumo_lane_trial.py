"""Actual pinned native lane, turning, obstruction and clearance experiment."""
from dataclasses import asdict
import hashlib
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "AI_Traffic_Light/apps/pc-studio/backend"))
from app.services.sumo_shadow_fixture import PhaseMap
from app.services.sumo_shadow_runtime import GeneratedSession


def run(seed):
    session = GeneratedSession(seed, lane_scenario=True)
    mapping = PhaseMap.load(Path(session._temp.name) / "network.xml")
    network = ET.parse(Path(session._temp.name) / "network.xml").getroot()
    stop_lines = {}
    for road in ("WC", "EC"):
        lane = network.find(f"edge[@id='{road}']/lane[@id='{road}_1']")
        assert lane is not None
        stop_lines[road] = tuple(float(x) for x in lane.attrib["shape"].split()[-1].split(","))
    digest = hashlib.sha256()
    prior = ()
    blocked_ticks = queued_ticks = ped_crossing_ticks = 0
    stop_line_ticks = vehicle_entries = pedestrian_entries = clearance_ticks = 0
    seen_turns = set()
    route_targets = {"straight_w": "CE", "left_w": "CN", "right_w": "CS", "straight_e": "CW"}
    cycle = ["vehicle_green"] * 100 + ["vehicle_yellow"] * 15 + ["all_red"] * 10 + ["pedestrian_green"] * 60 + ["pedestrian_flashing"] * 25 + ["all_red"] * 10
    try:
        for tick in range(2200):
            phase = cycle[tick % len(cycle)]
            session.set_phase(phase)
            session.advance()
            rows = sorted(session.agents(), key=lambda a: a.id)
            grant = {i for i, ch in enumerate(session.last_permission) if ch == "G"}
            if phase == "vehicle_green":
                assert len(grant) <= 1 and not grant.intersection(mapping.pedestrians)
                if any(a.kind == "pedestrian" and a.road_id in mapping.crossing_edges or
                       a.kind == "vehicle" and a.road_id.startswith(":C_") for a in prior):
                    assert not grant
                if tick < 250 and any(a.engine_id == "blocker" and a.road_id == "CE" and a.speed_m_s < .1 for a in prior):
                    assert all(mapping.links[i][1] != "CE_1" for i in grant)
                    blocked_ticks += 1
            elif phase == "pedestrian_green":
                assert grant in (set(), set(mapping.pedestrians))
                if any(a.kind == "vehicle" and a.road_id.startswith(":C_") for a in prior):
                    assert not grant
            else:
                assert not grant
            queued = [a for a in rows if a.kind == "vehicle" and a.road_id == "WC" and a.speed_m_s < .1]
            if len(queued) >= 2:
                queued_ticks += 1
            if any(a.kind == "pedestrian" and a.road_id in mapping.crossing_edges for a in rows):
                ped_crossing_ticks += 1
            # Native positions use the front bumper; compare against the lane endpoint
            # rather than an assumed camera coordinate. Require a stopped leader
            # near the actual stop line, not just a queue somewhere on the approach.
            if len(queued) >= 2 and any(math.dist((a.x_m, a.y_m), stop_lines["WC"]) <= 8 for a in queued):
                stop_line_ticks += 1
            previous = {a.id: a for a in prior}
            for a in rows:
                old = previous.get(a.id)
                if old is not None and a.kind == "vehicle" and old.road_id in stop_lines and a.road_id.startswith(":C_"):
                    vehicle_entries += 1
                    target = route_targets[a.engine_id.split("_", 1)[1]]
                    assert phase == "vehicle_green" and any(
                        mapping.links[i][0] == old.road_id + "_1" and
                        mapping.links[i][1] == target + "_1" for i in grant
                    ), (tick, phase, old, a, grant)
                if old is not None and a.kind == "pedestrian":
                    was_crossing = old.road_id in mapping.crossing_edges
                    now_crossing = a.road_id in mapping.crossing_edges
                    if now_crossing and not was_crossing:
                        pedestrian_entries += 1
                        assert phase == "pedestrian_green" and any(
                            mapping.links[i][1].rsplit("_", 1)[0] == a.road_id for i in grant
                        ), (tick, phase, old, a, grant)
                    if phase == "pedestrian_flashing" and was_crossing and now_crossing:
                        clearance_ticks += 1
                if (a.engine_id.endswith("_left_w") and a.road_id == "CN" or
                    a.engine_id.endswith("_right_w") and a.road_id == "CS"):
                    seen_turns.add(a.road_id)
            digest.update(json.dumps([tick, phase, session.last_permission, [asdict(a) for a in rows]], sort_keys=True).encode())
            prior = rows
        assert blocked_ticks > 0 and queued_ticks > 0, (blocked_ticks, queued_ticks)
        assert stop_line_ticks > 0 and vehicle_entries > 0 and pedestrian_entries > 0, (stop_line_ticks, vehicle_entries, pedestrian_entries)
        assert seen_turns == {"CN", "CS"}, seen_turns
        assert "v0_straight_w" in session.arrived and "v1_left_w" in session.arrived and "v2_right_w" in session.arrived
        assert ped_crossing_ticks > 0 and session.person_arrived
        return {"digest": digest.hexdigest(), "blocked_ticks": blocked_ticks,
                "queued_ticks": queued_ticks, "stop_line_queue_ticks": stop_line_ticks,
                "vehicle_entry_transitions": vehicle_entries, "pedestrian_entry_transitions": pedestrian_entries,
                "pedestrian_clearance_occupancy_ticks": clearance_ticks, "pedestrian_crossing_ticks": ped_crossing_ticks,
                "turn_exits": sorted(seen_turns), "vehicle_arrivals": len(session.arrived),
                "pedestrian_arrivals": len(session.person_arrived)}
    finally:
        session.close()
        assert not session.proc.is_alive()


if __name__ == "__main__":
    a, b = run(42), run(42)
    assert a == b, "Lane scenario is not repeatable"
    result = {"evidence": "executed synthetic native lane scenario", "seed": 42,
              "step_s": .2, "duration_s": 440, "repetitions": [a, b],
              "limitations": "isolated single junction, one vehicle link at a time; not a live controller comparison"}
    Path(sys.argv[1]).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
