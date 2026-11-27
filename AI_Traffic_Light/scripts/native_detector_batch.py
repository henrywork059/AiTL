"""Offline, qualified multi-capture synthetic evaluation; no live model authority."""
import argparse
import hashlib
from io import BytesIO
from importlib.metadata import version
import json
import math
from pathlib import Path
import sys
import shutil
from tempfile import TemporaryDirectory
from time import perf_counter
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/pc-studio/backend"))
from app.services.native_detector_validation import qualified_capture, palette_predictions, model_predictions, score_footprints
from app.services.sumo_projection import VIEW_FLIPS
from native_detector_holdout import admit_pixels, load_holdout, read_pinned_archive, sha256, verdict


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


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


def capture_input(path, capture_root, holdout, seen_pixels):
    if holdout is None:
        with ZipFile(path) as archive:
            annotations, images, integrity = qualified_capture(archive)
        return annotations, images, integrity, file_sha256(path)
    import cv2
    import numpy as np
    name = path.relative_to(capture_root).as_posix()
    digest = holdout["captures"][name]
    content = read_pinned_archive(path, digest)
    with ZipFile(BytesIO(content)) as archive:
        annotations, images, integrity = qualified_capture(archive)
    if not integrity["hash_manifest_verified"]:
        raise ValueError("Holdout requires an internally hashed capture")
    canonical = cv2.imdecode(np.frombuffer(images[next(iter(VIEW_FLIPS))], np.uint8), cv2.IMREAD_COLOR)
    pixel_digest = sha256(canonical.tobytes())
    admit_pixels(pixel_digest, seen_pixels, set(holdout["known_training_canonical_pixel_sha256"]))
    return annotations, images, {**integrity, "canonical_pixel_sha256": pixel_digest}, digest


def evaluate(paths, model=None, confidence=.1, iou=.5, capture_root=None, holdout=None):
    if not paths or not 0 < confidence <= 1 or not 0 < iou <= 1:
        raise ValueError("Invalid batch input")
    if holdout is not None and (model is None or capture_root is None):
        raise ValueError("Holdout requires an explicit offline model and capture root")
    records, seen, seen_pixels = [], set(), set()
    for path in paths:
        annotations, images, integrity, archive_digest = capture_input(path, capture_root, holdout, seen_pixels)
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
        records.append({"capture_name": path.relative_to(capture_root).as_posix() if capture_root is not None else path.name,
                        "archive_sha256": archive_digest, "identity": list(identity), "integrity": integrity, "views": views})
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
    parser.add_argument("--holdout-manifest", type=Path, help="Predeclared synthetic holdout plan; requires trusted local weights")
    parser.add_argument("--confidence", type=float, default=.1)
    parser.add_argument("--iou", type=float, default=.5)
    args = parser.parse_args()
    paths = sorted(args.capture_root.rglob("capture.zip"))
    if not paths or not 0 < args.confidence <= 1 or not 0 < args.iou <= 1:
        parser.error("Require capture.zip files and valid thresholds")
    model_path = args.model.resolve() if args.model is not None else None
    if model_path is not None and (not model_path.is_file() or model_path.suffix.lower() != ".pt"):
        parser.error("Provide trusted existing .pt weights")
    digest = file_sha256(model_path) if model_path is not None else None
    plan, plan_digest = None, None
    if args.holdout_manifest is not None:
        if model_path is None:
            parser.error("Holdout qualification requires explicit trusted weights")
        manifest_bytes = args.holdout_manifest.read_bytes()
        plan_digest = sha256(manifest_bytes)
        plan = load_holdout(manifest_bytes, [p.relative_to(args.capture_root).as_posix() for p in paths],
                            digest, args.confidence, args.iou)
        inputs = {model_path, args.holdout_manifest.resolve(), *(p.resolve() for p in paths)}
        if args.output.resolve() in inputs:
            parser.error("Output must not overwrite a holdout input")
    # All captures must be qualified before loading any model; pinned bytes are
    # checked again at inference, preventing changed inputs from being scored.
    seen, seen_pixels = set(), set()
    for path in paths:
        ann, _, _, _ = capture_input(path, args.capture_root, plan, seen_pixels)
        identity = (ann["epoch"], ann["generation"], ann["tick"], ann["layout_id"])
        if identity in seen:
            parser.error("Duplicate qualified capture identity")
        seen.add(identity)
    with TemporaryDirectory(prefix="mesh-detector-") as temp:
        model = None
        if model_path is not None:
            from ultralytics import YOLO
            # Load only the bytes whose digest was declared, not a later
            # replacement of the original operator-controlled path.
            snapshot = Path(temp) / model_path.name
            shutil.copyfile(model_path, snapshot)
            if file_sha256(snapshot) != digest:
                raise ValueError("Model changed during qualification")
            model = YOLO(str(snapshot))
            if plan is not None and getattr(model, "task", None) != "detect":
                raise ValueError("Holdout requires an object detection model")
        result = evaluate(paths, model, args.confidence, args.iou, args.capture_root, plan)
    result["model_sha256"] = digest
    if plan is not None:
        result["holdout"] = {"manifest_sha256": plan_digest, "plan": plan,
                             "ultralytics_version": version("ultralytics"),
                             "verdict": verdict(plan, result["views"], VIEW_FLIPS)}
    else:
        result["holdout"] = None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({"capture_count": result["capture_count"], "method": result["method"], "canonical": result["views"][result["canonical_view"]]["micro"]}))
    if plan is not None and not result["holdout"]["verdict"]["criteria_met"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
