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
