"""Regression tests for supplementary native-center and admission accounting."""
import unittest
from native_detector_temporal_review import availability, native_centers, review_sequence
from native_detector_temporal_metrics import evaluate_sequence


class ReviewTest(unittest.TestCase):
    def test_unknown_is_not_empty(self):
        out=availability([1,1,0,0],[1,0,0,1],[False,True,False,True])
        self.assertEqual(out["occupied"],dict(support=2,timely_correct=0,timely_incorrect=1,
            unavailable=1,timely_correct_fraction_of_all=0,correct_fraction_given_timely=0))
        self.assertEqual(out["empty"]["unavailable"],1)
        self.assertEqual(out["empty"]["timely_incorrect"],1)
        self.assertIsNone(availability([1],[1],[False])["occupied"]["correct_fraction_given_timely"])
        self.assertIsNone(availability([1],[1],[False])["empty"]["timely_correct_fraction_of_all"])
        with self.assertRaises(ValueError):
            availability([1],[1],[1])

    def test_body_center(self):
        scene={"pixels_per_m":2,"agents":[
            {"id":"v","kind":"vehicle","x":20,"y":5,"eastbound":True,"length_m":4},
            {"id":"w","kind":"vehicle","x":20,"y":5,"eastbound":False,"length_m":4},
            {"id":"p","kind":"pedestrian","x":20,"y":5}]}
        self.assertEqual(native_centers(scene,"vehicle"),{"v":(16,5),"w":(24,5)})
        self.assertEqual(native_centers(scene,"pedestrian"),{"p":(20,5)})

    def test_frozen_vs_sensitivity(self):
        import json
        zone=[4,0,6,10]
        frames=[]; scenes=[]
        for i,(raster,native) in enumerate([(3.5,3.5),(5.5,4.5),(6.5,6.5)]):
            box={"agent_id":"v","kind":"vehicle","box_xyxy":[raster-.5,4,raster+.5,6]}
            frames.append({"time_ms":i*400,"truth":[box],"predictions":[box],
                "gate":{"usable":i!=1,"physical_output_allowed":False,
                        "movement_authorized":False,"clearance_shortening_allowed":False}})
            scenes.append({"tick":i*2,"seed":9,"pixels_per_m":1,
                "lanes":[{"kind":"crossing","points":[[5,1],[5,9]],"width_px":2}],
                "agents":[{"id":"v","kind":"vehicle","x":native+1,"y":5,
                           "length_m":2,"eastbound":True}]})
        limits={"vehicle":11,"pedestrian":1.5}
        frozen=json.loads(json.dumps(evaluate_sequence(frames,zone,1,limits)))
        run={"seed":9,"sample_count":3,"zone":zone,"scale":1,"speed_limits_m_s":limits,
             "deadline_usable":2,"metrics":frozen}
        r=review_sequence(frames,scenes,run)["vehicle"]
        self.assertEqual(len(r["raster_reference"]["passages"]["matches"]),1)
        self.assertEqual(len(r["native_center_sensitivity"]["passages"]["matches"]),0)
        self.assertEqual(r["availability_raster"]["occupied"]["unavailable"],1)
        self.assertEqual(r["availability_native"]["occupied"]["unavailable"],1)
        self.assertEqual(run["metrics"],frozen)
        frames[0]["gate"]["movement_authorized"]=True
        with self.assertRaises(ValueError):
            review_sequence(frames,scenes,run)


if __name__=="__main__":
    unittest.main()
