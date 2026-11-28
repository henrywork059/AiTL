"""Offline method admission and actual shared tiled path with fake inference."""
import copy
import json
from types import SimpleNamespace
import unittest

from native_detector_batch import evaluate
from native_detector_holdout import load_holdout, sha256
from native_detector_tiled import METHOD, tiled_predict, windows
import cv2
import numpy as np
from app.services.sumo_projection import VIEW_FLIPS
from app.services.observation_identity import EVALUATION_ORIGINS


class FakeModel:
    names = {0: "pedestrian"}

    def __init__(self):
        self.calls = []

    def predict(self, *, source, **kwargs):
        self.calls.append(len(source))
        assert kwargs["imgsz"] == 640 and kwargs["conf"] == .1
        def value(v):
            return SimpleNamespace(cpu=lambda: SimpleNamespace(tolist=lambda: v))
        box = SimpleNamespace(xyxy=value([[1,2,5,6]]), conf=value([.8]), cls=value([0]))
        return [SimpleNamespace(boxes=box, names=self.names) for _ in source]


class TiledQualificationTest(unittest.TestCase):
    def test_method_binding(self):
        digest = sha256(b"fixture model")
        method = {"id": METHOD, "batch_size": 8, "source_sha256": {"fixture": digest}}
        plan = {"schema_version": 2, "model_sha256": digest, "model_provenance": "fixture",
                "training_separation": "fixture", "holdout_selection": "fixture",
                "confidence": .1, "iou_threshold": .5, "captures": {"capture.zip": digest},
                "known_training_canonical_pixel_sha256": [sha256(b"fixture training")],
                "criteria_rationale": "test-only numbers",
                "criteria": {k: {"min_truth": 1, "min_precision": .5, "min_recall": .5}
                             for k in ("vehicle","pedestrian")}, "method": method}
        def load(p, expected=method):
            return load_holdout(json.dumps(p).encode(), ["capture.zip"], digest, .1, .5, method=expected)
        self.assertEqual(load(plan), plan)
        for field, bad in (("schema_version",1), ("method", {**method,"batch_size":16}),
                           ("criteria_rationale",""), ("known_training_canonical_pixel_sha256",[])):
            p = copy.deepcopy(plan)
            p[field] = bad
            with self.assertRaises(ValueError):
                load(p)
        with self.assertRaises(ValueError):
            load(plan, None)

    def test_real_tiling_fake_model(self):
        img = np.zeros((720,1280,3), np.uint8)
        ok, data = cv2.imencode(".png", img)
        self.assertTrue(ok)
        ann = {"coordinate_space":"native_projection_v1","provenance":next(iter(EVALUATION_ORIGINS)),
               "authoritative":False,"detector_input_eligible":False,"tick":1,"layout_id":"fixture"}
        view = next(iter(VIEW_FLIPS))
        model = FakeModel()
        for _ in range(2):
            predictions, unmapped, details = tiled_predict(data.tobytes(), ann, view, model)
            self.assertEqual(details["work"], {"requested":45,"evaluated":1,"model_calls":1})
            self.assertEqual(len(predictions),45)
            self.assertEqual(unmapped,[])
            self.assertEqual({tuple(r["box_xyxy"]) for r in predictions},
                             {(x+1,y+2,x+5,y+6) for x,y in windows()})
        self.assertEqual(model.calls,[1,1])
        with self.assertRaises(ValueError):
            tiled_predict(data.tobytes(), {**ann,"authoritative":True}, view, model)
        with self.assertRaises(ValueError):
            evaluate([None], model, capture_root="unused", holdout={"schema_version":1},
                     method={"id":METHOD})


if __name__ == "__main__":
    unittest.main()
