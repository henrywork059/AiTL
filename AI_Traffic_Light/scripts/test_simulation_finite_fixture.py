"""Offline finite-reference admission and shared gate contract."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"apps/pc-studio/backend"))
from app.services.simulation_finite_fixture import Segment,Trip,FiniteReference,RouteGateAdapter
from app.services.simulation_gate_metrics import GateMetrics
from app.services.sumo_shadow_adapter import ShadowAgent


def path(prefix,kind,y):
    return (Segment(prefix+"a","road",((0.,y),(10.,y))),
            Segment(prefix+"g",kind+"_gate",((10.,y),(20.,y))),
            Segment(prefix+"b","road",((20.,y),(30.,y))))


class Tests(unittest.TestCase):
    def test_midblock_route_requires_exactly_one_crossing_both_directions(self):
        from app.services.simulation_finite_fixture import load_trips
        import xml.etree.ElementTree as ET
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            folder=Path(tmp)
            net=ET.Element("net")
            def edge(id,shape,kind=None,lane=0):
                e=ET.SubElement(net,"edge",{"id":id,**({"function":kind} if kind else {})})
                ET.SubElement(e,"lane",id=id+"_"+str(lane),shape=shape)
            for ident,shape in (("NC","0,20 0,8"),("CS","0,-8 0,-20"),("SC","0,-20 0,-8"),("CN","0,8 0,20")):
                edge(ident,shape)
            edge(":C_w0","0,8 0,5","walkingarea")
            edge(":C_w1","0,-5 0,-8","walkingarea")
            edge(":C_c0","0,5 0,-5","crossing")
            for a,z in (("NC",":C_w0"),(":C_w0",":C_c0"),(":C_c0",":C_w1"),(":C_w1","CS"),
                        ("SC",":C_w1"),(":C_w0","CN")):
                ET.SubElement(net,"connection",{"from":a,"to":z,"fromLane":"0","toLane":"0"})
            ET.ElementTree(net).write(folder/"network.xml")
            (folder/"routes.xml").write_text('<routes><person id="p0_0" depart="0"><walk edges="NC CS" speed=".65"/></person><person id="p1_0" depart="0"><walk edges="SC CN" speed="1.3"/></person></routes>')
            trips=load_trips(folder/"network.xml",folder/"routes.xml",midblock=True)
            self.assertEqual(len(trips),2)
            gates=[next(s for s in t.path if s.kind=="pedestrian_gate") for t in trips]
            self.assertEqual(gates[0].points,tuple(reversed(gates[1].points)))
            self.assertEqual(gates[0].road_id,gates[1].road_id)
            ET.SubElement(net,"connection",{"from":"NC","to":"CS","fromLane":"0","toLane":"0"})
            ET.ElementTree(net).write(folder/"network.xml")
            with self.assertRaises(ValueError):
                load_trips(folder/"network.xml",folder/"routes.xml",midblock=True)

    def test_cyclic_slot_ledger_and_protection(self):
        from app.services.sumo_midblock_fixture import slots_for,occupancy,write_midblock
        from app.services.sumo_midblock_session import CyclicLedger
        from app.services.sumo_shadow_fixture import PhaseMap
        from tempfile import TemporaryDirectory
        import xml.etree.ElementTree as ET
        for seed in (42,73):
            for density,nv,np in (("light",4,4),("normal",8,7),("busy",12,11)):
                slots=slots_for(seed,density)
                self.assertEqual(slots,slots_for(seed,density))
                self.assertEqual(sum(x.kind=="vehicle" for x in slots),nv)
                self.assertEqual(sum(x.kind=="pedestrian" for x in slots),np)
                self.assertEqual(sum(x.speed==.65 for x in slots if x.kind=="pedestrian"),1)
                ledger=CyclicLedger(slots)
                self.assertEqual(len(ledger.current),nv+np)
                first=tuple(ledger.current.values())
                now=max(ledger.offered.values())+1
                ledger.reconcile(first,(),now)
                a=first[0];z=first[-1]
                next_a=ledger.reconcile([i for i in first if i!=a],(a,),now+1)
                next_z=ledger.reconcile([i for i in first if i not in (a,z)],(z,),now+2)
                other=CyclicLedger(slots)
                other.reconcile(first,(),now)
                reverse_z=other.reconcile([i for i in first if i!=z],(z,),now+1)
                reverse_a=other.reconcile([i for i in first if i not in (a,z)],(a,),now+2)
                self.assertEqual(next_a[0][0],reverse_a[0][0])
                self.assertAlmostEqual(next_a[0][1]-(now+1),reverse_a[0][1]-(now+2))
                self.assertAlmostEqual(next_z[0][1]-(now+2),reverse_z[0][1]-(now+1))
                self.assertEqual(len(ledger.current),nv+np)
                self.assertEqual(len(ledger.arrived),2)
                self.assertEqual(len(ledger.offered),nv+np+2)
                with self.assertRaises(RuntimeError):
                    ledger.reconcile([],(),now+3)
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            write_midblock(root,42,"normal")
            net=ET.parse(root/"edges.xml").getroot()
            self.assertEqual(len(net.findall("edge")),8)
            for e in net.findall("edge"):
                if e.get("id") in {"NC","CN","SC","CS"}:
                    self.assertEqual(e.get("allow"),"pedestrian")
                else:
                    self.assertEqual(e.find("lane[@index='0']").get("allow"),"pedestrian")
                    self.assertEqual(e.find("lane[@index='1']").get("allow"),"passenger")
            self.assertEqual(len(ET.parse(root/"connections.xml").getroot().findall("crossing")),1)
        mapping=PhaseMap((("a","b",""),("c","d","")),(0,),(1,),frozenset({":C_c0"}))
        car=ShadowAgent("vehicle","v0_0",8.,0.,2.,"CE")
        walker=ShadowAgent("pedestrian","p0_0",0.,0.,.65,":C_c0")
        self.assertEqual(occupancy((car,),mapping,(-1.,1.)),(True,False))
        self.assertEqual(mapping.state("pedestrian_green",vehicle_inside=True,pedestrian_inside=False),"rr")
        with self.assertRaises(RuntimeError):
            occupancy((car,walker),mapping,(-1.,1.))
        self.assertEqual(occupancy((ShadowAgent("vehicle","v0_0",15.,0.,2.,"CE"),walker),mapping,(-1.,1.)),(False,True))

    def test_reference_session_lifecycle(self):
        from app.services.simulation_reference_session import FiniteReferenceSession
        from app.services.sumo_shadow_fixture import PhaseMap
        vpath=(Segment("v_in","road",((0.,0.),(10.,0.))),
               Segment(":C_0","vehicle_gate",((10.,0.),(20.,0.))),
               Segment("v_out","road",((20.,0.),(30.,0.))))
        ppath=(Segment("p_in","walk",((0.,1.),(10.,1.))),
               Segment(":C_c0","pedestrian_gate",((10.,1.),(20.,1.))),
               Segment("p_out","walk",((20.,1.),(30.,1.))))
        trips=(Trip("v0","vehicle",0.,5.,vpath),Trip("p0","pedestrian",0.,2.,ppath))
        mapping=PhaseMap((("a","b",""),("c","d","")),(0,),(1,),frozenset({":C_c0"}))
        def run():
            session=FiniteReferenceSession(Path("fixture.xml"),trips,mapping)
            trace=[]
            stationary=False
            for tick in range(200):
                phase="all_red" if tick<30 else "vehicle_green" if tick<41 else "pedestrian_green"
                session.set_phase(phase)
                before=session.agents()
                session.advance()
                rows=session.agents()
                self.assertEqual(session.last_permission,mapping.state(phase,
                    vehicle_inside=any(a.road_id==":C_0" for a in before),
                    pedestrian_inside=any(a.road_id==":C_c0" for a in before)))
                self.assertFalse({":C_0",":C_c0"} <= {a.road_id for a in rows})
                self.assertTrue(all(a.id.startswith("reference:") and a.speed_m_s>=0 for a in rows))
                stationary=stationary or any(a.speed_m_s==0 for a in rows)
                trace.append((session.last_permission,rows))
            self.assertTrue(stationary)
            self.assertEqual(session.arrived,{"v0"})
            self.assertEqual(session.person_arrived,{"p0"})
            session.close()
            with self.assertRaises(RuntimeError): session.advance()
            with self.assertRaises(RuntimeError): session.agents()
            with self.assertRaises(ValueError): session.set_phase("vehicle_green")
            return trace
        self.assertEqual(run(),run())

    def test_finite_protected_schedule(self):
        trips=(Trip("v0","vehicle",0.,5.,path("v","vehicle",0.)),
               Trip("p0","pedestrian",0.,2.,path("p","pedestrian",1.)))
        reference=FiniteReference(trips)
        adapter=RouteGateAdapter(trips)
        metrics=GateMetrics()
        for tick in range(1,201):
            phase="vehicle_green" if tick<20 else "pedestrian_green" if tick<150 else "all_red"
            agents=reference.advance(phase)
            roads={a.road_id for a in agents}
            self.assertFalse("vg" in roads and "pg" in roads)
            metrics.sample(tick,adapter.observations(agents))
        self.assertEqual(reference.arrived,{"v0","p0"})
        self.assertEqual(metrics.summary()["vehicle_passages"],1)
        self.assertEqual(metrics.summary()["pedestrian_crossings"],1)
        self.assertFalse(adapter.unknown_roads)
        self.assertFalse(reference.advance("all_red"))

    def test_reverse_branch_entry_and_exit(self):
        start=Segment("approach","walk",((0.,0.),(1.,0.)))
        forward=(start,Segment("south","pedestrian_gate",((1.,0.),(1.,2.))),
                 Segment("end","walk",((1.,2.),(2.,2.))))
        reverse=(start,Segment("west","pedestrian_gate",((1.,0.),(3.,0.))),
                 Segment("end","walk",((3.,0.),(4.,0.))))
        trip=Trip("p0","pedestrian",0.,1.,forward,(reverse,))
        adapter=RouteGateAdapter((trip,))
        metrics=GateMetrics()
        trace=[("approach",.9,0.),("west",1.1,0.),("west",1.9,0.),
               ("west",2.7,0.),("end",3.1,0.)]
        for tick,(road,x,y) in enumerate(trace,1):
            metrics.sample(tick,adapter.observations((ShadowAgent("pedestrian","p0",x,y,1.,road),)))
        self.assertEqual(metrics.summary()["pedestrian_crossings"],1)
        self.assertFalse(adapter.unknown_roads)
        self.assertEqual(adapter.seen_roads["p0"],["approach","west","end"])

    def test_missing_entry_is_not_completion(self):
        trip=Trip("p0","pedestrian",0.,1.,path("p","pedestrian",0.))
        adapter=RouteGateAdapter((trip,))
        metrics=GateMetrics()
        for tick,(road,x) in enumerate((("pg",19.),("pb",20.1)),1):
            metrics.sample(tick,adapter.observations((ShadowAgent("pedestrian","p0",x,0.,1.,road),)))
        self.assertEqual(metrics.summary()["pedestrian_crossings"],0)

    def test_waiting_finite(self):
        trip=Trip("v0","vehicle",0.,5.,path("v","vehicle",0.))
        reference=FiniteReference((trip,))
        for _ in range(30):
            rows=reference.advance("vehicle_yellow")
            self.assertTrue(all(a.road_id=="va" for a in rows))
        self.assertFalse(reference.arrived)
        with self.assertRaises(ValueError):
            reference.advance("invalid")


if __name__=="__main__":
    unittest.main()
