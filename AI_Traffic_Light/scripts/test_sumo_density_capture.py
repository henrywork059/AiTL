"""Offline finite-demand and isolated capture contract regression."""
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch
import json
import os

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/pc-studio/backend"))
from app.services.sumo_shadow_fixture import write_scenario, DENSITY_COUNTS, SLOW_WALK_M_S
from app.services.sumo_projection import NativeProjection, Projection, PROVENANCE
from app.services.sumo_shadow_adapter import ShadowSnapshot, ShadowAgent
from app.services.sumo_projection_capture import evaluation_frames
from app.services.dataset_capture import DatasetCaptureService


class Tests(unittest.TestCase):
    def test_demand(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for density, (vehicles, people) in DENSITY_COUNTS.items():
                write_scenario(root, controlled=True, density=density)
                route = ET.parse(root / "routes.xml").getroot()
                self.assertEqual(len(route.findall("vehicle")), vehicles)
                self.assertEqual(len(route.findall("person")), people)
                self.assertEqual(float(route.find("person[@id='p0']/walk").get("speed")), SLOW_WALK_M_S)
                departures = [float(x.get("depart")) for x in route if x.tag in ("vehicle", "person")]
                self.assertEqual(departures, sorted(departures))
            with self.assertRaises(ValueError):
                write_scenario(root, controlled=True, density="unknown")
            write_scenario(root, controlled=True)
            self.assertEqual(len(ET.parse(root / "routes.xml").getroot().findall("person")), 12)

    def test_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            network = root / "net.xml"
            network.write_text('<net><edge id="WC"><lane id="WC_1" shape="0,0 20,0"/></edge></net>')
            projection = NativeProjection(Projection.load(network), 3)
            meta, views = projection.render(ShadowSnapshot(42, 5, False, (ShadowAgent("vehicle","v0",5,0,1,"WC"),)))
            frames = evaluation_frames(meta, views, received_at_ms=100)
            with patch.dict(os.environ, {"AITL_DATASET_DIR": str(root / "dataset")}):
                service = DatasetCaptureService()
                for frame in frames:
                    record = service.capture_frame(frame, session_id="native_evaluation")
                    self.assertEqual(record.origin, PROVENANCE)
                    self.assertTrue(record.source_id.startswith("native_eval_g3_"))
                    self.assertEqual(record.source_frame_number, 5)
                    self.assertEqual((service.dataset_root / record.image_path).read_bytes(), frame.content)
                    self.assertEqual(json.loads((service.dataset_root / record.metadata_path).read_text())["origin"], PROVENANCE)
                    self.assertEqual(frame.observation.provenance, "unknown")
                self.assertEqual(service.status()["frame_count"], 4)
            broken = {**views, "simulation_camera_b": views["simulation_camera"]}
            with self.assertRaises(ValueError):
                evaluation_frames(meta, broken, received_at_ms=100)


if __name__ == "__main__":
    unittest.main()
