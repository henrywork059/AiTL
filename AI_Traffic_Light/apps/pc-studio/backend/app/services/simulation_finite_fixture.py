"""Finite, generated-network evaluation fixture; never a production simulator.

Vehicle paths use the actual straight lane and internal connection polylines.
Pedestrian sidewalk/crossing polylines are exact; walking-area interiors are
endpoint chords, not SUMO's pedestrian dynamics. Only the trusted WC/CN
fixture and straight WE/EW routes are supported.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from app.services.sumo_shadow_adapter import ShadowAgent
from app.services.sumo_shadow_fixture import PHASES
from app.services.simulation_gate_metrics import GateObservation, STEP_S


@dataclass(frozen=True)
class Segment:
    road_id: str
    kind: str
    points: tuple[tuple[float, float], ...]

    @property
    def length(self):
        return sum(math.dist(a, b) for a, b in zip(self.points, self.points[1:]))

    def point(self, distance):
        distance = max(0., min(self.length, distance))
        for a, b in zip(self.points, self.points[1:]):
            length = math.dist(a, b)
            if length > 0 and distance <= length:
                f = distance / length
                return (a[0] + f*(b[0]-a[0]), a[1] + f*(b[1]-a[1]))
            distance -= length
        return self.points[-1]


@dataclass(frozen=True)
class Trip:
    ident: str
    kind: str
    depart_s: float
    desired_speed: float
    path: tuple[Segment, ...]
    alternatives: tuple[tuple[Segment, ...], ...] = ()

    @property
    def length(self):
        return sum(s.length for s in self.path)

    def locate(self, distance):
        for i, segment in enumerate(self.path):
            if distance < segment.length or i == len(self.path)-1:
                return i, distance, segment.point(distance)
            distance -= segment.length
        raise AssertionError("Empty path")


def load_trips(network: Path, routes: Path, *, midblock=False) -> tuple[Trip, ...]:
    net = ET.parse(network).getroot()
    demand = ET.parse(routes).getroot()
    edges = {e.attrib["id"]:e for e in net.findall("edge")}
    lanes = {l.attrib["id"]:(e.attrib["id"],l) for e in edges.values() for l in e.findall("lane")}

    def lane_segment(lane_id, kind):
        edge, lane = lanes[lane_id]
        points = tuple(tuple(map(float, x.split(",")[:2])) for x in lane.attrib["shape"].split())
        seg = Segment(edge, kind, points)
        if len(points) < 2 or seg.length <= 0 or not all(math.isfinite(v) for pt in points for v in pt):
            raise ValueError("Invalid lane geometry")
        return seg

    def vehicle_path(first, last):
        links = [c for c in net.findall("connection") if c.get("from")==first and c.get("to")==last and c.get("dir")=="s"]
        if len(links)!=1:
            raise ValueError("Expected a single straight connection")
        c=links[0]
        return (lane_segment(first+"_"+c.attrib["fromLane"],"road"),
                lane_segment(c.attrib["via"],"vehicle_gate"),
                lane_segment(last+"_"+c.attrib["toLane"],"road"))

    # SUMO pedestrian lanes can be traversed in both directions between
    # walking areas. External route edges retain their declared direction.
    graph = {}
    internal = {"walkingarea","crossing"}
    for c in net.findall("connection"):
        a,b=c.attrib["from"],c.attrib["to"]
        if c.get("fromLane")=="0" and c.get("toLane")=="0":
            graph.setdefault(a,set()).add(b)
            if edges[a].get("function") in internal and edges[b].get("function") in internal:
                graph.setdefault(b,set()).add(a)

    def pedestrian_paths(first,last):
        pending=[(first,)]
        found=[]
        while pending:
            path=pending.pop(0)
            if path[-1]==last:
                found.append(path)
                continue
            for nxt in sorted(graph.get(path[-1],())):
                if nxt in path:
                    continue
                if nxt!=last and edges[nxt].get("function") not in internal:
                    continue
                pending.append(path+(nxt,))
        paths=[]
        for route in found:
            crossing_count=sum(edges[e].get("function")=="crossing" for e in route)
            if midblock and crossing_count!=1:
                raise ValueError("Midblock pedestrian bypass or multiple crossings")
            if not midblock and crossing_count!=2:
                continue
            segments={}
            for i,e in enumerate(route):
                kind=edges[e].get("function")
                if kind=="walkingarea":
                    continue
                seg=lane_segment(e+"_0","pedestrian_gate" if kind=="crossing" else "walk")
                if kind=="crossing":
                    # The original directed connection indicates the lane's
                    # forward direction; reverse pedestrian travel is valid.
                    forward=any(c.get("from")==route[i-1] and c.get("to")==e and
                                c.get("fromLane")=="0" and c.get("toLane")=="0"
                                for c in net.findall("connection"))
                    if not forward:
                        seg=Segment(e,seg.kind,tuple(reversed(seg.points)))
                segments[i]=seg
            for i,e in enumerate(route):
                if edges[e].get("function")=="walkingarea":
                    seg=Segment(e,"walk",(segments[i-1].points[-1],segments[i+1].points[0]))
                    if seg.length<=0:
                        raise ValueError("Degenerate walking area chord")
                    segments[i]=seg
            paths.append(tuple(segments[i] for i in range(len(route))))
        if len(paths)!=(1 if midblock else 2):
            raise ValueError("Unexpected pedestrian route alternatives")
        # Deterministic reference chooses shortest chord path, ties by road IDs.
        return tuple(sorted(paths,key=lambda path:(sum(s.length for s in path),tuple(s.road_id for s in path))))

    declared_routes={n.attrib["id"]:tuple(n.attrib["edges"].split()) for n in demand.findall("route")}
    trips=[]
    for v in demand.findall("vehicle"):
        path=declared_routes[v.attrib["route"]]
        if path not in (("WC","CE"),("EC","CW")):
            raise ValueError("Unsupported vehicle route")
        trips.append(Trip(v.attrib["id"],"vehicle",float(v.attrib["depart"]),10.,vehicle_path(*path)))
    for person in demand.findall("person"):
        walk=person.find("walk")
        path=tuple(walk.attrib["edges"].split())
        allowed=(("NC","CS"),("SC","CN")) if midblock else (("WC","CN"),)
        if path not in allowed:
            raise ValueError("Unsupported walking route")
        options=pedestrian_paths(*path)
        trips.append(Trip(person.attrib["id"],"pedestrian",float(person.attrib["depart"]),float(walk.attrib["speed"]),options[0],options[1:]))
    if not trips or len({t.ident for t in trips})!=len(trips) or any(
        not math.isfinite(t.depart_s) or t.depart_s<0 or not math.isfinite(t.desired_speed) or t.desired_speed<=0 for t in trips):
        raise ValueError("Invalid finite demand")
    return tuple(sorted(trips,key=lambda t:(t.depart_s,t.ident)))


class RouteGateAdapter:
    """Observe either declared route; never infer an unobserved crossing.

    Before a branch is resolved, choose the nearest permitted next entry
    for queue measurement only. Actual adjacent road transitions establish
    gate entry and exit, including reverse-direction crossing lanes.
    """
    def __init__(self,trips):
        self.trips={t.ident:t for t in trips}
        self.previous={}
        self.candidates={}
        self.seen_roads={}
        self.unknown_roads=set()

    def observations(self,agents):
        rows=[]
        current={}
        for a in agents:
            trip=self.trips[a.engine_id]
            if a.kind!=trip.kind:
                raise ValueError("Trip kind mismatch")
            old=self.previous.get(a.engine_id)
            point=(a.x_m,a.y_m)
            options=self.candidates.get(a.engine_id,(trip.path,*trip.alternatives))
            valid=[path for path in options if sum(s.road_id==a.road_id for s in path)==1]
            if not valid:
                self.unknown_roads.add((a.engine_id,a.road_id))
                continue
            self.candidates[a.engine_id]=tuple(valid)
            current[a.engine_id]=a
            seen=self.seen_roads.setdefault(a.engine_id,[])
            if not seen or seen[-1]!=a.road_id:
                seen.append(a.road_id)
            choices=[]
            for path in valid:
                index=next(i for i,s in enumerate(path) if s.road_id==a.road_id)
                gates=[i for i,s in enumerate(path) if s.kind==a.kind+"_gate"]
                prev=next((i for i,s in enumerate(path) if old is not None and s.road_id==old.road_id),None)
                exited=prev if prev in gates and index==prev+1 else None
                gate_index=exited if exited is not None else next((i for i in gates if i>=index),None)
                if gate_index is None:
                    continue
                gate=path[gate_index]
                first,last=gate.points[0],gate.points[-1]
                span=gate.length
                entry=(index==gate_index and prev==index-1 and a.kind=="pedestrian")
                if index<gate_index:
                    progress=-max(math.dist(point,first)/span,1e-9)
                elif index==gate_index:
                    chord=math.dist(first,last)
                    if chord<=0:
                        raise ValueError("Degenerate gate")
                    progress=((point[0]-first[0])*(last[0]-first[0])+(point[1]-first[1])*(last[1]-first[1]))/chord**2
                    progress=max(0.,min(.999999,progress))
                else:
                    progress=1.
                row=GateObservation(a.id,a.kind,progress,a.x_m,a.y_m,span,gate.road_id,entry_observed=entry)
                # Actual occupied/exited gates outrank unresolved approach choices.
                choices.append((0 if index>=gate_index else 1,math.dist(point,first),gate.road_id,row))
            if choices:
                rows.append(min(choices,key=lambda c:c[:3])[-1])
        self.previous=current
        return rows


class FiniteReference:
    """Legacy-style constant-speed/gap/stop-line evaluation reference.

    Not CameraFrameService. Vehicle front-position insertion at 5 m and
    following gap 7.5 m are explicit assumptions; pedestrian interactions
    and acceleration are not modeled. Every trip is finite. No phase owner.
    """
    def __init__(self,trips):
        self.trips=tuple(trips)
        self.pending=list(trips)
        self.active={}
        self.arrived=set()
        self.tick=0

    def advance(self,phase):
        if phase not in PHASES:
            raise ValueError("Unknown protected phase")
        now=self.tick*STEP_S
        for trip in list(self.pending):
            if trip.depart_s>now+1e-9:
                continue
            initial=5. if trip.kind=="vehicle" else 0.
            if trip.kind=="vehicle" and any(
                other.path==trip.path and pos-initial<7.5 for other,pos in self.active.values()):
                continue
            self.active[trip.ident]=(trip,initial)
            self.pending.remove(trip)
        occupied={trip.path[trip.locate(pos)[0]].kind for trip,pos in self.active.values()}
        grants={"vehicle":phase=="vehicle_green" and "pedestrian_gate" not in occupied,
                "pedestrian":phase=="pedestrian_green" and "vehicle_gate" not in occupied}
        assert not all(grants.values())
        leaders={}
        for ident,(trip,pos) in sorted(self.active.items(),key=lambda item:-item[1][1]):
            next_pos=min(pos+trip.desired_speed*STEP_S,trip.length)
            offset=0.
            for segment in trip.path:
                if segment.kind==trip.kind+"_gate" and pos<offset<=next_pos and not grants[trip.kind]:
                    next_pos=min(next_pos,max(pos,offset-.001))
                    break
                offset+=segment.length
            if trip.kind=="vehicle":
                if trip.path in leaders:
                    next_pos=max(pos,min(next_pos,leaders[trip.path]-7.5))
                leaders[trip.path]=next_pos
            self.active[ident]=(trip,next_pos)
        for ident,(trip,pos) in list(self.active.items()):
            if pos>=trip.length:
                self.arrived.add(ident)
                del self.active[ident]
        self.tick+=1
        rows=[]
        for ident,(trip,pos) in self.active.items():
            index,_,point=trip.locate(pos)
            rows.append(ShadowAgent(trip.kind,ident,*point,trip.desired_speed,trip.path[index].road_id))
        return tuple(rows)
