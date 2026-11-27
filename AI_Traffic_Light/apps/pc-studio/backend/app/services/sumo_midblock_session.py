"""Recirculating native midblock session using the existing private child/adapter.
Each slot has exactly one offered visit; only observed native arrivals permit reentry.
"""
from __future__ import annotations

from dataclasses import asdict, replace
from importlib.metadata import version
import math
import os
from pathlib import Path
import random
from tempfile import TemporaryDirectory

from app.services.sumo_shadow_adapter import ShadowAgent, STEP_S
from app.services.sumo_shadow_fixture import PHASES, PIN, native_netconvert
from app.services.sumo_shadow_process import LibsumoSession
from app.services.sumo_midblock_fixture import generate_midblock, load_midblock_map, load_slots, occupancy, crossing_bounds
from app.services.simulation_finite_fixture import load_trips


class CyclicLedger:
    """Policy-dependent journey timing, policy-independent slot/reentry stream."""
    def __init__(self, slots):
        self.slots={x.ident:x for x in slots}
        if len(self.slots)!=len(slots) or not slots:
            raise ValueError("Invalid cyclic slots")
        self.visits={s.ident:0 for s in slots}
        self.current={s.ident:s.ident+"_0" for s in slots}
        self.offered={s.ident+"_0":s.depart_s for s in slots}
        self.seen=set()
        self.arrived=set()

    def slot(self, ident):
        return self.slots[ident.rsplit("_",1)[0]]

    def reconcile(self,active,arrived,now):
        active=set(active); arrivals=set(arrived)
        current=set(self.current.values())
        if not active.isdisjoint(arrivals) or not (active|arrivals)<=current:
            raise RuntimeError("Invalid cyclic visit identity")
        if (self.seen & current)-active-arrivals:
            raise RuntimeError("Unconfirmed cyclic disappearance")
        if not arrivals<=self.seen:
            raise RuntimeError("Unobserved cyclic arrival")
        if any(self.offered[i]>now+1e-6 for i in active):
            raise RuntimeError("Premature cyclic insertion")
        self.seen.update(active)
        self.arrived.update(arrivals)
        offered=[]
        for ident in sorted(arrivals):
            slot=self.slot(ident)
            visit=self.visits[slot.ident]+1
            self.visits[slot.ident]=visit
            next_id=f"{slot.ident}_{visit}"
            # Draw keyed by slot and visit, never another slot's arrival order.
            delay_ticks=random.Random(slot.reentry_seed+visit).randint(5,15)
            depart=round(now+delay_ticks*STEP_S,6)
            self.current[slot.ident]=next_id
            self.offered[next_id]=depart
            offered.append((next_id,depart))
        return offered


