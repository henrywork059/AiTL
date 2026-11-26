"""Native two-junction directed transfer, capacity and protected phase trial."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "AI_Traffic_Light/apps/pc-studio/backend"))
from app.services.sumo_corridor import JUNCTIONS, load_corridor
from app.services.sumo_corridor_session import CorridorSession


def run(seed):
    session = CorridorSession(seed)
    try:
        path = Path(session._temp.name) / "network.xml"
        maps = load_corridor(path)
        lane = ET.parse(path).getroot().find("edge[@id='AB']/lane[@id='AB_1']")
        assert lane is not None
        x0 = float(lane.get("shape").split()[0].split(",")[0])
        digest = hashlib.sha256()
        prior = {}
        entered = {}
        exited = {}
        seen = set()
        blocked = spillback = concurrent = pedestrian_entries = clearance = peak_link = 0
        cycles = ["vehicle_green"] * 100 + ["vehicle_yellow"] * 15 + ["all_red"] * 10 + ["pedestrian_green"] * 60 + ["pedestrian_flashing"] * 25 + ["all_red"] * 10
        for tick in range(4000):
            phases = {"A": cycles[tick % len(cycles)],
                      "B": "all_red" if tick < 600 else cycles[(tick - 600 + 80) % len(cycles)]}
            session.set_junction_phases(phases)
            session.advance()
            rows = sorted(session.agents(), key=lambda a: a.id)
            current = {a.id: a for a in rows}
            assert len(current) == len(rows)
            grants = {}
            for j in JUNCTIONS:
                mapping = maps[j]
                state = session.last_permission[j]
                g = {i for i, ch in enumerate(state) if ch == "G"}
                grants[j] = g
                assert set(state) <= {"G", "r"} and len(state) == len(mapping.links)
                inside_v = any(a.kind == "vehicle" and a.road_id.startswith(f":{j}_") for a in prior.values())
                inside_p = any(a.kind == "pedestrian" and a.road_id in mapping.crossing_edges for a in prior.values())
                if phases[j] == "vehicle_green":
                    assert g <= set(mapping.vehicles) and len(g) <= 1
                    if inside_v or inside_p:
                        assert not g
                elif phases[j] == "pedestrian_green":
                    assert g in (set(), set(mapping.pedestrians))
                    if inside_v:
                        assert not g
                else:
                    assert not g
            if grants["A"] and grants["B"] and phases["A"] != phases["B"]:
                concurrent += 1
            # For the straight horizontal connector, x minus lane start is
            # front-bumper distance. Five-metre cars and 2.5 m gap need 7.5 m
            # behind the nearest rear bumper. Use a conservative 12 m cutoff.
            on_link_before = [a for a in prior.values() if a.kind == "vehicle" and a.road_id == "AB"]
            upstream_waiting = any(a.kind == "vehicle" and a.road_id == "WA" and a.speed_m_s < .1 for a in prior.values())
            if phases["A"] == "vehicle_green" and upstream_waiting and any(a.x_m - x0 < 12 for a in on_link_before):
                blocked += 1
                assert not grants["A"]
                if phases["B"] == "all_red":
                    spillback += 1
            peak_link = max(peak_link, sum(a.kind == "vehicle" and a.road_id == "AB" for a in rows))
            for a in rows:
                old = prior.get(a.id)
                if a.kind == "vehicle":
                    seen.add(a.engine_id)
                    if a.road_id == "AB" and a.engine_id not in entered:
                        assert old is not None and old.road_id.startswith(":A_")
                        entered[a.engine_id] = tick
                    if old is not None and old.road_id == "AB" and a.road_id.startswith(":B_"):
                        assert a.engine_id in entered and a.engine_id not in exited
                        assert phases["B"] == "vehicle_green" and grants["B"]
                        exited[a.engine_id] = tick
                    if old is not None and old.road_id == "WA" and a.road_id.startswith(":A_"):
                        assert phases["A"] == "vehicle_green" and grants["A"]
                elif old is not None:
                    for j in JUNCTIONS:
                        crossings = maps[j].crossing_edges
                        if a.road_id in crossings and old.road_id not in crossings:
                            assert phases[j] == "pedestrian_green" and grants[j]
                            pedestrian_entries += 1
                        if a.road_id in crossings and old.road_id in crossings and phases[j] == "pedestrian_flashing":
                            clearance += 1
            assert not set(a.engine_id for a in rows if a.kind == "vehicle").intersection(session.arrived)
            digest.update(json.dumps([tick, phases, session.last_permission, [asdict(a) for a in rows]], sort_keys=True).encode())
            prior = current
        expected = {f"v{i}" for i in range(16)}
        assert seen == set(entered) == set(exited) == session.arrived == expected
        assert all(exited[i] > entered[i] for i in expected)
        assert blocked > 0 and spillback > 0 and peak_link >= 2 and concurrent > 0
        assert pedestrian_entries > 0 and len(session.person_arrived) == 4
        travel = {i: round((exited[i] - entered[i]) * .2, 1) for i in sorted(expected)}
        return {"digest": digest.hexdigest(), "transferred": len(exited), "arrived": len(session.arrived),
                "link_travel_time_s_by_id": travel, "peak_link_vehicles": peak_link,
                "blocked_admission_ticks": blocked, "spillback_ticks": spillback,
                "independent_concurrent_grant_ticks": concurrent, "pedestrian_entries": pedestrian_entries,
                "pedestrian_clearance_samples": clearance, "pedestrian_arrivals": len(session.person_arrived)}
    finally:
        session.close()
        assert not session.proc.is_alive()


if __name__ == "__main__":
    a, b = run(42), run(42)
    assert a == b, "Corridor experiment not repeatable"
    result = {"evidence": "executed synthetic native two-junction corridor", "seed": 42,
              "step_s": .2, "duration_s": 800, "repetitions": [a, b],
              "limitations": "one directed corridor, explicit phase schedule, no live topology or control"}
    Path(sys.argv[1]).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
