"""Evaluation-only gate adapters; never alter original camera/editor pixels."""
from __future__ import annotations

import math
from pathlib import Path
import xml.etree.ElementTree as ET

from app.services.simulation_gate_metrics import GateObservation
from app.services.legacy_world import (EASTBOUND_STOP_LINE, WESTBOUND_STOP_LINE,
                                       TOP_PEDESTRIAN_WAIT_Y, BOTTOM_PEDESTRIAN_WAIT_Y)


def legacy_observations(vehicles, pedestrians):
    rows = []
    width = WESTBOUND_STOP_LINE - EASTBOUND_STOP_LINE
    for i, a in enumerate(vehicles):
        x = a.x + a.width / 2
        progress = ((x-EASTBOUND_STOP_LINE) if a.direction > 0 else (WESTBOUND_STOP_LINE-x)) / width
        rows.append(GateObservation(f"v{i}", "vehicle", progress, x, a.y, width, f"vehicle:{a.direction}"))
    width = BOTTOM_PEDESTRIAN_WAIT_Y - TOP_PEDESTRIAN_WAIT_Y
    for i, a in enumerate(pedestrians):
        progress = ((a.y-TOP_PEDESTRIAN_WAIT_Y) if a.direction > 0 else (BOTTOM_PEDESTRIAN_WAIT_Y-a.y)) / width
        # At the exact curb the legacy agent is still waiting, not committed.
        if progress == 0:
            progress = -1e-9
        rows.append(GateObservation(f"p{i}", "pedestrian", progress, a.x, a.y, width, f"pedestrian:{a.direction}"))
    return rows


class NativeGateAdapter:
    """Derive native gate spans from actual generated junction/crossing geometry.

    The route is restricted to straight WE/EW vehicles and WC-CN pedestrians.
    Native pedestrian gate direction is inferred only from an observed approach,
    never from a first sample already on a crossing. Walking area proximity
    maps to approach; a consecutive observed crossing exit maps to exit.
    """
    def __init__(self, network: Path):
        root = ET.parse(network).getroot()
        junction = root.find("junction[@id='C']")
        if junction is None:
            raise ValueError("Missing C junction")
        points = [tuple(map(float, p.split(",")[:2])) for p in junction.attrib["shape"].split()]
        self.left, self.right = min(x for x,y in points), max(x for x,y in points)
        if self.right <= self.left:
            raise ValueError("Invalid junction span")
        self.crossings = {}
        for edge in root.findall("edge[@function='crossing']"):
            lane = edge.find("lane")
            points = [tuple(map(float, p.split(",")[:2])) for p in lane.attrib["shape"].split()]
            a,b = points[0],points[-1]
            span = math.dist(a,b)
            if span <= 0:
                raise ValueError("Invalid crossing span")
            self.crossings[edge.attrib["id"]] = (a,b,span)
        if not self.crossings:
            raise ValueError("Missing crossings")
        self.previous = {}
        self.visits = {}

    def observations(self, agents):
        rows = []
        current = {a.id:a for a in agents}
        for a in agents:
            if a.kind == "vehicle":
                # Fixture route alternates WE/EW by numeric vehicle id.
                east = int(a.engine_id[1:]) % 2 == 0
                span = self.right-self.left
                progress = ((a.x_m-self.left) if east else (self.right-a.x_m))/span
                rows.append(GateObservation(a.id,"vehicle",progress,a.x_m,a.y_m,span,"vehicle:east" if east else "vehicle:west"))
                continue
            old = self.previous.get(a.id)
            point = (a.x_m,a.y_m)
            if a.road_id in self.crossings:
                a0,b0,span = self.crossings[a.road_id]
                prior = self.visits.get(a.id)
                if prior is None or prior[0] != a.road_id:
                    # Without an observed approach we do not infer a complete visit.
                    if old is None:
                        continue
                    reverse = math.dist((old.x_m,old.y_m),b0) < math.dist((old.x_m,old.y_m),a0)
                    prior = (a.road_id, reverse)
                    self.visits[a.id] = prior
                start,end = (b0,a0) if prior[1] else (a0,b0)
                progress = ((point[0]-start[0])*(end[0]-start[0])+(point[1]-start[1])*(end[1]-start[1]))/span**2
                progress = max(0.,min(.999999,progress))
                gate = prior[0]+str(prior[1])
            elif old is not None and old.road_id in self.crossings and a.id in self.visits:
                edge,reverse = self.visits.pop(a.id)
                a0,b0,span = self.crossings[edge]
                end = a0 if reverse else b0
                if math.dist(point,end) > span*.25:
                    continue
                progress,gate = 1.,edge+str(reverse)
            else:
                # Choose the nearest real curb, within one quarter crossing span.
                options = [(math.dist(point,endpoint)/span, edge, reverse, span)
                           for edge,(a0,b0,span) in self.crossings.items()
                           for reverse,endpoint in ((False,a0),(True,b0))]
                dist,edge,reverse,span = min(options)
                if dist > .25:
                    continue
                progress,gate = -max(dist,1e-9),edge+str(reverse)
            rows.append(GateObservation(a.id,"pedestrian",progress,a.x_m,a.y_m,span,gate))
        self.previous = current
        self.visits = {i:v for i,v in self.visits.items() if i in current}
        return rows
