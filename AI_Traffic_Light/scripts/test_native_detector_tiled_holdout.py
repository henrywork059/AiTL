"""Offline method admission and actual shared tiled path with fake inference."""
import copy
import json
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from types import SimpleNamespace
import unittest

from native_detector_batch import evaluate, capture_input
from native_detector_holdout import load_holdout, sha256
from native_detector_tiled import METHOD, tiled_predict, windows, method_descriptor
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
                           ("criteria_rationale",""), ("known_training_canonical_pixel_sha256",[]),
                           ("model_sha256",sha256(b"other model"))):
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

    def test_descriptor_and_dependency_binding(self):
        with patch("native_detector_tiled.version", side_effect=lambda name: "fixture-" + name):
            descriptor = method_descriptor()
        self.assertEqual(descriptor["batch_size"], 8)
        self.assertEqual(descriptor["versions"]["ultralytics"], "fixture-ultralytics")
        root = Path(__file__).resolve().parents[1]
        for name, digest in descriptor["source_sha256"].items():
            self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(), digest)
        self.assertIn("scripts/native_detector_batch.py", descriptor["source_sha256"])
        digest = sha256(b"fixture")
        plan = {"schema_version": 2, "model_sha256": digest, "model_provenance": "fixture",
                "training_separation": "fixture", "holdout_selection": "fixture",
                "confidence": .1, "iou_threshold": .5, "captures": {"capture.zip": digest},
                "known_training_canonical_pixel_sha256": [sha256(b"training")],
                "criteria_rationale": "fixture only",
                "criteria": {k: {"min_truth": 1, "min_precision": .5, "min_recall": .5}
                             for k in ("vehicle", "pedestrian")}, "method": descriptor}
        for key in ("versions", "source_sha256"):
            mutated = copy.deepcopy(descriptor)
            subkey = next(iter(mutated[key]))
            mutated[key][subkey] = "changed"
            with self.assertRaises(ValueError):
                load_holdout(json.dumps(plan).encode(), ["capture.zip"], digest, .1, .5, method=mutated)
        # No in-process caller can attach a made-up descriptor to predictions.
        with patch("native_detector_tiled.method_descriptor", return_value=descriptor):
            with self.assertRaises(ValueError):
                evaluate([None], FakeModel(), method={**descriptor, "batch_size": 16})

    def test_mirrored_training_and_prior_capture_overlap(self):
        # Only archive qualification is doubled; pixel decoding and hash admission are real.
        image = np.zeros((720,1280,3), np.uint8)
        image[20:30,40:50] = (10,20,30)
        images = {}
        for sid, flip in VIEW_FLIPS.items():
            im = image if flip is None else cv2.flip(image, flip)
            ok, data = cv2.imencode(".png", im)
            self.assertTrue(ok)
            images[sid] = data.tobytes()
        views = list(images)
        mirrored = sha256(cv2.imdecode(np.frombuffer(images[views[1]], np.uint8), cv2.IMREAD_COLOR).tobytes())
        canonical = sha256(image.tobytes())
        self.assertNotEqual(mirrored, canonical)
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "capture.zip"
            path.write_bytes(b"fixture")
            plan = {"schema_version": 2, "captures": {"capture.zip": sha256(b"fixture")},
                    "known_training_canonical_pixel_sha256": [mirrored]}
            with patch("native_detector_batch.qualified_capture",
                       return_value=({}, images, {"hash_manifest_verified": True})), patch(
                           "native_detector_batch.ZipFile"):
                seen = set()
                with self.assertRaises(ValueError):
                    capture_input(path, root, plan, seen)
                self.assertEqual(seen, set())
                plan["known_training_canonical_pixel_sha256"] = [sha256(b"other")]
                capture_input(path, root, plan, seen)
                self.assertEqual(len(seen), 4)
                self.assertIn(mirrored, seen)
                with self.assertRaises(ValueError):
                    capture_input(path, root, plan, seen)
                path.write_bytes(b"changed")
                with self.assertRaises(ValueError):
                    capture_input(path, root, plan, set())


if __name__ == "__main__":
    unittest.main()
