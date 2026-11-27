"""Hand-check aggregate counts and missing denominators without trained weights."""
import unittest
from native_detector_batch import summarize, latency_summary
from app.services.native_detector_validation import score_footprints

class BatchTest(unittest.TestCase):
    def test_counts(self):
        truth = [{"kind": "vehicle", "agent_id": "a", "box_xyxy": [0,0,10,10]},
                 {"kind": "pedestrian", "agent_id": "b", "box_xyxy": [30,30,40,40]}]
        prediction = [{"kind": "vehicle", "box_xyxy": [0,0,10,10]},
                      {"kind": "vehicle", "box_xyxy": [50,50,60,60]}]
        result = summarize([score_footprints(truth, prediction), score_footprints(truth, [])])
        self.assertEqual(result["vehicle"]["matched"], 1)
        self.assertEqual(result["vehicle"]["truth_count"], 2)
        self.assertEqual(result["vehicle"]["precision"], .5)
        self.assertEqual(result["vehicle"]["recall"], .5)
        self.assertEqual(result["pedestrian"]["unmatched_truth"], 2)
        self.assertIsNone(result["pedestrian"]["precision"])
        self.assertEqual(result["pedestrian"]["recall"], 0)
    def test_latency(self):
        self.assertEqual(latency_summary([2,1,3])["p95_ms"], 3)
        self.assertEqual(latency_summary([2,1,3])["mean_ms"], 2)
        with self.assertRaises(ValueError): latency_summary([float("nan")])

if __name__ == "__main__":
    unittest.main()
