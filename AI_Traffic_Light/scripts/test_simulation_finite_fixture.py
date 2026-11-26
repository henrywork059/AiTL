"""Offline finite-reference admission and shared gate contract."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"apps/pc-studio/backend"))
from app.services.simulation_finite_fixture import Segment,Trip,FiniteReference,RouteGateAdapter
from app.services.simulation_gate_metrics import GateMetrics


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
