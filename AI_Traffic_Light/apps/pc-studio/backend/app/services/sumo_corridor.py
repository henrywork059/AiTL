"""Trusted two-junction SUMO corridor; no configured/live network or controller ownership."""
from __future__ import annotations

import os
from pathlib import Path
import random
import subprocess
import xml.etree.ElementTree as ET

from app.services.sumo_shadow_fixture import PhaseMap, PHASES, native_netconvert
from app.services.sumo_lane_scenarios import choose_permission, observe_lanes

JUNCTIONS = ("A", "B")
MOVEMENTS = {"A": (("WA", "AB"),), "B": (("AB", "BE"),)}
APPROACHES = frozenset(("WA", "AB"))
EDGES = frozenset(("WA", "AW", "AB", "BA", "BE", "EB",
                   "NA", "AN", "SA", "AS", "QB", "BQ", "RB", "BR"))


def write_corridor(root: Path, seed: int) -> None:
    nodes = ET.Element("nodes")
    for name, x, y in (("W", -100, 0), ("A", 0, 0), ("B", 45, 0),
                       ("E", 145, 0), ("N", 0, 100), ("S", 0, -100),
                       ("Q", 45, 100), ("R", 45, -100)):
        ET.SubElement(nodes, "node", id=name, x=str(x), y=str(y),
                      type="traffic_light" if name in JUNCTIONS else "priority")
    edges = ET.Element("edges")
    for edge in sorted(EDGES):
        ET.SubElement(edges, "edge", {"id": edge, "from": edge[0], "to": edge[1],
                      "numLanes": "1", "speed": "10", "sidewalkWidth": "2"})
    routes = ET.Element("routes")
    ET.SubElement(routes, "vType", id="car", vClass="passenger", sigma="0.5")
    ET.SubElement(routes, "route", id="corridor", edges="WA AB BE")
    rng = random.Random(seed)
    depart = 0
    for i in range(16):
        ET.SubElement(routes, "vehicle", id=f"v{i}", type="car", route="corridor", depart=str(depart))
        depart += rng.randint(2, 4)
    for i in range(4):
        person = ET.SubElement(routes, "person", id=f"p{i}", depart=str(depart + i * 3))
        ET.SubElement(person, "walk", edges="WA AN" if i % 2 == 0 else "EB BQ")
    for name, node in (("nodes.xml", nodes), ("edges.xml", edges), ("routes.xml", routes)):
        ET.ElementTree(node).write(root / name, encoding="utf-8", xml_declaration=True)


def load_corridor(path: Path) -> dict[str, PhaseMap]:
    network = ET.parse(path).getroot()
    external = {e.get("id") for e in network.findall("edge") if e.get("function") is None}
    if external != EDGES:
        raise ValueError("Unexpected corridor topology")
    result = {}
    for junction in JUNCTIONS:
        crossings = frozenset(e.attrib["id"] for e in network.findall("edge")
                              if e.get("function") == "crossing" and e.attrib["id"].startswith(f":{junction}_"))
        if len(crossings) != 4:
            raise ValueError("Unexpected corridor crossings")
        result[junction] = PhaseMap.for_junction(network, junction, MOVEMENTS[junction], crossings)
    return result


def generate_corridor(root: Path, seed: int) -> None:
    native = native_netconvert()
    write_corridor(root, seed)
    subprocess.run([str(native), "--node-files", "nodes.xml", "--edge-files", "edges.xml",
                    "--crossings.guess", "true", "--output-file", "network.xml"],
                   cwd=root, env={**os.environ, "SUMO_HOME": str(native.parent.parent)},
                   capture_output=True, check=True, timeout=15)
    load_corridor(root / "network.xml")


def validate_phases(phases) -> dict[str, str]:
    if not isinstance(phases, dict) or set(phases) != set(JUNCTIONS) or any(
        not isinstance(phase, str) or phase not in PHASES for phase in phases.values()
    ):
        raise ValueError("Expected independent protected phases for A and B")
    return dict(phases)


def corridor_permissions(maps, phases, vehicles, vehicle_roads, pedestrian_roads):
    phases = validate_phases(phases)
    return {j: choose_permission(maps[j], phases[j], vehicles,
                                vehicle_inside=any(road.startswith(f":{j}_") for road in vehicle_roads),
                                pedestrian_inside=any(road in maps[j].crossing_edges for road in pedestrian_roads),
                                routes=MOVEMENTS[j]) for j in JUNCTIONS}


def observe_permissions(engine, maps, phases):
    return corridor_permissions(maps, phases, observe_lanes(engine, APPROACHES),
                                tuple(engine.vehicle.getRoadID(i) for i in engine.vehicle.getIDList()),
                                tuple(engine.person.getRoadID(i) for i in engine.person.getIDList()))