def _midblock_worker(pipe, root, seed):
    engine=None
    started=False
    try:
        for name in ("libsumo","traci","sumolib","sumo-data"):
            if version(name)!=PIN:
                raise RuntimeError("Unexpected midblock dependency version")
        root=Path(root)
        mapping=load_midblock_map(root/"network.xml")
        bounds=crossing_bounds(root/"network.xml",mapping)
        ledger=CyclicLedger(load_slots(root))
        os.environ["SUMO_HOME"]=str(native_netconvert().parent.parent)
        import libsumo as engine
        engine.start(["sumo","-n",str(root/"network.xml"),"-r",str(root/"routes.xml"),
                      "--seed",str(seed),"--step-length",str(STEP_S),"--time-to-teleport","-1",
                      "--no-step-log","true","--route-steps","0"])
        started=True
        if engine.getVersion()[1].split()[-1]!=PIN or tuple(engine.trafficlight.getIDList())!=("C",):
            raise RuntimeError("Unexpected native midblock engine")
        links=engine.trafficlight.getControlledLinks("C")
        if len(links)!=len(mapping.links) or any(len(g)!=1 or tuple(g[0][:2])!=e[:2] for g,e in zip(links,mapping.links)):
            raise RuntimeError("Midblock link readback mismatch")
        def insert(ident,depart):
            slot=ledger.slot(ident)
            if slot.kind=="vehicle":
                engine.vehicle.add(ident,"_".join(slot.route),typeID="slot_"+slot.ident,depart="now",departLane="1")
            else:
                reverse=slot.route==("CS","NC")
                depart_pos=engine.lane.getLength("CS_0")-.5 if reverse else .5
                arrival_pos=.5 if reverse else engine.lane.getLength("CS_0")-.5
                engine.person.add(ident,slot.route[0],depart_pos,depart=depart,typeID=slot.type_id)
                engine.person.appendWalkingStage(ident,list(slot.route),arrival_pos,speed=slot.speed)
        engine.trafficlight.setRedYellowGreenState("C","r"*len(links))
        submitted=set()
        tick=0
        rows=()
        pipe.send(("ok",None))
        while True:
            command=pipe.recv()
            if command=="close":
                break
            if not isinstance(command,tuple) or len(command)!=2 or command[0]!="step" or command[1] not in PHASES:
                raise ValueError("Invalid cyclic step")
            v,p=occupancy(rows,mapping,bounds)
            state=mapping.state(command[1],vehicle_inside=v,pedestrian_inside=p)
            engine.trafficlight.setRedYellowGreenState("C",state)
            if engine.trafficlight.getRedYellowGreenState("C")!=state:
                raise RuntimeError("Midblock permission readback mismatch")
            # Submit only due visits. Native insertion may wait for a safe gap;
            # no moveTo, teleport, forced insertion or premature duplicate.
            now=round(tick*STEP_S,6)
            for ident in sorted(ledger.current.values()):
                if ident not in submitted and ledger.offered[ident]<=now+1e-9:
                    insert(ident,now)
                    submitted.add(ident)
            engine.simulationStep()
            if engine.simulation.getCollidingVehiclesIDList() or engine.simulation.getStartingTeleportIDList() or engine.simulation.getEndingTeleportIDList():
                raise RuntimeError("Native collision or teleport in protected midblock")
            tick+=1
            now=round(tick*STEP_S,6)
            if abs(engine.simulation.getTime()-now)>1e-6 or engine.trafficlight.getRedYellowGreenState("C")!=state:
                raise RuntimeError("Midblock clock or permission mismatch")
            result=[]
            for kind,domain in (("vehicle",engine.vehicle),("pedestrian",engine.person)):
                for ident in domain.getIDList():
                    x,y=domain.getPosition(ident)
                    result.append(ShadowAgent(kind,ident,x,y,domain.getSpeed(ident),domain.getRoadID(ident)))
            rows=tuple(result)
            occupancy(rows,mapping,bounds)
            arrived=tuple(engine.simulation.getArrivedIDList())
            persons=tuple(engine.simulation.getArrivedPersonIDList())
            new=ledger.reconcile((a.engine_id for a in rows),arrived+persons,now)
            submitted.difference_update(arrived+persons)
            pipe.send(("ok",(rows,arrived,persons,state,new)))
    except EOFError:
        pass
    except Exception as exc:
        try:
            pipe.send(("error",f"{type(exc).__name__}: {str(exc)[:300]}"))
        except (OSError,EOFError):
            pass
    finally:
        try:
            if started:
                engine.close()
        finally:
            pipe.close()


