"""Known normalized geometry trace; both event types, queues and censoring."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"apps/pc-studio/backend"))
from app.services.simulation_gate_metrics import GateMetrics,GateObservation


def obs(i,k,p,x=None,gate="g"):
    return GateObservation(i,k,p,p if x is None else x,0,1,gate)


class Tests(unittest.TestCase):
    def test_same_geometry_and_events(self):
        m=GateMetrics()
        m.sample(1,[obs("v","vehicle",-.1),obs("p","pedestrian",-.1)])
        row=m.sample(2,[obs("v","vehicle",-.1),obs("p","pedestrian",-.1)])
        self.assertEqual((row["vehicle_queue"],row["pedestrian_queue"]),(1,1))
        m.sample(3,[obs("v","vehicle",.1),obs("p","pedestrian",.1)])
        row=m.sample(4,[obs("v","vehicle",.5),obs("p","pedestrian",.5)])
        self.assertEqual(row["vehicle_passages"],1)
        row=m.sample(5,[obs("v","vehicle",.8),obs("p","pedestrian",1.)])
        self.assertEqual(row["pedestrian_crossings"],1)
        m.sample(6,[])
        self.assertEqual(m.summary()["vehicle_wait_agent_s"],.2)
        self.assertEqual(m.summary()["pedestrian_wait_agent_s"],.2)
        self.assertEqual(m.summary()["censored_pedestrian_visits"],0)

    def test_wait_episodes_complete_censor_and_match_integral(self):
        m=GateMetrics()
        m.sample(1,[obs("v","vehicle",-.2),obs("p","pedestrian",-.2)])
        m.sample(2,[obs("v","vehicle",-.2),obs("p","pedestrian",-.2)])
        m.sample(3,[obs("v","vehicle",-.2),obs("p","pedestrian",-.1)])
        m.sample(4,[obs("p","pedestrian",-.1)])
        waits=m.waiting_episodes()
        self.assertEqual(waits["vehicle"]["censored_observed_seconds"],[.4])
        self.assertEqual(waits["pedestrian"]["completed_seconds"],[.2])
        self.assertEqual(waits["pedestrian"]["censored_observed_seconds"],[.2])
        for kind in waits:
            self.assertEqual(waits[kind]["observed_agent_seconds"],m.summary()[kind+"_wait_agent_s"])
        self.assertEqual(m.waiting_episodes(),waits)

    def test_disappearance_and_reset_are_not_crossings(self):
        m=GateMetrics()
        m.sample(1,[obs("p","pedestrian",-.1)])
        m.sample(2,[obs("p","pedestrian",.1)])
        m.sample(3,[])
        m.sample(4,[obs("p","pedestrian",1.)])
        m.sample(5,[obs("v","vehicle",-.1)])
        m.sample(6,[obs("v","vehicle",.9)])
        self.assertEqual(m.summary()["vehicle_passages"],0)
        self.assertEqual(m.summary()["pedestrian_crossings"],0)
        self.assertEqual(m.summary()["censored_pedestrian_visits"],1)
        with self.assertRaises(ValueError):
            m.sample(8,[])
        with self.assertRaises(ValueError):
            m.sample(7,[obs("v","vehicle",.1),obs("v","vehicle",.2)])
        self.assertEqual(m.tick,6)


if __name__=="__main__":
    unittest.main()
