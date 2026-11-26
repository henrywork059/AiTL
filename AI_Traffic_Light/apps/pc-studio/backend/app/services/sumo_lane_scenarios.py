"""Conservative lane-scenario admission for the optional synthetic SUMO engine.

This is a restrictive experiment, not a traffic controller or a physical safety model.
The protected phase remains an upper bound on movement permission.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import random
import xml.etree.ElementTree as ET

from app.services.sumo_shadow_fixture import PhaseMap, generate_controlled_fixture

ROUTES = {"straight_w": ("WC", "CE"), "left_w": ("WC", "CN"),
          "right_w": ("WC", "CS"), "straight_e": ("EC", "CW")}
APPROACHES = frozenset(a for a, _ in ROUTES.values())


@dataclass(frozen=True)
class LaneVehicle:
    ident: str
    lane: str
    position: float
    length: float
    gap: float
    destination: str | None = None


def choose_permission(mapping: PhaseMap, phase: str, vehicles: tuple[LaneVehicle, ...],
                      *, vehicle_inside: bool, pedestrian_inside: bool) -> str:
    """Grant at most one vehicle link, only to a lane leader with room beyond C."""
    red = "r" * len(mapping.links)
    if phase != "vehicle_green":
        return mapping.state(phase, vehicle_inside=vehicle_inside,
                             pedestrian_inside=pedestrian_inside)
    if vehicle_inside or pedestrian_inside:
        return red
    leaders: dict[str, LaneVehicle] = {}
    for v in sorted(vehicles, key=lambda v: (-v.position, v.ident)):
        leaders.setdefault(v.lane, v)
    for v in sorted(leaders.values(), key=lambda v: (-v.position, v.ident)):
        if v.destination is None:
            continue
        for index, (source, target, _) in enumerate(mapping.links):
            if source != v.lane or target.rsplit("_", 1)[0] != v.destination:
                continue
            if (source.rsplit("_", 1)[0], v.destination) not in ROUTES.values():
                continue
            # SUMO lane position is the front bumper. The minimum rear position
            # on the exit must leave space for the incoming vehicle plus its gap.
            if any(other.lane == target and other.position - other.length < v.length + v.gap
                   for other in vehicles):
                continue
            return red[:index] + "G" + red[index + 1:]
    return red


def observe_lanes(engine) -> tuple[LaneVehicle, ...]:
    rows = []
    for ident in engine.vehicle.getIDList():
        road = engine.vehicle.getRoadID(ident)
        route = engine.vehicle.getRoute(ident)
        index = engine.vehicle.getRouteIndex(ident)
        target = None
        if road in APPROACHES and 0 <= index < len(route) - 1 and route[index] == road:
            target = route[index + 1]
        rows.append(LaneVehicle(ident, engine.vehicle.getLaneID(ident),
                    engine.vehicle.getLanePosition(ident), engine.vehicle.getLength(ident),
                    engine.vehicle.getMinGap(ident), target))
    return tuple(rows)


def write_lane_demand(root: Path, seed: int) -> None:
    """Finite, seed-repeatable demand including a temporarily obstructed exit."""
    rng = random.Random(seed)
    routes = ET.Element("routes")
    ET.SubElement(routes, "vType", id="car", vClass="passenger", sigma="0.5")
    for name, edges in ROUTES.items():
        ET.SubElement(routes, "route", id=name, edges=" ".join(edges))
    ET.SubElement(routes, "route", id="blocker_exit", edges="CE")
    blocker = ET.SubElement(routes, "vehicle", id="blocker", type="car",
                            route="blocker_exit", depart="0", departPos="5", departSpeed="0")
    ET.SubElement(blocker, "stop", lane="CE_1", endPos="10", duration="60")
    schedule = [(0, "straight_w"), (2, "left_w"), (4, "right_w"), (6, "straight_e")]
    names = tuple(ROUTES)
    schedule += [(8 + i * 3, rng.choice(names)) for i in range(12)]
    for i, (depart, route) in enumerate(schedule):
        ET.SubElement(routes, "vehicle", id=f"v{i}_{route}", type="car",
                      route=route, depart=str(depart))
    # Keep XML departure order (all persons depart after the final vehicle).
    for i in range(4):
        p = ET.SubElement(routes, "person", id=f"p{i}", depart=str(43 + i * 2))
        ET.SubElement(p, "walk", edges="WC CN")
    ET.ElementTree(routes).write(root / "routes.xml", encoding="utf-8", xml_declaration=True)


def generate_lane_fixture(root: Path, seed: int) -> None:
    generate_controlled_fixture(root)
    write_lane_demand(root, seed)
