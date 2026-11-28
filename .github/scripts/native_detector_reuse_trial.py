"""Development-only exact tile reuse; no holdout or live registration."""
import argparse
from collections import Counter
from pathlib import Path
from time import perf_counter

import numpy as np

from native_detector_tile_trial import (
    predict_view, self_test as tile_self_test, CONFIDENCE, IOU, TILE, STRIDE, windows,
)
from native_detector_development_trial import (
    VIEW_FLIPS, inspect_capture, file_sha256, sha, write_json,
)
from native_detector_resolution_trial import MODEL_DIGEST
from native_detector_batch import summarize, latency_summary
from app.services.native_detector_validation import score_footprints


class FrameDedupModel:
    """One frame only; exact byte equality, not similarity or stale tracking."""
    def __init__(self, model):
        self.model = model
        self.results = {}
        self.requested = self.evaluated = self.model_calls = 0

    def __getattr__(self, name):
        return getattr(self.model, name)

    def predict(self, *, source, **kwargs):
        keys = [(crop.shape, crop.dtype.str, crop.tobytes()) for crop in source]
        missing = {}
        for key, crop in zip(keys, source):
            if key not in self.results:
                missing.setdefault(key, crop)
        self.requested += len(keys)
        if missing:
            results = self.model.predict(source=list(missing.values()), **kwargs)
            if len(results) != len(missing):
                raise ValueError("Unique-tile prediction cardinality mismatch")
            self.results.update(zip(missing, results))
            self.evaluated += len(missing)
            self.model_calls += 1
        return [self.results[key] for key in keys]


def self_test():
    tile_self_test()

    class Fake:
        names = {0: "vehicle"}

        def __init__(self):
            self.calls = []

        def predict(self, *, source, **kwargs):
            self.calls.append(len(source))
            return [int(crop.sum()) for crop in source]

    a = np.zeros((2, 2, 3), np.uint8)
    b = a.copy()
    b[0, 0, 0] = 1
    model = Fake()
    frame = FrameDedupModel(model)
    assert frame.names == model.names
    assert frame.predict(source=[a, a.copy(), b], imgsz=640) == [0, 0, 1]
    assert frame.predict(source=[b.copy(), a.copy()], imgsz=640) == [1, 0]
    assert (frame.requested, frame.evaluated, frame.model_calls) == (5, 2, 1)
    assert FrameDedupModel(model).predict(source=[a], imgsz=640) == [0]
    assert model.calls == [2, 1]

    class Broken(Fake):
        def predict(self, **kwargs):
            return []

    broken = FrameDedupModel(Broken())
    try:
        broken.predict(source=[a, b])
    except ValueError:
        pass
    else:
        raise AssertionError("Bad cardinality admitted")
    assert broken.results == {}
    print("Exact reuse, pixel distinction, cross-batch reuse, frame isolation and invalid cardinality passed")


def class_boxes(rows):
    return Counter((r["class_name"], tuple(r["box_xyxy"])) for r in rows)


def parity(base, reuse):
    return {
        "merged_exact": base["predictions"] == reuse["predictions"],
        "merged_class_boxes_equal": class_boxes(base["predictions"]) == class_boxes(reuse["predictions"]),
        "raw_class_boxes_equal": all(
            class_boxes(a["local_predictions"]) == class_boxes(b["local_predictions"])
            for a, b in zip(base["tiles"], reuse["tiles"])
        ),
        "unmapped_class_boxes_equal": class_boxes(base["unmapped_classes"]) == class_boxes(reuse["unmapped_classes"]),
        "score_counts_equal": all(
            base["score"]["by_kind"][k] == reuse["score"]["by_kind"][k]
            for k in ("vehicle", "pedestrian")
        ),
    }


