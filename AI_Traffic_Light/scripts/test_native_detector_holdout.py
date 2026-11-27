"""Deterministic holdout admission tests; no model or field accuracy claim."""
import json
from pathlib import Path
import tempfile
import unittest
from native_detector_holdout import admit_pixels, load_holdout, read_pinned_archive, sha256, verdict


class HoldoutTest(unittest.TestCase):
    def setUp(self):
        self.model = sha256(b"test double")
        self.capture = sha256(b"archive")
        self.plan = {"schema_version": 1, "model_sha256": self.model,
                     "model_provenance": "fixture", "training_separation": "fixture only",
                     "holdout_selection": "predeclared fixture", "confidence": .1,
                     "iou_threshold": .5, "captures": {"a/capture.zip": self.capture},
                     "known_training_canonical_pixel_sha256": [],
                     "criteria": {k: {"min_truth": 2, "min_precision": .75, "min_recall": .75}
                                  for k in ("vehicle", "pedestrian")}}

    def load(self):
        return load_holdout(json.dumps(self.plan).encode(), ["a/capture.zip"], self.model, .1, .5)

    def test_plan(self):
        self.assertEqual(self.load(), self.plan)
        for key, bad in (("model_sha256", self.capture), ("confidence", .2),
                         ("captures", {"other/capture.zip": self.capture}),
                         ("training_separation", ""), ("criteria", {})):
            original = self.plan[key]
            self.plan[key] = bad
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.load()
            self.plan[key] = original
        with self.assertRaises(ValueError):
            load_holdout(b'{"schema_version":1,"schema_version":1}', [], self.model, .1, .5)

    def test_pinned_bytes_and_pixels(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "capture.zip"
            path.write_bytes(b"archive")
            self.assertEqual(read_pinned_archive(path, self.capture), b"archive")
            path.write_bytes(b"changed")
            with self.assertRaises(ValueError):
                read_pinned_archive(path, self.capture)
        seen = set()
        admit_pixels(self.capture, seen, {self.model})
        for digest in (self.capture, self.model):
            with self.assertRaises(ValueError):
                admit_pixels(digest, seen, {self.model})

    def test_verdict(self):
        def view():
            return {"micro": {k: {"truth_count": 4, "precision": .75, "recall": 1.0}
                              for k in ("vehicle", "pedestrian")}}
        views = {"A": view(), "B": view()}
        self.assertTrue(verdict(self.plan, views, ("A", "B"))["criteria_met"])
        for key, bad in (("truth_count", 1), ("precision", None), ("recall", .5), ("precision", float("nan"))):
            original = views["B"]["micro"]["vehicle"][key]
            views["B"]["micro"]["vehicle"][key] = bad
            result = verdict(self.plan, views, ("A", "B"))
            self.assertFalse(result["criteria_met"])
            self.assertFalse(result["migration_authorized"])
            views["B"]["micro"]["vehicle"][key] = original
        with self.assertRaises(ValueError):
            verdict(self.plan, views, ("A", "B", "C"))


if __name__ == "__main__":
    unittest.main()
