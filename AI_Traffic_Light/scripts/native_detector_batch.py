"""Offline, qualified multi-capture synthetic evaluation; no live model authority."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from time import perf_counter
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/pc-studio/backend"))
from app.services.native_detector_validation import qualified_capture, palette_predictions, model_predictions, score_footprints
from app.services.sumo_projection import VIEW_FLIPS


def summarize(scores):
    """Micro counts on a single named view; never pool correlated mirrors."""
    scores = list(scores)
    result = {}
    for kind in ("vehicle", "pedestrian"):
        counts = {key: sum(s["by_kind"][kind][key] for s in scores)
                  for key in ("truth_count", "prediction_count", "matched", "unmatched_truth", "unmatched_predictions")}
        counts["precision"] = counts["matched"] / counts["prediction_count"] if counts["prediction_count"] else None
        counts["recall"] = counts["matched"] / counts["truth_count"] if counts["truth_count"] else None
        result[kind] = counts
    return result


def latency_summary(samples):
    values = sorted(samples)
    if not values or any(not math.isfinite(x) or x < 0 for x in values):
        raise ValueError("Invalid latency samples")
    return {"count": len(values), "mean_ms": sum(values) / len(values),
            "p95_ms": values[math.ceil(.95 * len(values)) - 1], "raw_ms": samples}


def evaluate(paths, model=None, confidence=.1, iou=.5):
    if not paths or not 0 < confidence <= 1 or not 0 < iou <= 1:
        raise ValueError("Invalid batch input")
    records, seen = [], set()
    for path in paths:
        with ZipFile(path) as archive:
            annotations, images, integrity = qualified_capture(archive)
        identity = (annotations["epoch"], annotations["generation"], annotations["tick"], annotations["layout_id"])
        if identity in seen:
            raise ValueError("Duplicate qualified capture identity")
        seen.add(identity)
        views = {}
        for sid in VIEW_FLIPS:
            start = perf_counter()
            predictions, unmapped = (palette_predictions(images[sid]), []) if model is None else model_predictions(images[sid], annotations, sid, model, confidence)
            elapsed = (perf_counter() - start) * 1000
            views[sid] = {"score": score_footprints(annotations["views"][sid], predictions, iou),
                          "prediction_latency_ms": elapsed, "predictions": predictions,
                          "unmapped_classes": unmapped}
        records.append({"capture_name": path.name, "identity": list(identity), "integrity": integrity, "views": views})
    return {"schema_version": 1, "evidence_class": "executed_synthetic_capture_evaluation",
            "method": "exact_palette_components_not_trained_model" if model is None else "offline_local_yolo",
            "confidence": confidence if model is not None else None, "iou_threshold": iou,
            "capture_count": len(records), "canonical_view": next(iter(VIEW_FLIPS)),
            "views": {sid: {"micro": summarize(r["views"][sid]["score"] for r in records),
                           "latency": latency_summary([r["views"][sid]["prediction_latency_ms"] for r in records])}
                      for sid in VIEW_FLIPS},
            "records": records, "production_detector_validated": False, "physical_output_allowed": False,
            "limitations": "Synthetic raster truth; mirrored views reported separately; captures may be correlated or repeated seeded demand. Prediction latency includes decode/conversion, not model load, scoring or live pipeline; no mAP, field accuracy or independence claim."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", type=Path, help="Explicit trusted local .pt weights; never download")
    parser.add_argument("--confidence", type=float, default=.1)
    parser.add_argument("--iou", type=float, default=.5)
    args = parser.parse_args()
    paths = sorted(args.capture_root.rglob("capture.zip"))
    if not paths or not 0 < args.confidence <= 1 or not 0 < args.iou <= 1:
        parser.error("Require capture.zip files and valid thresholds")
    model = None
    digest = None
    # All capture qualification must precede model loading.
    for path in paths:
        with ZipFile(path) as archive:
            qualified_capture(archive)
    if args.model is not None:
        path = args.model.resolve()
        if not path.is_file() or path.suffix.lower() != ".pt":
            parser.error("Provide trusted existing .pt weights")
        with path.open("rb") as source:
            h = hashlib.sha256()
            for block in iter(lambda: source.read(1048576), b""):
                h.update(block)
        digest = h.hexdigest()
        from ultralytics import YOLO
        model = YOLO(str(path))
    result = evaluate(paths, model, args.confidence, args.iou)
    result["model_sha256"] = digest
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({"capture_count": result["capture_count"], "method": result["method"], "canonical": result["views"][result["canonical_view"]]["micro"]}))


if __name__ == "__main__":
    main()
