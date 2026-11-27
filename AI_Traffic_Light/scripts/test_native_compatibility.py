"""Offline coordinate, synthetic footprint and reporting contract regressions."""
import sys
from pathlib import Path
import unittest
from copy import deepcopy
import cv2
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"apps/pc-studio/backend"))
from app.services.native_evaluation_geometry import legacy_rectangle_preview
from app.services.native_detector_validation import footprint_annotations,palette_predictions,score_footprints
from app.services.simulation_gate_reporting import normalized_report_metrics
from app.services.sumo_projection import PROVENANCE,RASTER_PALETTE,VIEW_FLIPS
from app.services.observation_identity import simulation_view_point


class Tests(unittest.TestCase):
    def scene(self):
        return {"geometry":"midblock","engine":"native","coordinate_space":"native_projection_v1",
                "provenance":PROVENANCE,"layout_id":"a"*64,"generation":1,"tick":0,
                "width":1280,"height":720,"pixels_per_m":4.,
                "lanes":[{"id":"WC_1","kind":"road","points":[[20,360],[620,360]]},
                         {"id":"EC_1","kind":"road","points":[[1260,350],[660,350]]},
                         {"id":"NC_0","kind":"walk","points":[[640,270],[640,330]]},
                         {"id":"CS_0","kind":"walk","points":[[640,390],[640,450]]},
                         {"id":"cross","kind":"crossing","points":[[640,340],[640,380]],"width_px":16}],
                "agents":[{"id":"v","kind":"vehicle","x":630.,"y":350.,"length_m":4.5,"width_m":2.,"eastbound":True},
                          {"id":"p","kind":"pedestrian","x":640.,"y":340.,"slot_id":"p0"}]}

    def test_preview_and_mirrors(self):
        scene=self.scene()
        original=deepcopy(scene)
        polygon=[[520,179],[760,179],[760,625],[520,625]]
        base=legacy_rectangle_preview(scene,polygon,"simulation_camera")
        self.assertEqual(base["polygon"],[[632.,340.],[648.,340.],[648.,380.],[632.,380.]])
        for sid in VIEW_FLIPS:
            source=[simulation_view_point(x,y,1280,720,sid) for x,y in polygon]
            mapped=legacy_rectangle_preview(scene,source,sid)
            self.assertEqual(mapped["polygon"],[list(simulation_view_point(x,y,1280,720,sid)) for x,y in base["polygon"]])
            self.assertFalse(mapped["calibrated"])
        self.assertEqual(scene,original)
        with self.assertRaises(ValueError):
            legacy_rectangle_preview(scene,[[520,179],[760,180],[760,625],[520,625]],"simulation_camera")
        with self.assertRaises(ValueError):
            legacy_rectangle_preview({**scene,"geometry":"standard"},polygon,"simulation_camera")

    def test_footprint_and_palette(self):
        scene=self.scene()
        annotation=footprint_annotations(scene)
        img=np.full((720,1280,3),RASTER_PALETTE[0],np.uint8)
        cv2.rectangle(img,(612,346),(630,354),RASTER_PALETTE[4],-1)
        cv2.line(img,(630,346),(630,354),RASTER_PALETTE[5],1)
        cv2.circle(img,(640,340),1,RASTER_PALETTE[6],-1)
        for sid,flip in VIEW_FLIPS.items():
            ok,png=cv2.imencode(".png",img if flip is None else cv2.flip(img,flip))
            self.assertTrue(ok)
            truth=annotation["views"][sid]
            result=score_footprints(truth,palette_predictions(png.tobytes()))
            self.assertEqual(result["matched"],2)
            self.assertTrue(all(x["iou"]==1 for x in result["matches"]))
            self.assertFalse(result["production_detector_validated"])
        self.assertEqual(score_footprints(annotation["views"]["simulation_camera"],[])["unmatched_truth"],2)

    def test_offline_model_uses_box_conversion(self):
        from types import SimpleNamespace
        from app.services.native_detector_validation import model_predictions
        ann=footprint_annotations(self.scene())
        img=np.zeros((720,1280,3),np.uint8)
        ok,png=cv2.imencode(".png",img)
        self.assertTrue(ok)
        class Array:
            def __init__(self,values): self.values=values
            def cpu(self): return self
            def tolist(self): return self.values
        class Model:
            names={0:"car",1:"person",2:"unknown"}
            def predict(self,**kwargs):
                assert kwargs["source"].shape==(720,1280,3) and kwargs["device"]=="cpu"
                return [SimpleNamespace(boxes=SimpleNamespace(
                    xyxy=Array([[612,346,631,355],[639,339,642,342],[1,1,2,2]]),
                    conf=Array([.9,.8,.7]),cls=Array([0,1,2])),names=self.names)]
        predictions,unmapped=model_predictions(png.tobytes(),ann,"simulation_camera",Model())
        self.assertEqual(len(unmapped),1)
        self.assertEqual(score_footprints(ann["views"]["simulation_camera"],predictions)["matched"],2)
        self.assertEqual(predictions[0]["box_xyxy"],[612,346,631,355])
        with self.assertRaises(ValueError):
            model_predictions(png.tobytes(),{**ann,"detector_input_eligible":True},"simulation_camera",Model())

    def test_body_centerline_uses_consecutive_journey(self):
        from app.services.native_evaluation_experiments import vehicle_centerline_events
        from app.services.sumo_midblock_fixture import slots_for,LENGTHS
        from app.services.sumo_shadow_adapter import ShadowAgent
        slots={slot.ident:slot for slot in slots_for(42,"light")}
        half=LENGTHS[slots["v0"].type_id]/2
        old=ShadowAgent("vehicle","v0_0",half-.5,0.,5.,"WC")
        new=ShadowAgent("vehicle","v0_0",half+.5,0.,5.,":C_0")
        self.assertEqual(vehicle_centerline_events((old,),(new,),slots,(-2.,2.),set()),["v0_0"])
        self.assertEqual(vehicle_centerline_events((),(new,),slots,(-2.,2.),set()),[])
        self.assertEqual(vehicle_centerline_events((old,),(new,),slots,(-2.,2.),{"v0_0"}),[])
        self.assertEqual(vehicle_centerline_events((old,),(ShadowAgent("vehicle","v0_0",50.,0.,5.,"CE"),),slots,(-2.,2.),set()),[])
        half=LENGTHS[slots["v1"].type_id]/2
        old=ShadowAgent("vehicle","v1_0",-half+.5,0.,5.,"EC")
        new=ShadowAgent("vehicle","v1_0",-half-.5,0.,5.,":C_1")
        self.assertEqual(vehicle_centerline_events((old,),(new,),slots,(-2.,2.),set()),["v1_0"])

    def test_normalized_report_censoring(self):
        rows=[{"vehicle_queue":1,"pedestrian_queue":0},{"vehicle_queue":2,"pedestrian_queue":1}]
        summary={"vehicle_wait_agent_s":.6,"pedestrian_wait_agent_s":.2,"vehicle_passages":1,
                 "pedestrian_crossings":0,"censored_pedestrian_visits":1}
        episodes={"vehicle":{"observed_agent_seconds":.6,"completed_seconds":[.2],"censored_observed_seconds":[.4]},
                  "pedestrian":{"observed_agent_seconds":.2,"completed_seconds":[],"censored_observed_seconds":[.2]}}
        report=normalized_report_metrics(rows,summary,episodes)
        self.assertEqual(report["waiting"]["vehicle"]["completed"]["count"],1)
        self.assertEqual(report["waiting"]["vehicle"]["censored_observed"]["total_seconds"],.4)
        self.assertEqual(report["queues"]["vehicle"]["queue_seconds"],.6)
        self.assertFalse(report["production_experiment_parity"])


if __name__=="__main__":
    unittest.main()
