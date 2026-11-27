"""Hand-check aggregate counts and missing denominators without trained weights."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from zipfile import ZipFile
import cv2
import numpy as np
from native_detector_batch import evaluate, summarize, latency_summary, file_sha256
from native_detector_holdout import verdict
from app.services.observation_identity import SUMO_EVALUATION_ORIGIN
from app.services.sumo_projection import WIDTH, HEIGHT, VIEW_FLIPS
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


    def test_pinned_batch_with_production_converter_and_model_double(self):
        # The archive reader and model are doubles; PNG decoding, production
        # result conversion, mapping, matching, aggregation and verdict are real.
        truth = [{"kind": "vehicle", "agent_id": "car", "box_xyxy": [10, 10, 30, 30]},
                 {"kind": "pedestrian", "agent_id": "person", "box_xyxy": [50, 50, 60, 70]}]
        image = np.zeros((HEIGHT, WIDTH, 3), np.uint8)
        ok, png = cv2.imencode(".png", image)
        self.assertTrue(ok)
        annotations = {"epoch": "fixture", "generation": 1, "tick": 2, "layout_id": "fixture",
                       "coordinate_space": "native_projection_v1", "provenance": SUMO_EVALUATION_ORIGIN,
                       "detector_input_eligible": False, "authoritative": False,
                       "views": {sid: truth for sid in VIEW_FLIPS}}
        images = {sid: png.tobytes() for sid in VIEW_FLIPS}
        def tensor(rows):
            return SimpleNamespace(cpu=lambda: np.asarray(rows))
        boxes = SimpleNamespace(xyxy=tensor([[10, 10, 30, 30], [50, 50, 60, 70], [80, 80, 90, 90]]),
                                conf=tensor([.9, .8, .7]), cls=tensor([0, 1, 2]))
        class ModelDouble:
            calls = 0
            def predict(self, **kwargs):
                self.calls += 1
                if kwargs["device"] != "cpu" or kwargs["save"] or kwargs["conf"] != .1:
                    raise AssertionError("Unexpected offline inference settings")
                return [SimpleNamespace(boxes=boxes, names={0: "car", 1: "person", 2: "dog"})]
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "capture.zip"
            with ZipFile(path, "w") as archive:
                archive.writestr("fixture", "test-only archive")
            plan = {"captures": {"capture.zip": file_sha256(path)},
                    "known_training_canonical_pixel_sha256": [],
                    "criteria": {k: {"min_truth": 1, "min_precision": 1, "min_recall": 1}
                                 for k in ("vehicle", "pedestrian")}}
            model = ModelDouble()
            with patch("native_detector_batch.qualified_capture",
                       return_value=(annotations, images, {"hash_manifest_verified": True})):
                result = evaluate([path], model, capture_root=root, holdout=plan)
                self.assertEqual(model.calls, len(VIEW_FLIPS))
                self.assertTrue(verdict(plan, result["views"], VIEW_FLIPS)["criteria_met"])
                self.assertFalse(result["production_detector_validated"])
                for view in result["records"][0]["views"].values():
                    self.assertEqual(view["score"]["matched"], 2)
                    self.assertEqual(view["unmapped_classes"][0]["class_name"], "dog")
                digest = result["records"][0]["integrity"]["canonical_pixel_sha256"]
                plan["known_training_canonical_pixel_sha256"] = [digest]
                with self.assertRaises(ValueError):
                    evaluate([path], model, capture_root=root, holdout=plan)
                plan["known_training_canonical_pixel_sha256"] = []
                path.write_bytes(b"changed")
                with self.assertRaises(ValueError):
                    evaluate([path], model, capture_root=root, holdout=plan)
                self.assertEqual(model.calls, len(VIEW_FLIPS))

if __name__ == "__main__":
    unittest.main()
