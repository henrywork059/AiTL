"""One-off pinned historical synthetic cohort; exploratory reference, not qualification."""
import argparse
from collections import Counter
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
from zipfile import ZipFile

import cv2
import numpy as np

ARCHIVE_SHA = "b0a8a8220924ecd01d44e9ecc35d6c905fba21db3ee1fca22ea3e6e6a0d2cdf5"
MODEL_SHA = "0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1"
MODEL_URL = "https://huggingface.co/Ultralytics/YOLO11/resolve/5599de6f3b0ef95f98f37530ed0f3bf149c10b37/yolo11n.pt"
# Frozen before viewing any trained-model output; first path per decoded
# canonical-pixel group in the previously executed palette batch.
CAPTURES = {
    "42-normal-adaptive/capture.zip": ("d88ea3505a389545ec927fa7144745db7f717ca9cc66feb00214b0d7f16e9ce2", "48242e483f62c6474716f05d21f9ef125a4b525aeda2190c615d5d1ae316f10b"),
    "42-normal-fixed-midblock_compact/capture.zip": ("c81c1db0693a029cff1f961921912a7b0745bdf20737e412188846d6b7bb3a53", "61b073e503e7cc9d244015b30e1253ee40bce40a50daa17b2cff72381de80034"),
    "42-normal-fixed-midblock_wide/capture.zip": ("ff6ba1f8b2f9bde0b71268ea00aa3199513b220fc76717e15bbc7637dfa2533b", "5d6dc02ed78325717911f6427391d0b7e166b8a5a81fcd671411ef40f8b74258"),
    "73-busy-adaptive/capture.zip": ("497c648fd480f75071661cbb8f0e0d6511a2508c588cefd36a6073d0987da265", "77cd583b30b8a7cef26ef1765d2b180f2aa7dd72ca32cc5a379cbe72982805cd"),
    "73-busy-fixed/capture.zip": ("01c517e8099533fdb23b45965151fd478020ea40daebc44f382f10ffe43954ad", "3236f423921b06168f40ee17cecad39b97c06369f79cf3f11e0995601949888b"),
}
VIEWS = ("simulation_camera", "simulation_camera_b", "simulation_camera_c", "simulation_camera_d")
KINDS = ("vehicle", "pedestrian")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def prepare(archive, root, evidence):
    raw = archive.read_bytes()
    require(sha(raw) == ARCHIVE_SHA, "Unexpected historical artifact bytes")
    require(not root.exists(), "Use a fresh disposable capture root")
    root.mkdir(parents=True)
    evidence.mkdir(parents=True, exist_ok=True)
    with ZipFile(BytesIO(raw)) as outer:
        for name, (archive_sha, pixel_sha) in CAPTURES.items():
            content = outer.read("mesh-sumo-midblock/" + name)
            require(sha(content) == archive_sha, "Capture hash mismatch")
            with ZipFile(BytesIO(content)) as inner:
                image = cv2.imdecode(np.frombuffer(inner.read("simulation_camera.png"), np.uint8), cv2.IMREAD_COLOR)
                require(image is not None and image.shape == (720, 1280, 3), "Bad canonical image")
                require(sha(image.tobytes()) == pixel_sha, "Canonical pixel hash mismatch")
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
    require(len({value[1] for value in CAPTURES.values()}) == len(CAPTURES), "Duplicate cohort pixels")
    (evidence / "cohort.json").write_text(json.dumps({
        "source_artifact_id": 15221111551, "source_artifact_sha256": ARCHIVE_SHA,
        "model_sha256": MODEL_SHA, "model_url": MODEL_URL,
        "model_provenance": "Publisher COCO-pretrained YOLO11n; AGPL-3.0 model card",
        "captures": {name: {"archive_sha256": a, "canonical_pixel_sha256": b}
                     for name, (a, b) in CAPTURES.items()},
        "confidence": .1, "iou_threshold": .5, "selection": "historical deduplicated exploratory cohort",
        "training_separation_independently_verified": False,
        "acceptance_criteria": None, "production_detector_validated": False,
        "migration_authorized": False,
    }, indent=2), encoding="utf-8")


def independently_count(truth, predictions, kind, threshold):
    t = [row["box_xyxy"] for row in truth if row["kind"] == kind]
    p = [row["box_xyxy"] for row in predictions if row["kind"] == kind]
    candidates = []
    for i, (ax, ay, bx, by) in enumerate(t):
        for j, (cx, cy, dx, dy) in enumerate(p):
            intersection = max(0, min(bx, dx) - max(ax, cx)) * max(0, min(by, dy) - max(ay, cy))
            union = (bx-ax)*(by-ay) + (dx-cx)*(dy-cy) - intersection
            overlap = intersection / union
            if overlap >= threshold:
                candidates.append((-overlap, i, j))
    used_t, used_p = set(), set()
    for _, i, j in sorted(candidates):
        if i not in used_t and j not in used_p:
            used_t.add(i)
            used_p.add(j)
    matched = len(used_t)
    return {"truth_count": len(t), "prediction_count": len(p), "matched": matched,
            "unmatched_truth": len(t)-matched, "unmatched_predictions": len(p)-matched}


def verify(root, evidence):
    report = json.loads((evidence / "reference-detector.json").read_text(encoding="utf-8"))
    require(report["method"] == "offline_local_yolo" and report["model_sha256"] == MODEL_SHA,
            "Wrong reference model")
    require(report["holdout"] is None and report["production_detector_validated"] is False
            and report["physical_output_allowed"] is False, "Unexpected authority")
    require(report["confidence"] == .1 and report["iou_threshold"] == .5, "Threshold mismatch")
    records = report["records"]
    require(report["capture_count"] == len(records) == len(CAPTURES)
            and {r["capture_name"] for r in records} == set(CAPTURES), "Incomplete cohort")
    totals = {(v, k): Counter() for v in VIEWS for k in KINDS}
    for record in records:
        name = record["capture_name"]
        content = (root / name).read_bytes()
        require(sha(content) == record["archive_sha256"] == CAPTURES[name][0], "Capture changed")
        with ZipFile(BytesIO(content)) as inner:
            annotations = json.loads(inner.read("synthetic_footprints.json"))
        require(set(record["views"]) == set(VIEWS), "Missing view")
        for view in VIEWS:
            row = record["views"][view]
            require(math.isfinite(row["prediction_latency_ms"]) and row["prediction_latency_ms"] >= 0,
                    "Invalid latency")
            for kind in KINDS:
                counts = independently_count(annotations["views"][view], row["predictions"], kind, .5)
                require(all(row["score"]["by_kind"][kind][k] == value for k, value in counts.items()),
                        "Per-image count mismatch")
                totals[view, kind].update(counts)
    for (view, kind), counts in totals.items():
        actual = report["views"][view]["micro"][kind]
        require(all(actual[k] == value for k, value in counts.items()), "Aggregate count mismatch")
        for metric, denominator in (("precision", "prediction_count"), ("recall", "truth_count")):
            expected = counts["matched"] / counts[denominator] if counts[denominator] else None
            require(actual[metric] == expected, "Aggregate ratio mismatch")
    result = {"verified_records": len(records), "verified_views": len(records)*len(VIEWS),
              "counts": {v: {k: dict(totals[v,k]) for k in KINDS} for v in VIEWS},
              "trained_model_execution_report_reconciled": True,
              "production_detector_validated": False, "migration_authorized": False}
    (evidence / "independent-audit.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "verify"))
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "prepare":
        if args.archive is None:
            parser.error("prepare requires --archive")
        prepare(args.archive, args.root, args.evidence)
    else:
        verify(args.root, args.evidence)
