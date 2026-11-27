"""Isolated native publishing and exact legacy export format checks."""
import csv
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/pc-studio/backend"))
from app.services.experiment_timeline_csv import serialize_experiment_timeline
from app.services.sumo_frame_publisher import NativeFramePublisher
from app.services.sumo_projection import NativeProjection, Projection, VIEW_FLIPS, PROVENANCE
from app.services.sumo_shadow_adapter import ShadowAgent, ShadowSnapshot


class Tests(unittest.TestCase):
    def test_native_publisher(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "net.xml"
            path.write_text('<net><edge id="WC"><lane id="WC_1" shape="0,0 20,0"/></edge></net>')
            layout = Projection.load(path)
            pub = NativeFramePublisher()
            def bundle(gen, tick):
                return NativeProjection(layout, gen).render(ShadowSnapshot(42,tick,False,
                    (ShadowAgent("vehicle","v0",5,0,1,"WC"),)))
            pub.begin(1)
            meta, views = bundle(1, 1)
            pub.publish(meta, views, received_at_ms=42)
            for sid in VIEW_FLIPS:
                frame = pub.frame_for(sid)
                self.assertIs(frame, pub.frame_for(sid))
                scene = pub.scene_for(sid)
                self.assertEqual(scene["source_id"], frame.source_id)
                self.assertEqual(scene["frame_number"], frame.frame_number)
                self.assertEqual(scene["received_at_ms"], frame.received_at_ms)
                self.assertEqual(frame.origin, PROVENANCE)
                self.assertEqual(frame.observation.provenance, "unknown")
            pub.scene_for("simulation_camera")["agents"].clear()
            self.assertEqual(len(pub.scene_for("simulation_camera")["agents"]), 1)
            with self.assertRaises(ValueError):
                pub.publish(meta, views, received_at_ms=43)
            pub.invalidate()
            self.assertIsNone(pub.frame_for("simulation_camera"))
            with self.assertRaises(ValueError):
                pub.publish(meta, views, received_at_ms=44)
            pub.begin(2)
            with self.assertRaises(ValueError):
                pub.publish(meta, views, received_at_ms=45)
            meta2, views2 = bundle(2, 0)
            pub.publish(meta2, views2, received_at_ms=46)
            self.assertEqual(pub.frame_for("simulation_camera").frame_number, 0)
            meta3, views3 = bundle(2, 1)
            views3["simulation_camera_b"] = b"invalid"
            with self.assertRaises(ValueError):
                pub.publish(meta3, views3, received_at_ms=47)
            self.assertIsNone(pub.scene_for("simulation_camera"))
            with self.assertRaises(ValueError):
                pub.publish(meta3, views2, received_at_ms=48)

    def test_lazy_view_cache_and_retirement(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"net.xml"
            path.write_text('<net><edge id="WC"><lane id="WC_1" shape="0,0 20,0"/></edge></net>')
            projection=NativeProjection(Projection.load(path),1)
            snap=ShadowSnapshot(42,1,False,(ShadowAgent("vehicle","v0",5,0,1,"WC"),))
            meta,pixels=projection.render_pixels(snap)
            expected=projection.render(snap)[1]
            pub=NativeFramePublisher()
            pub.begin(1)
            with patch("app.services.sumo_frame_publisher.cv2.imencode",wraps=cv2.imencode) as encoder:
                pub.prepare(meta,pixels,received_at_ms=42)
                pixels[:]=0
                self.assertEqual(encoder.call_count,0)
                first=pub.frame_for("simulation_camera_d")
                self.assertEqual(encoder.call_count,1)
                self.assertIs(first,pub.frame_for("simulation_camera_d"))
                self.assertEqual(encoder.call_count,1)
                for sid in VIEW_FLIPS:
                    self.assertEqual(pub.frame_for(sid).content,expected[sid])
                self.assertEqual(encoder.call_count,4)
                self.assertIsNone(pub._pixels)
                self.assertIs(first,pub.frame_for("simulation_camera_d"))
                self.assertEqual(pub.scene_for("simulation_camera_d")["agents"][0]["x"],1279-meta["agents"][0]["x"])
            newmeta,newpixels=projection.render_pixels(ShadowSnapshot(42,2,False,snap.agents))
            pub.prepare(newmeta,newpixels,received_at_ms=43)
            self.assertTrue(pub.has_tick(2))
            with patch("app.services.sumo_frame_publisher.cv2.imencode",return_value=(False,None)):
                with self.assertRaises(RuntimeError):
                    pub.frame_for("simulation_camera_b")
            self.assertIsNone(pub.frame_for("simulation_camera_d"))
            self.assertFalse(pub.has_tick(2))

    def test_engine_provenance_bound_to_generation(self):
        from app.services.observation_identity import REFERENCE_EVALUATION_ORIGIN
        from app.services.simulation_reference_session import ReferenceAgent
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"net.xml"
            path.write_text('<net><edge id="WC"><lane id="WC_1" shape="0,0 20,0"/></edge></net>')
            layout=Projection.load(path)
            pub=NativeFramePublisher()
            native=NativeProjection(layout,1)
            ref=NativeProjection(layout,2,provenance=REFERENCE_EVALUATION_ORIGIN)
            self.assertEqual(native.layout_id,ref.layout_id)
            snap=ShadowSnapshot(42,1,False,(ReferenceAgent("vehicle","v0",5.,0.,1.,"WC"),))
            meta,pixels=ref.render_pixels(snap)
            pub.begin(2,provenance=REFERENCE_EVALUATION_ORIGIN)
            with self.assertRaises(ValueError):
                pub.prepare({**meta,"provenance":PROVENANCE},pixels,received_at_ms=42)
            pub.prepare(meta,pixels,received_at_ms=42)
            for sid in VIEW_FLIPS:
                frame=pub.frame_for(sid)
                self.assertEqual(frame.origin,REFERENCE_EVALUATION_ORIGIN)
                self.assertTrue(frame.source_id.startswith("reference_eval_"))
                self.assertEqual(pub.scene_for(sid)["provenance"],REFERENCE_EVALUATION_ORIGIN)
                self.assertEqual(frame.observation.provenance,"unknown")
            pub.begin(3)
            self.assertIsNone(pub.frame_for("simulation_camera"))
            with self.assertRaises(ValueError):
                pub.prepare({**meta,"generation":3},pixels,received_at_ms=43)

    def test_export_contract(self):
        timeline = {"fixed":{"timeline":[{"t":1,"phase":"vehicle_green","vehicle_queue":3,
                    "pedestrian_queue":2,"vehicle_passages":1,"pedestrian_crossings":0,"active_rules":["a","b"]}]},
                    "adaptive":{"timeline":[{"t":1,"phase":"pedestrian_green","vehicle_queue":2,
                    "pedestrian_queue":0,"vehicle_passages":0,"pedestrian_crossings":1,"active_rules":[]}]}}
        expected = ("t_seconds,fixed_phase,fixed_vehicle_queue,fixed_pedestrian_queue,fixed_vehicle_passages,"
                    "fixed_pedestrian_crossings,fixed_active_rules,adaptive_phase,adaptive_vehicle_queue,"
                    "adaptive_pedestrian_queue,adaptive_vehicle_passages,adaptive_pedestrian_crossings,adaptive_active_rules\n"
                    "1,vehicle_green,3,2,1,0,a|b,pedestrian_green,2,0,0,1,\n")
        self.assertEqual(serialize_experiment_timeline(timeline), expected)
        partial = serialize_experiment_timeline({"fixed":{"timeline":[{"t":.4,"phase":"all_red"}]}})
        row = next(csv.DictReader(io.StringIO(partial)))
        self.assertEqual(row["fixed_phase"], "all_red")
        for key in row:
            if key not in ("t_seconds","fixed_phase"):
                self.assertEqual(row[key], "")


if __name__ == "__main__":
    unittest.main()
