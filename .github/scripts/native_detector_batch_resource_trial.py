"""Offline batch-consolidation and process resource comparison; no live registration."""
import argparse
import os
import platform
import resource
from pathlib import Path
from time import perf_counter, process_time

import numpy as np
from native_detector_tile_trial import predict_view, windows, TILE, STRIDE, IOU, CONFIDENCE
from native_detector_reuse_trial import FrameDedupModel, self_test as reuse_self_test
from native_detector_development_trial import VIEW_FLIPS, inspect_capture, file_sha256, sha, write_json
from native_detector_resolution_trial import MODEL_DIGEST
from native_detector_batch import summarize, latency_summary
from app.services.native_detector_validation import score_footprints

PROFILES = ("reuse_stream_8", "reuse_frame_8", "reuse_frame_16")


class FrameBatchReuse:
    """Group exact unique crops for one frame, with a bounded underlying batch."""
    def __init__(self, model, limit):
        if limit not in (8, 16):
            raise ValueError("Unplanned batch bound")
        self.model, self.limit = model, limit
        self.requested = self.evaluated = self.model_calls = 0

    def __getattr__(self, name):
        return getattr(self.model, name)

    def predict(self, *, source, **kwargs):
        if self.requested or not source:
            raise ValueError("Expected exactly one complete frame batch")
        keys = [(c.shape, c.dtype.str, c.tobytes()) for c in source]
        unique = {}
        for key, crop in zip(keys, source):
            unique.setdefault(key, crop)
        self.requested = len(keys)
        self.evaluated = len(unique)
        results = {}
        entries = list(unique.items())
        for offset in range(0, len(entries), self.limit):
            batch = entries[offset:offset+self.limit]
            out = self.model.predict(source=[c for _, c in batch], **kwargs)
            if len(out) != len(batch):
                raise ValueError("Unique-tile prediction cardinality mismatch")
            results.update(zip((k for k, _ in batch), out))
            self.model_calls += 1
        return [results[k] for k in keys]


def self_test():
    reuse_self_test()
    class Fake:
        def __init__(self):
            self.calls = []

        def predict(self, *, source, **kwargs):
            self.calls.append(len(source))
            return [int(c.sum()) for c in source]

    for limit in (8, 16):
        f = Fake()
        adapter = FrameBatchReuse(f, limit)
        crops = [np.full((2,2,3), i, np.uint8) for i in range(19)]
        request = crops + [crops[2].copy(), crops[0].copy()]
        assert adapter.predict(source=request) == [int(c.sum()) for c in request]
        assert adapter.requested == 21 and adapter.evaluated == 19
        assert max(f.calls) <= limit and sum(f.calls) == 19
        try:
            adapter.predict(source=request)
        except ValueError:
            pass
        else:
            raise AssertionError("Cross-frame reuse admitted")
    assert FrameBatchReuse(Fake(), 8).predict(source=[crops[0]]) == [0]

    class Broken(Fake):
        def predict(self, **kwargs):
            return []
    try:
        FrameBatchReuse(Broken(), 8).predict(source=[crops[0]])
    except ValueError:
        pass
    else:
        raise AssertionError("Bad cardinality admitted")
    print("Whole-frame unique batching, re-expansion, batch bounds and isolation passed")