class CyclicMidblockSession(LibsumoSession):
    def __init__(self,seed,*,density,lean_worker=True):
        self._temp=TemporaryDirectory(prefix="mesh-midblock-")
        root=Path(self._temp.name)
        try:
            self.phase_map=generate_midblock(root,seed,density)
            self.bounds=crossing_bounds(root/"network.xml",self.phase_map)
            self.slots=load_slots(root)
            self.ledger=CyclicLedger(self.slots)
            # Parse exactly the declared first routes from actual network geometry.
            import xml.etree.ElementTree as ET
            demand=ET.parse(root/"routes.xml")
            for slot in self.slots:
                attrs={"id":slot.ident+"_0","depart":str(slot.depart_s)}
                if slot.kind=="vehicle":
                    ET.SubElement(demand.getroot(),"vehicle",**attrs,type="slot_"+slot.ident,route="_".join(slot.route))
                else:
                    person=ET.SubElement(demand.getroot(),"person",**attrs)
                    person.set("departPos","-.5" if slot.route==("CS","NC") else ".5")
                    ET.SubElement(person,"walk",edges=" ".join(slot.route),speed=str(slot.speed),arrivalPos=".5" if slot.route==("CS","NC") else "-.5")
            demand.write(root/"first_visits.xml",encoding="utf-8",xml_declaration=True)
            first=load_trips(root/"network.xml",root/"first_visits.xml",midblock=True)
            self._templates={t.ident.rsplit("_",1)[0]:replace(t,desired_speed=self.ledger.slot(t.ident).speed) for t in first}
            self._trips={t.ident:replace(t,desired_speed=self.ledger.slot(t.ident).speed) for t in first}
            self.tick=0
            self._seen_gate=set()
            self._last_road={}
            self._last_route_index={}
            self._exited_gate=set()
            self.closed=False
            if lean_worker:
                from app.services.sumo_midblock_transport import launch_midblock
                super().__init__(root,seed,controlled=True,_launcher=launch_midblock)
            else:
                super().__init__(root,seed,controlled=True,_target=_midblock_worker)
        except BaseException:
            self._temp.cleanup()
            raise

    @property
    def network_path(self):
        return Path(self._temp.name)/"network.xml"

    @property
    def trips(self):
        return tuple(self._trips.values())

    @property
    def demand_manifest(self):
        return [asdict(s) for s in self.slots]

    def occupied(self,agents):
        return occupancy(agents,self.phase_map,self.bounds)

    def agents(self):
        if self.closed:
            raise RuntimeError("Cyclic session closed")
        return super().agents()

    def set_phase(self,phase):
        if self.closed:
            raise RuntimeError("Cyclic session closed")
        super().set_phase(phase)

    def advance(self):
        if self.closed:
            raise RuntimeError("Cyclic session closed")
        try:
            self._pipe.send(("step",self._phase))
            rows,arrived,persons,permission,new=self._receive()
            self.tick+=1
            now=round(self.tick*STEP_S,6)
            previous_vehicle,previous_pedestrian=self.occupied(self._agents)
            expected_permission=self.phase_map.state(self._phase,vehicle_inside=previous_vehicle,pedestrian_inside=previous_pedestrian)
            if permission!=expected_permission:
                raise RuntimeError("Midblock parent/child permission mismatch")
            for agent in rows:
                trip=self._trips.get(agent.engine_id)
                if trip is None or agent.kind!=trip.kind or agent.road_id not in {s.road_id for s in trip.path}:
                    raise RuntimeError("Midblock agent outside validated route")
                ident=agent.engine_id
                index=next(i for i,s in enumerate(trip.path) if s.road_id==agent.road_id)
                prior=self._last_route_index.get(ident)
                gate=next(i for i,s in enumerate(trip.path) if s.kind==agent.kind+"_gate")
                if prior is None and index!=0 or prior is not None and index<prior:
                    raise RuntimeError("Cyclic journey started mid-route or moved backwards")
                if index==gate and prior!=gate:
                    group=self.phase_map.vehicles if agent.kind=="vehicle" else self.phase_map.pedestrians
                    if prior is None or prior>=gate or not any(permission[i]=="G" for i in group):
                        raise RuntimeError("Midblock entry without applied permission")
                    self._seen_gate.add(ident)
                if index>gate:
                    if ident not in self._seen_gate:
                        raise RuntimeError("Cyclic journey skipped protected crossing")
                    self._exited_gate.add(ident)
                self._last_route_index[ident]=index
                self._last_road[ident]=agent.road_id
            if any(i not in self._exited_gate or self._trips[i].kind!="vehicle" for i in arrived) or any(
                i not in self._exited_gate or self._trips[i].kind!="pedestrian" for i in persons):
                raise RuntimeError("Arrival without observed protected gate exit")
            for ident in tuple(arrived)+tuple(persons):
                self._seen_gate.discard(ident)
                self._exited_gate.discard(ident)
                self._last_route_index.pop(ident,None)
                self._last_road.pop(ident,None)
            expected=self.ledger.reconcile((a.engine_id for a in rows),tuple(arrived)+tuple(persons),now)
            if list(new)!=expected:
                raise RuntimeError("Cyclic demand readback mismatch")
            self.occupied(rows)
            for ident,depart in expected:
                slot=self.ledger.slot(ident)
                self._trips[ident]=replace(self._templates[slot.ident],ident=ident,depart_s=depart)
            self._agents=rows
            self.arrived.update(arrived)
            self.person_arrived.update(persons)
            self.last_permission=permission
        except BaseException:
            self.close()
            raise

    def close(self):
        self.closed=True
        try:
            super().close()
        finally:
            self._temp.cleanup()
