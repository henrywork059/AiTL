"""Deterministic checks of every-tick reference and bracket ambiguity."""
import unittest
from native_detector_tick_truth import bracket_review,collisions,series,analyze,freeze_scene


def event(ident,start,stop,direction="positive"):
    return {"id":ident,"direction":direction,"start_ms":start,"stop_ms":stop}


class TickTruthTest(unittest.TestCase):
    def test_wire_geometry_normalization(self):
        original={"bounds_m":(0,1,2,3),"lanes":[{"points":[(1,2),(3,4)]}]}
        frozen=freeze_scene(original)
        self.assertEqual(frozen,{"bounds_m":[0,1,2,3],"lanes":[{"points":[[1,2],[3,4]]}]})
        frozen["lanes"][0]["points"][0][0]=99
        self.assertEqual(original["lanes"][0]["points"][0],(1,2))
        with self.assertRaises(ValueError):
            freeze_scene({"x":float("nan")})

    def test_brackets_not_tuned(self):
        native=[event("a",0,200),event("b",200,400),event("c",200,400),
                event("d",0,200),event("r",0,200),event("r",400,600)]
        sample=[event("a",0,400),event("b",400,800),event("c",800,1200),
                event("r",0,400),event("z",0,400)]
        result={r["id"]:r["status"] for r in bracket_review(native,sample)}
        self.assertEqual(result,{"a":"overlap","b":"touching","c":"disjoint",
            "d":"native_only","r":"ambiguous_repeated_identity","z":"sample_only"})
        self.assertEqual(collisions(native,[0,400,800]),
            [{"start_ms":0,"stop_ms":400,"direction":"positive","native_indices":[0,1,2,3,4]}])

    def test_subsample_hidden_episode(self):
        points=[{"p":(3,5)},{"p":(5,5)},{"p":(7,5)}]
        full=series(points,[0,200,400],[4,4,6,6],"vehicle")
        sampled=series(points[::2],[0,400],[4,4,6,6],"vehicle")
        self.assertEqual(full["occupied_samples"],1)
        self.assertEqual(full["complete_episodes"],1)
        self.assertEqual(sampled["occupied_samples"],0)
        self.assertEqual(full["passages"],[event("p",0,200)])
        self.assertEqual(sampled["passages"],[event("p",0,400)])

    def test_complete_tick_trace_and_hidden_episode(self):
        common={"epoch":"x","generation":1,"layout_id":"l","seed":1,"geometry":"midblock",
                "density":"light","engine":"native","provenance":"synthetic_sumo_projection",
                "coordinate_space":"native_projection_v1","demand_digest":"d","pixels_per_m":1,
                "paused":False,"lanes":[{"kind":"crossing","points":[[5,4],[5,6]],"width_px":2}]}
        scene=[];raster={}
        for i,x in enumerate([3,5,7]):
            scene.append({**common,"tick":i,"time_s":i/5,"received_at_ms":i,"signal":None if i==0 else
                {"vehicle_go":False,"pedestrian_walk":False,"applied_vehicle_go":False,"applied_pedestrian_walk":False},
                "agents":[{"id":"v","kind":"vehicle","x":x+1,"y":5,"length_m":2,"eastbound":True}]})
            if i%2==0:
                raster[i]=[{"agent_id":"v","kind":"vehicle","box_xyxy":[x-.5,4.5,x+.5,5.5]}]
        r=analyze(scene,raster)["classes"]["vehicle"]
        self.assertEqual(r["hidden_occupancy_episode_indices"],[0])
        self.assertEqual(r["native_vs_sampled_brackets"][0]["status"],"overlap")
        with self.assertRaises(ValueError):
            analyze(scene,{0:raster[0]})
        scene[1]["tick"]=2
        with self.assertRaises(ValueError):
            analyze(scene,raster)


if __name__=="__main__":
    unittest.main()