def run(captures, weights, evidence, profile):
    if platform.system() != "Linux":
        raise ValueError("Linux resource units required for this offline trial")
    if file_sha256(weights) != MODEL_DIGEST:
        raise ValueError("Unexpected checkpoint")
    evidence.mkdir(parents=True, exist_ok=False)
    write_json(evidence / "plan.json", {
        "profile": profile, "model_sha256": MODEL_DIGEST, "capture_artifact_id": 15245454146,
        "checkpoint_artifact_id": 15247571354, "imgsz": 640, "tile_size": TILE,
        "stride": STRIDE, "confidence": CONFIDENCE, "iou_threshold": IOU,
        "reference_target_ms": 500, "reference_target_basis": "existing default inference interval; engineering diagnostic only",
        "formal_holdout_used": False, "migration_authorized": False,
    })
    from ultralytics import YOLO
    model = YOLO(str(weights))
    records = []
    count = 0
    n = len(windows())
    for path in sorted((captures / "val").rglob("capture.zip")):
        raw = path.read_bytes()
        ann, images, _ = inspect_capture(raw, int(path.parent.name.rsplit("-",1)[1]))
        views = {}
        for view in VIEW_FLIPS:
            start = perf_counter()
            cpu = process_time()
            if profile == "reuse_stream_8":
                adapter = FrameDedupModel(model)
                batch = 8
            else:
                adapter = FrameBatchReuse(model, int(profile.rsplit("_",1)[1]))
                batch = n
            predictions, unmapped, tiles = predict_view(images[view], ann, view, adapter, batch_size=batch)
            elapsed = (perf_counter()-start)*1000
            cpu_ms = (process_time()-cpu)*1000
            if len(tiles) != n or adapter.requested != n or not 0 < adapter.evaluated <= n:
                raise ValueError("Incomplete tile coverage or invalid work")
            views[view] = {
                "predictions": predictions, "unmapped_classes": unmapped, "tiles": tiles,
                "score": score_footprints(ann["views"][view], predictions, IOU),
                "prediction_latency_ms": elapsed, "process_cpu_ms": cpu_ms,
                "work": {"requested": adapter.requested, "evaluated": adapter.evaluated, "model_calls": adapter.model_calls},
            }
            count += 1
        records.append({"capture_name": path.relative_to(captures).as_posix(),
                        "archive_sha256": sha(raw), "views": views})
    if len(records) != 16 or count != 64:
        raise ValueError("Incomplete development cohort")
    usage = resource.getrusage(resource.RUSAGE_SELF)
    rows = [v for r in records for v in r["views"].values()]
    report = {
        "profile": profile, "model_sha256": MODEL_DIGEST, "view_count": count,
        "capture_count": len(records), "formal_holdout_used": False,
        "migration_authorized": False, "production_detector_validated": False,
        "physical_output_allowed": False, "views": {
            view: {"micro": summarize(r["views"][view]["score"] for r in records),
                   "latency": latency_summary([r["views"][view]["prediction_latency_ms"] for r in records])}
            for view in VIEW_FLIPS},
        "pooled_latency": latency_summary([v["prediction_latency_ms"] for v in rows]),
        "pooled_cpu_ms": latency_summary([v["process_cpu_ms"] for v in rows]),
        "work": {k: sum(v["work"][k] for v in rows) for k in ("requested","evaluated","model_calls")},
        "resources": {"process_peak_rss_kib": usage.ru_maxrss,
                      "process_user_cpu_s": usage.ru_utime, "process_system_cpu_s": usage.ru_stime,
                      "cpu_affinity_count": len(os.sched_getaffinity(0)), "platform": platform.platform(),
                      "omp_num_threads": os.getenv("OMP_NUM_THREADS")},
        "limitations": "Fresh isolated process per profile on same Linux runner; fixed sequential order, no utilization sampling or Windows/end-to-end claim. CPU time includes all process threads; peak RSS includes imports and model. No accuracy acceptance thresholds.",
    }
    write_json(evidence / "summary.json", report)
    write_json(evidence / "validation.json", {**report, "records": records})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("self-test","run"))
    parser.add_argument("--profile", choices=PROFILES)
    parser.add_argument("--captures", type=Path)
    parser.add_argument("--weights", type=Path)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    if args.mode == "self-test":
        self_test()
    else:
        if not all((args.profile,args.captures,args.weights,args.evidence)):
            parser.error("run requires profile, captures, weights and evidence")
        run(args.captures,args.weights,args.evidence,args.profile)
