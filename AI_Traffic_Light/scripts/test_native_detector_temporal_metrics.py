"""Zero-argument regression for evaluation-only temporal metrics."""
import unittest
from native_detector_temporal_metrics import (presence,episodes,episode_comparison,
    associate,line_events,compare_passages,evaluate_sequence,fault_checks,zone_from_scene)


class TemporalTest(unittest.TestCase):
    def test_presence_denominators(self):
        self.assertEqual(presence([True,False],[False,True]),dict(tp=0,tn=0,fp=1,fn=1,sensitivity=0,specificity=0))
        self.assertIsNone(presence([True],[True])["specificity"])

    def test_censoring_and_missed_episodes(self):
        r=episode_comparison([True,False,True,True],[True,False,False,False],[0,400,800,1200])
        self.assertEqual(r["missed"],[1])
        self.assertIsNone(r["matches"][0]["entry_offset_ms"])
        self.assertTrue(r["truth"][1]["right_censored"])
        self.assertIsNone(episodes([False,True],[0,400])[0]["exit_ms"])

    def test_association_and_passage(self):
        old={0:(4,5),1:(20,20)}
        current,next_id=associate(old,[(6,5),(100,100)],3,2)
        self.assertEqual(current,{0:(6,5),2:(100,100)})
        self.assertEqual(next_id,3)
        events=line_events(old,current,[0,0,10,10],"vehicle",0,400)
        self.assertEqual(len(events),1)
        self.assertEqual(compare_passages(events,events)["matches"],[[0,0]])
        shifted=[{**events[0],"start_ms":400,"stop_ms":800}]
        self.assertEqual(compare_passages(events,shifted)["missed"],[0])

    def test_sequence_and_faults(self):
        def row(x):
            return {"kind":"vehicle","agent_id":"v0","box_xyxy":[x-1,4,x+1,6]}
        frames=[{"time_ms":i*400,"truth":[row(x)],"predictions":[row(x)]}
                for i,x in enumerate([2,4,6,8])]
        report=evaluate_sequence(frames,[3,0,7,10],1,{"vehicle":11,"pedestrian":1.5})
        self.assertEqual(report["vehicle"]["zone_presence"]["specificity"],1)
        self.assertEqual(len(report["vehicle"]["passages"]["matches"]),1)
        self.assertIsNone(report["pedestrian"]["zone_presence"]["sensitivity"])
        self.assertEqual(len(fault_checks()),11)
        self.assertEqual(zone_from_scene({"lanes":[{"kind":"crossing","points":[[5,10],[5,20]],"width_px":2}]}),[4,9,6,21])
        with self.assertRaises(ValueError):
            evaluate_sequence([frames[0],frames[0]],[3,0,7,10],1,{"vehicle":11,"pedestrian":1.5})


if __name__=="__main__":
    unittest.main()