def evaluate(captures, weights, evidence):
    if file_sha256(weights) != MODEL_DIGEST:
        raise ValueError("Unexpected development checkpoint")
    evidence.mkdir(parents=True, exist_ok=False)
    write_json(evidence / "plan.json", {
        "model_sha256": MODEL_DIGEST, "capture_artifact_id": 15245454146,
        "checkpoint_artifact_id": 15247571354, "imgsz": 640,
        "tile_size": TILE, "stride": STRIDE, "confidence": CONFIDENCE, "iou_threshold": IOU,
        "profiles": ["baseline", "frame_exact_reuse"],
        "order": "alternate per paired view; separate model instances",
        "formal_holdout_used": False, "migration_authorized": False,
    })
    from ultralytics import YOLO
    models = {k: YOLO(str(weights)) for k in ("baseline", "frame_exact_reuse")}
    records = []
    count = 0
    expected = len(windows())
    for path in sorted((captures / "val").rglob("capture.zip")):
        raw = path.read_bytes()
        ann, images, _ = inspect_capture(raw, int(path.parent.name.rsplit("-", 1)[1]))
        views = {}
        for view in VIEW_FLIPS:
            profiles = {}
            order = list(models) if count % 2 == 0 else list(reversed(models))
            for profile in order:
                start = perf_counter()
                model = models[profile]
                if profile == "frame_exact_reuse":
                    model = FrameDedupModel(model)
                predictions, unmapped, tiles = predict_view(images[view], ann, view, model)
                elapsed = (perf_counter() - start) * 1000
                if len(tiles) != expected:
                    raise ValueError("Incomplete tile coverage")
                work = {"requested": expected, "evaluated": expected, "model_calls": (expected + 7) // 8}
                if profile == "frame_exact_reuse":
                    work = {"requested": model.requested, "evaluated": model.evaluated, "model_calls": model.model_calls}
                    if work["requested"] != expected or not 0 < work["evaluated"] <= expected:
                        raise ValueError("Invalid reuse counters")
                profiles[profile] = {
                    "predictions": predictions, "unmapped_classes": unmapped, "tiles": tiles,
                    "prediction_latency_ms": elapsed, "work": work,
                    "score": score_footprints(ann["views"][view], predictions, IOU),
                }
            views[view] = {"order": order, "profiles": profiles,
                           "parity": parity(profiles["baseline"], profiles["frame_exact_reuse"])}
            count += 1
        records.append({"capture_name": path.relative_to(captures).as_posix(),
                        "archive_sha256": sha(raw), "views": views})
    if len(records) != 16 or count != 64:
        raise ValueError("Incomplete matched cohort")
    summary = {}
    for profile in models:
        summary[profile] = {
            view: {
                "micro": summarize(r["views"][view]["profiles"][profile]["score"] for r in records),
                "latency": latency_summary([r["views"][view]["profiles"][profile]["prediction_latency_ms"] for r in records]),
                "work": {k: sum(r["views"][view]["profiles"][profile]["work"][k] for r in records)
                         for k in ("requested", "evaluated", "model_calls")},
            } for view in VIEW_FLIPS
        }
    parity_counts = Counter()
    for record in records:
        for row in record["views"].values():
            parity_counts.update(k for k, v in row["parity"].items() if v)
    report = {"model_sha256": MODEL_DIGEST, "profiles": summary, "parity_view_counts": dict(parity_counts),
              "capture_count": len(records), "view_count": count, "formal_holdout_used": False,
              "migration_authorized": False, "production_detector_validated": False,
              "physical_output_allowed": False,
              "limitations": "Synthetic development only. Different batch composition may change predictions; no cross-frame reuse, no acceptance criteria."}
    write_json(evidence / "summary.json", report)
    write_json(evidence / "paired-validation.json", {**report, "records": records})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("self-test", "evaluate"))
    parser.add_argument("--captures", type=Path)
    parser.add_argument("--weights", type=Path)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    if args.mode == "self-test":
        self_test()
    else:
        if not all((args.captures, args.weights, args.evidence)):
            parser.error("evaluate requires captures, weights and evidence")
        evaluate(args.captures, args.weights, args.evidence)
