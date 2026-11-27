"""Trusted, isolated midblock topology and cyclic slot specification.
Only generated local synthetic networks; no legacy pixel calibration or hardware.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
import os
from pathlib import Path
import random
import subprocess
import xml.etree.ElementTree as ET

from app.services.legacy_world import DENSITY_COUNTS, DENSITY_SEED_OFFSETS, vehicle_specs, pedestrian_specs
from app.services.sumo_shadow_fixture import PhaseMap, native_netconvert, PIN

ROAD_EDGES = frozenset({"WC","CW","EC","CE"})
WALK_EDGES = frozenset({"NC","CN","SC","CS"})
STRAIGHT = frozenset({("WC","CE"),("EC","CW")})
LENGTHS = {"car":4.5,"suv":4.9,"van":6.0,"bus":12.0}
WIDTHS = {"car":1.8,"suv":1.95,"van":2.1,"bus":2.5}
MAX_LENGTH = max(LENGTHS.values())


@dataclass(frozen=True)
class Slot:
    ident: str
    kind: str
    route: tuple[str,str]
    type_id: str
    speed: float
    depart_s: float
    reentry_seed: int


def slots_for(seed, density):
    if type(seed) is not int or not 0<=seed<=2**31-1 or density not in DENSITY_COUNTS:
        raise ValueError("Invalid midblock seed or density")
    rng = random.Random(seed + DENSITY_SEED_OFFSETS[density])
    vehicles = list(vehicle_specs(density,rng))
    people = list(pedestrian_specs(density,rng))
    # Same seeded slot count, classes and directions, deliberately new physical
    # speeds and insertion distances (no isotropic pixel-to-metre calibration).
    slots = [Slot(f"v{i}","vehicle",("WC","CE") if v.direction>0 else ("EC","CW"),
                  v.vehicle_type,round(v.speed/11,3),float(i//2*3),rng.getrandbits(64))
             for i,v in enumerate(vehicles)]
    slots += [Slot(f"p{i}","pedestrian",("NC","CS") if v.direction>0 else ("CS","NC"),
                   "DEFAULT_PEDTYPE",.65 if i==0 else round(v.speed/75,3),float(i//2*2),rng.getrandbits(64))
              for i,v in enumerate(people)]
    return tuple(slots)


def write_midblock(root: Path, seed, density):
    slots = slots_for(seed,density)
    nodes=ET.Element("nodes")
    for ident,x,y in (("W",-150,0),("E",150,0),("N",0,20),("S",0,-20),("C",0,0)):
        ET.SubElement(nodes,"node",id=ident,x=str(x),y=str(y),type="traffic_light" if ident=="C" else "priority")
    edges=ET.Element("edges")
    for ident in sorted(ROAD_EDGES | WALK_EDGES):
        attrs={"id":ident,"from":ident[0],"to":ident[1],"numLanes":"1",
               "speed":"11" if ident in ROAD_EDGES else "1.5",
               "allow":"passenger" if ident in ROAD_EDGES else "pedestrian",
               "width":"3.5" if ident in ROAD_EDGES else "2.5"}
        if ident in ROAD_EDGES:
            attrs.update(numLanes="2")
            attrs.pop("allow")
            attrs.pop("width")
        edge=ET.SubElement(edges,"edge",attrs)
        if ident in ROAD_EDGES:
            ET.SubElement(edge,"lane",index="0",allow="pedestrian",width="2")
            ET.SubElement(edge,"lane",index="1",allow="passenger",width="3.5")
    connections=ET.Element("connections")
    for first,last in sorted(STRAIGHT):
        ET.SubElement(connections,"connection",{"from":first,"to":last,"fromLane":"1","toLane":"1"})
    ET.SubElement(connections,"crossing",node="C",edges="WC CW",priority="true",width="4")
    routes=ET.Element("routes")
    for slot in slots:
        if slot.kind=="vehicle":
            ET.SubElement(routes,"vType",id="slot_"+slot.ident,vClass="passenger",length=str(LENGTHS[slot.type_id]),
                          width=str(WIDTHS[slot.type_id]),maxSpeed=str(slot.speed),speedFactor="1",speedDev="0",sigma="0",minGap="2.5")
    for route in (("WC","CE"),("EC","CW")):
        ET.SubElement(routes,"route",id="_".join(route),edges=" ".join(route))
    # First visits and later visits share the same dynamic insertion path.
    for name,element in (("nodes.xml",nodes),("edges.xml",edges),("connections.xml",connections),("routes.xml",routes)):
        ET.ElementTree(element).write(root/name,encoding="utf-8",xml_declaration=True)
    (root/"slots.json").write_text(json.dumps([asdict(x) for x in slots],indent=2),encoding="utf-8")
    return slots


def load_slots(root):
    raw=json.loads((root/"slots.json").read_text(encoding="utf-8"))
    return tuple(Slot(**{**x,"route":tuple(x["route"])}) for x in raw)


def load_midblock_map(path):
    net=ET.parse(path).getroot()
    external={e.get("id") for e in net.findall("edge") if e.get("function") is None}
    crossings=frozenset(e.get("id") for e in net.findall("edge[@function='crossing']"))
    if external!=(ROAD_EDGES|WALK_EDGES) or len(crossings)!=1:
        raise ValueError("Unexpected midblock topology")
    for e in net.findall("edge"):
        if e.get("id") in WALK_EDGES and any(l.get("allow")!="pedestrian" for l in e.findall("lane")):
            raise ValueError("Motor access to pedestrian approach")
        if e.get("id") in ROAD_EDGES:
            lanes=e.findall("lane")
            if len(lanes)!=2 or lanes[0].get("allow")!="pedestrian" or lanes[1].get("allow")!="passenger":
                raise ValueError("Invalid separated sidewalk/road lanes")
    links={}
    vehicles=[]
    pedestrians=[]
    for c in net.findall("connection"):
        if c.get("tl")!="C":
            continue
        index=int(c.attrib["linkIndex"])
        a,z=c.attrib["from"],c.attrib["to"]
        if index in links:
            raise ValueError("Ambiguous midblock controlled link")
        links[index]=(a+"_"+c.attrib["fromLane"],z+"_"+c.attrib["toLane"],c.get("via",""))
        if (a,z) in STRAIGHT and c.get("dir")=="s":
            vehicles.append(index)
        elif z in crossings:
            pedestrians.append(index)
        else:
            raise ValueError("Unexpected controlled movement")
    n=len(links)
    if set(links)!=set(range(n)) or len(vehicles)!=2 or not 1<=len(pedestrians)<=2:
        raise ValueError("Unexpected midblock link partition")
    foes={int(x.attrib["index"]):x.attrib["foes"][::-1] for x in net.findall("junction[@id='C']/request")}
    if set(foes)!=set(links) or any(len(x)!=n or set(x)-{"0","1"} for x in foes.values()):
        raise ValueError("Missing midblock conflict matrix")
    if any(foes[a][z]!="0" for group in (vehicles,pedestrians) for a in group for z in group if a!=z):
        raise ValueError("Conflicting same-phase movements")
    # Require the network to recognize every straight/crossing conflict.
    if any(foes[a][z]!="1" or foes[z][a]!="1" for a in vehicles for z in pedestrians):
        raise ValueError("Unprotected crossing conflict")
    return PhaseMap(tuple(links[i] for i in range(n)),tuple(sorted(vehicles)),tuple(sorted(pedestrians)),crossings)


def crossing_bounds(path,mapping):
    net=ET.parse(path).getroot()
    lane=next(e.find("lane") for e in net.findall("edge") if e.get("id") in mapping.crossing_edges)
    points=[tuple(map(float,x.split(",")[:2])) for x in lane.attrib["shape"].split()]
    if len(points)<2 or not all(math.isfinite(v) for p in points for v in p):
        raise ValueError("Invalid crossing coordinates")
    if abs(points[-1][1]-points[0][1])<=abs(points[-1][0]-points[0][0]):
        raise ValueError("Crossing not transverse to road")
    # Include the crossing surface thickness, not only its centre line.
    width=float(lane.get("width","4"))
    if not math.isfinite(width) or width<=0:
        raise ValueError("Invalid crossing width")
    return min(x for x,y in points)-width/2,max(x for x,y in points)+width/2


def occupancy(agents,mapping,bounds):
    left,right=bounds
    # Internal vehicles may be committed. Outgoing fronts near the crossing
    # remain committed until even the longest configured body is clear.
    vehicle=any(a.kind=="vehicle" and (a.road_id.startswith(":C_") or
        (a.road_id=="CE" and a.x_m<=right+MAX_LENGTH+1) or
        (a.road_id=="CW" and a.x_m>=left-MAX_LENGTH-1)) for a in agents)
    pedestrian=any(a.kind=="pedestrian" and a.road_id in mapping.crossing_edges for a in agents)
    if vehicle and pedestrian:
        raise RuntimeError("Opposing midblock occupancy")
    return vehicle,pedestrian


def generate_midblock(root,seed,density):
    write_midblock(root,seed,density)
    binary=native_netconvert()
    env={**os.environ,"SUMO_HOME":str(binary.parent.parent)}
    version=subprocess.run([str(binary),"--version"],cwd=root,env=env,capture_output=True,text=True,check=True,timeout=15)
    banner=version.stdout.splitlines()[0] if version.stdout else ""
    if banner.strip() not in (f"Eclipse SUMO netconvert {PIN}",f"Eclipse SUMO netconvert Version {PIN}"):
        raise RuntimeError("Unexpected netconvert version")
    subprocess.run([str(binary),"--node-files","nodes.xml","--edge-files","edges.xml",
                    "--connection-files","connections.xml","--no-turnarounds","true",
                    "--output-file","network.xml"],cwd=root,env=env,capture_output=True,check=True,timeout=15)
    mapping=load_midblock_map(root/"network.xml")
    crossing_bounds(root/"network.xml",mapping)
    return mapping
