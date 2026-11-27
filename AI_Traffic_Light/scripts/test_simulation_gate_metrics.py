"""Known normalized geometry trace; both event types, queues and censoring."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"apps/pc-studio/backend"))
from app.services.simulation_gate_metrics import GateMetrics,GateObservation
from verify_wait_trace import record_rows, qualify, replay, comparison
from copy import deepcopy


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

    def test_independent_wait_trace_and_negative_controls(self):
        m=GateMetrics()
        frames=[
            [obs("v","vehicle",-.2),obs("p","pedestrian",-.2)],
            [obs("v","vehicle",-.2),obs("p","pedestrian",-.2)],
            [obs("v","vehicle",-.2),obs("p","pedestrian",-.1)],
            [obs("p","pedestrian",-.1)],
        ]
        raw=[record_rows(row) for row in frames]
        timeline=[m.sample(i,row) for i,row in enumerate(frames,1)]
        summary,episodes=m.summary(),m.waiting_episodes()
        audit=qualify(raw,timeline,summary,episodes)
        self.assertTrue(audit["independent_replay_passed"])
        self.assertEqual(audit["waiting"]["vehicle"]["censored_observed_seconds"],[.4])
        self.assertEqual(audit["waiting"]["pedestrian"]["completed_seconds"],[.2])
        self.assertEqual(audit["waiting"]["pedestrian"]["censored_observed_seconds"],[.2])
        scaled=[[[i,k,p,x*11,y*11,s*11,g] for i,k,p,x,y,s,g in row] for row in raw]
        self.assertEqual(replay(raw),replay(scaled))
        changed=deepcopy(timeline)
        changed[1]["vehicle_queue"]=0
        with self.assertRaisesRegex(ValueError,"queue mismatch"):
            qualify(raw,changed,summary,episodes)
        changed=deepcopy(episodes)
        changed["vehicle"]["censored_observed_seconds"]=[.2,.2]
        with self.assertRaisesRegex(ValueError,"episode mismatch"):
            qualify(raw,timeline,summary,changed)
        changed=deepcopy(summary)
        changed["vehicle_wait_agent_s"]=.2
        with self.assertRaisesRegex(ValueError,"integral"):
            qualify(raw,timeline,changed,episodes)
        runs=[{"engine":e,"summary":summary,"wait_audit":audit} for e in ("legacy","native") for _ in range(2)]
        verdict=comparison(runs,"legacy","native",False)
        self.assertTrue(verdict["exact_wait_totals_equal"])
        self.assertEqual(verdict["production_wait_parity"],"not_established")
        self.assertFalse(verdict["default_migration_allowed"])
        changed=deepcopy(runs)
        changed[-1]["wait_audit"]={**audit,"trace_sha256":"different"}
        with self.assertRaisesRegex(ValueError,"Nonrepeatable"):
            comparison(changed,"legacy","native",False)

    def test_wait_gate_change_censors_old_episode(self):
        m=GateMetrics()
        frames=[[obs("v","vehicle",-.2,gate=g)] for g in ("a","a","b","b")]
        timeline=[m.sample(i,row) for i,row in enumerate(frames,1)]
        audit=qualify([record_rows(row) for row in frames],timeline,m.summary(),m.waiting_episodes())
        self.assertEqual(audit["waiting"]["vehicle"]["censored_observed_seconds"],[.2,.2])

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
