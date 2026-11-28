"""Run schema-2 evaluator on the pinned, already-seen development cohort only."""
import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2] / "AI_Traffic_Light"
sys.path.insert(0, str(ROOT / "scripts"))
from native_detector_batch import file_sha256, capture_input
from native_detector_holdout import load_holdout
from native_detector_tiled import method_descriptor

CHECKPOINT = "9c888355e3228db090c98969672a4418eb207e1c0ffa926746091485da84ecba"


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def boxes(rows):
    return Counter((r["class_name"], tuple(r["box_xyxy"])) for r in rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("captures", "weights", "source-manifest", "reference", "evidence"):
        p.add_argument("--"+name, required=True, type=Path)
    a = p.parse_args()
    a.evidence.mkdir(parents=True, exist_ok=False)
    if file_sha256(a.weights) != CHECKPOINT:
        raise ValueError("Unexpected reference checkpoint")
    reference = json.loads(a.reference.read_text(encoding="utf-8"))
    if (reference["model_sha256"] != CHECKPOINT or reference["formal_holdout_used"] is not False
            or reference["capture_count"] != 16 or reference["view_count"] != 64):
        raise ValueError("Unexpected paired development reference")
    source = json.loads(a.source_manifest.read_text(encoding="utf-8"))
    training = sorted({v["pixel_sha256"] for k,v in source["images"].items() if k.startswith("images/train/")})
    if len(training) != 96 or source["formal_holdout_used"] is not False:
        raise ValueError("Unexpected development training manifest")
    records = json.loads((a.captures / "manifest.json").read_text(encoding="utf-8"))["records"]
    root = a.captures / "val"
    names = sorted(p.relative_to(root).as_posix() for p in root.rglob("capture.zip"))
    expected = {r["capture_name"].removeprefix("val/"): r["archive_sha256"] for r in reference["records"]}
    if len(names) != 16 or set(names) != set(expected):
        raise ValueError("Development validation cohort mismatch")
    for name, digest in expected.items():
        if records["val/"+name]["archive_sha256"] != digest or file_sha256(root/name) != digest:
            raise ValueError("Development capture digest mismatch")
    if set(training) != {h for n,row in records.items() if n.startswith("train/") for h in row["pixels"].values()}:
        raise ValueError("Training digest list mismatch")
    command = [sys.executable, str(ROOT/"scripts/native_detector_batch.py"), "--method", "tiled-stream-reuse-v1"]
    descriptor = json.loads(subprocess.check_output(command+["--describe-method"], text=True))
    if descriptor != method_descriptor():
        raise ValueError("CLI method identity differs")
    for name,digest in descriptor["source_sha256"].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != digest:
            raise ValueError("Source digest mismatch")
    write(a.evidence/"method.json", descriptor)
    # These are historical development reference minima, NOT independently
    # justified absolute accuracy thresholds for a reserved holdout.
    views = reference["profiles"]["frame_exact_reuse"]
    criteria = {kind: {"min_truth": min(v["micro"][kind]["truth_count"] for v in views.values()),
                      "min_precision": min(v["micro"][kind]["precision"] for v in views.values()),
                      "min_recall": min(v["micro"][kind]["recall"] for v in views.values())}
                for kind in ("vehicle","pedestrian")}
    plan = {"schema_version":2, "method":descriptor, "model_sha256":CHECKPOINT,
            "model_provenance":"Original fixed six-epoch tiled development artifact 15247571354",
            "training_separation":"Known 96 decoded training orientations; not proof of crop-level independence",
            "holdout_selection":"DEVELOPMENT REGRESSION ONLY: previously evaluated validation artifact 15245454146; not the reserved holdout",
            "criteria_rationale":"Prior streaming-eight per-view minima from artifact 15247099750, for regression only; not absolute qualification criteria",
            "confidence":.1, "iou_threshold":.5, "captures":expected,
            "known_training_canonical_pixel_sha256":training, "criteria":criteria}
    path = a.evidence/"development-plan.json"
    write(path, plan)
    load_holdout(path.read_bytes(), names, CHECKPOINT, .1, .5, method=descriptor)
    # Verify that a known noncanonical orientation of a real development
    # capture is rejected, without invoking inference or accessing holdout.
    first = names[0]
    hashes = list(records["val/"+first]["pixels"].values())
    bad = copy.deepcopy(plan)
    bad["known_training_canonical_pixel_sha256"] += [hashes[1]]
    try:
        capture_input(root/first, root, bad, set())
    except ValueError as exc:
        if "orientation" not in str(exc):
            raise
    else:
        raise AssertionError("Mirrored training overlap admitted")
    output = a.evidence/"development-evaluation.json"
    executed = subprocess.run(command+["--capture-root",str(root),"--model",str(a.weights),
                             "--holdout-manifest",str(path),"--output",str(output)], check=False)
    if not output.is_file():
        raise RuntimeError("Evaluator did not produce evidence")
    report = json.loads(output.read_text(encoding="utf-8"))
    if (report["model_sha256"] != CHECKPOINT or report["inference_method"] != descriptor
            or report["holdout"]["manifest_sha256"] != file_sha256(path)
            or report["holdout"]["plan"] != plan or report["production_detector_validated"] is not False
            or report["physical_output_allowed"] is not False):
        raise ValueError("Evaluation report identity mismatch")
    previous = {r["capture_name"].removeprefix("val/"):r for r in reference["records"]}
    rows = []
    for record in report["records"]:
        ref = previous[record["capture_name"]]
        if record["archive_sha256"] != ref["archive_sha256"] or set(record["views"]) != set(ref["views"]):
            raise ValueError("Comparison identity mismatch")
        for view,result in record["views"].items():
            old = ref["views"][view]["profiles"]["frame_exact_reuse"]
            a_tiles,b_tiles = result["tiles"],old["tiles"]
            rows.append({"capture":record["capture_name"],"view":view,
                "geometry_equal":boxes(result["predictions"])==boxes(old["predictions"]),
                "raw_geometry_equal":len(a_tiles)==len(b_tiles)==45 and all(
                    x["tile_index"]==y["tile_index"] and x["origin_xy"]==y["origin_xy"] and
                    boxes(x["local_predictions"])==boxes(y["local_predictions"]) for x,y in zip(a_tiles,b_tiles)),
                "scores_equal":result["score"]["by_kind"]==old["score"]["by_kind"],
                "unmapped_equal":boxes(result["unmapped_classes"])==boxes(old["unmapped_classes"]),
                "work_equal":result["work"]==old["work"],
                "exact_predictions_equal":result["predictions"]==old["predictions"],
                "latency_ms":result["prediction_latency_ms"]})
    parity = ("geometry_equal","raw_geometry_equal","scores_equal","unmapped_equal","work_equal")
    passed = len(rows)==64 and len({(r["capture"],r["view"]) for r in rows})==64 and all(all(r[k] for k in parity) for r in rows)
    write(a.evidence/"comparison.json",{"purpose":"development regression only","formal_holdout_used":False,
          "migration_authorized":False,"reference_artifact":15247099750,
          "mirrored_training_overlap_rejected":True,"returncode":executed.returncode,
          "parity_counts":{k:sum(r[k] for r in rows) for k in (*parity,"exact_predictions_equal")},
          "passed":passed and executed.returncode==0,"rows":rows})
    if not passed or executed.returncode != 0:
        raise SystemExit("Development reference non-regression failed; retain evidence")


if __name__ == "__main__":
    main()
