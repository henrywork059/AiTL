"""Isolated native raster adaptation experiment; never a managed/live detector."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
from zipfile import ZipFile

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2] / "AI_Traffic_Light"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "apps/pc-studio/backend"))
from native_detector_batch import evaluate, file_sha256
from app.services.native_detector_validation import qualified_capture
from app.services.sumo_projection import VIEW_FLIPS, WIDTH, HEIGHT

# Historical and reserved cohort canonical pixels. Every orientation is
# compared to these hashes, so exact mirrors cannot bypass exclusion.
RESERVED = frozenset("""
3236f423921b06168f40ee17cecad39b97c06369f79cf3f11e0995601949888b
48242e483f62c6474716f05d21f9ef125a4b525aeda2190c615d5d1ae316f10b
5d6dc02ed78325717911f6427391d0b7e166b8a5a81fcd671411ef40f8b74258
61b073e503e7cc9d244015b30e1253ee40bce40a50daa17b2cff72381de80034
77cd583b30b8a7cef26ef1765d2b180f2aa7dd72ca32cc5a379cbe72982805cd
08eaf73a5dfc9c484f6ac4be130b135ef524a69c5836bc8941e867517367086f
2e9e8b6a24b9ccae6d423fd26fa4d7d5322be31fb009e6ce4c2dddc53c13b125
a890fd50ce0f3f57dffc1fc385ce1a7e85c7e73167764222eeba3f8b44dab6f5
0c920b50359735e0a4fa0b23b0de4ebf4ab6ea80c0f1941b942a851f5e461d58
0992b5f4fbb946991ec476f7727519bff6b2683d0399521b52a9a610130de969
055aa77d9a249c39b526d04f33f12a94fb7599ddee2ab9ce4fc689fcbcca5f2f
""".split())
ARMS = (("train",401,"light","midblock_compact","adaptive"),
        ("train",503,"normal","midblock","fixed"),
        ("train",607,"busy","midblock_wide","adaptive"),
        ("val",709,"normal","midblock_compact","fixed"),
        ("val",811,"busy","midblock","adaptive"))
TICKS = (50,125,200,275,350,425,500,575)
KINDS = ("vehicle", "pedestrian")
MODEL_SHA = "0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1"
SETTINGS = dict(epochs=6, imgsz=640, batch=8, device="cpu", workers=0,
                seed=20261128, deterministic=True, optimizer="AdamW", lr0=.001,
                patience=0, amp=False, plots=False, save=True, cache=False,
                mosaic=0., mixup=0., fliplr=0., flipud=0., degrees=0.,
                translate=0., scale=0., shear=0., perspective=0.,
                hsv_h=0., hsv_s=0., hsv_v=0.)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False), encoding="utf-8")


def expected():
    return {f"{split}/{seed}-{density}-{geometry}-{mode}-{tick}/capture.zip":
            (split, seed, density, geometry, mode, tick)
            for split, seed, density, geometry, mode in ARMS for tick in TICKS}


def inspect_capture(raw, tick):
    with ZipFile(io.BytesIO(raw)) as z:
        annotations, images, integrity = qualified_capture(z)
    if not integrity["hash_manifest_verified"] or annotations["tick"] != tick:
        raise ValueError("Unqualified capture or tick")
    hashes = {}
    for view in VIEW_FLIPS:
        image = cv2.imdecode(np.frombuffer(images[view], np.uint8), cv2.IMREAD_COLOR)
        hashes[view] = sha(image.tobytes())
    return annotations, images, hashes


def admit(hashes, split, seen):
    values = set(hashes.values())
    if values & RESERVED:
        raise ValueError("Historical or reserved holdout overlap")
    if values & seen["val" if split == "train" else "train"]:
        raise ValueError("Cross-split pixel overlap")
    # Reject duplicates instead of selecting favorable samples.
    if len(values) != len(VIEW_FLIPS) or values & seen[split]:
        raise ValueError("Duplicate development image")
    seen[split].update(values)


def generate(out):
    from app.services.native_evaluation import NativeEvaluationService, MAX_BATCH
    out.mkdir(parents=True, exist_ok=False)
    records = {}
    seen = {"train": set(), "val": set()}
    for split, seed, density, geometry, mode in ARMS:
        svc = NativeEvaluationService(enabled=True)
        try:
            state = svc.start(epoch=svc.epoch, generation=svc.generation,
                              seed=seed, density=density, geometry=geometry, mode=mode)
            ident = {k: state[k] for k in ("epoch", "generation")}
            tick = 0
            for target in TICKS:
                while tick < target:
                    step = min(MAX_BATCH, target-tick)
                    svc.step(**ident, tick=tick, steps=step, _return_scene=False)
                    tick += step
                raw = svc.capture(**ident, tick=tick)
                ann, _, hashes = inspect_capture(raw, tick)
                admit(hashes, split, seen)
                name = f"{split}/{seed}-{density}-{geometry}-{mode}-{tick}/capture.zip"
                path = out / name
                path.parent.mkdir(parents=True)
                path.write_bytes(raw)
                records[name] = {"archive_sha256": sha(raw), "pixels": hashes,
                                 "layout_id": ann["layout_id"]}
        finally:
            svc.close()
    if set(records) != set(expected()):
        raise ValueError("Incomplete development cohort")
    write_json(out / "manifest.json", {"records": records, "arms": ARMS, "ticks": TICKS,
               "reserved_canonical_hashes": sorted(RESERVED), "formal_holdout_used": False})
    print(f"Generated {len(records)} native captures across disjoint scenario seeds")


def materialize(captures, dataset):
    manifest = json.loads((captures / "manifest.json").read_text(encoding="utf-8"))
    records = manifest["records"]
    if set(records) != set(expected()) or set(records) != {
        p.relative_to(captures).as_posix() for p in captures.rglob("capture.zip")
    } or set(manifest["reserved_canonical_hashes"]) != RESERVED:
        raise ValueError("Unexpected capture manifest")
    dataset.mkdir(parents=True, exist_ok=False)
    seen = {"train": set(), "val": set()}
    images_manifest = {}
    support = {split: {kind: 0 for kind in KINDS} for split in seen}
    for split in seen:
        (dataset / "images" / split).mkdir(parents=True)
        (dataset / "labels" / split).mkdir(parents=True)
    for name, (split, seed, density, geometry, mode, tick) in expected().items():
        raw = (captures / name).read_bytes()
        record = records[name]
        if sha(raw) != record["archive_sha256"]:
            raise ValueError("Development archive changed")
        ann, images, hashes = inspect_capture(raw, tick)
        if hashes != record["pixels"] or ann["layout_id"] != record["layout_id"]:
            raise ValueError("Development pixels or layout changed")
        admit(hashes, split, seen)
        for view, rows in ann["views"].items():
            stem = f"{seed}-{tick}-{view}"
            image_path = dataset / "images" / split / (stem + ".png")
            label_path = dataset / "labels" / split / (stem + ".txt")
            image_path.write_bytes(images[view])
            labels = []
            for row in rows:
                x1,y1,x2,y2 = row["box_xyxy"]
                if not (0 <= x1 < x2 <= WIDTH and 0 <= y1 < y2 <= HEIGHT):
                    raise ValueError("Invalid footprint")
                kind = row["kind"]
                support[split][kind] += 1
                labels.append(f"{KINDS.index(kind)} {(x1+x2)/(2*WIDTH):.10f} {(y1+y2)/(2*HEIGHT):.10f} {(x2-x1)/WIDTH:.10f} {(y2-y1)/HEIGHT:.10f}")
            label_path.write_text("\n".join(labels) + ("\n" if labels else ""), encoding="utf-8")
            images_manifest[image_path.relative_to(dataset).as_posix()] = {
                "image_sha256": file_sha256(image_path), "label_sha256": file_sha256(label_path),
                "pixel_sha256": hashes[view], "capture": name, "view": view, "seed": seed}
    if any(n == 0 for counts in support.values() for n in counts.values()):
        raise ValueError("Both kinds required in development splits")
    # This is deliberately not the production managed dataset builder.
    yaml = dataset / "data.yaml"
    yaml.write_text("path: " + json.dumps(dataset.resolve().as_posix()) +
                    "\ntrain: images/train\nval: images/val\nnames:\n  0: vehicle\n  1: pedestrian\n",
                    encoding="utf-8")
    return yaml, {"images": images_manifest, "support": support,
                  "formal_holdout_used": False, "training_separation_from_coco_verified": False}


def train(captures, work, weights, evidence):
    evidence.mkdir(parents=True, exist_ok=False)
    if file_sha256(weights) != MODEL_SHA:
        raise ValueError("Untrusted reference checkpoint")
    work.mkdir(parents=True, exist_ok=False)
    dataset = work / "dataset"
    yaml, manifest = materialize(captures, dataset)
    write_json(evidence / "dataset-manifest.json", manifest)
    write_json(evidence / "training-plan.json", {"settings": SETTINGS, "initial_model_sha256": MODEL_SHA,
               "selection": "fixed final epoch checkpoint; development split only",
               "formal_holdout_used": False, "production_detector_validated": False})
    from ultralytics import YOLO
    paths = sorted((captures / "val").rglob("capture.zip"))
    before = evaluate(paths, YOLO(str(weights)), .1, .5, captures)
    before["model_sha256"] = MODEL_SHA
    write_json(evidence / "before.json", before)
    model = YOLO(str(weights))
    model.train(data=str(yaml), project=str(work / "runs"), name="adaptation", **SETTINGS)
    run = Path(model.trainer.save_dir)
    last = run / "weights" / "last.pt"
    if not last.is_file():
        raise ValueError("Fixed final checkpoint missing")
    import csv
    with (run / "results.csv").open(newline="", encoding="utf-8") as stream:
        epochs = list(csv.DictReader(stream))
    if len(epochs) != SETTINGS["epochs"]:
        raise ValueError("Training did not complete all predeclared epochs")
    for filename in ("results.csv", "args.yaml"):
        shutil.copyfile(run / filename, evidence / filename)
    shutil.copyfile(last, evidence / "development-last.pt")
    digest = file_sha256(evidence / "development-last.pt")
    after = evaluate(paths, YOLO(str(evidence / "development-last.pt")), .1, .5, captures)
    after["model_sha256"] = digest
    write_json(evidence / "after.json", after)
    write_json(evidence / "summary.json", {"model_sha256": digest, "completed_epochs": len(epochs),
               "before": before["views"], "after": after["views"],
               "formal_holdout_used": False, "production_detector_validated": False,
               "migration_authorized": False,
               "limitations": "Development validation influenced training monitoring; not independent holdout. Full raster footprint labels may include occlusion. Synthetic-only checkpoint; never register in production."})


def self_test():
    assert len(RESERVED) == 11 and all(len(h) == 64 for h in RESERVED)
    assert len(expected()) == 40
    seen = {"train": set(), "val": set()}
    fake = {v: sha(v.encode()) for v in VIEW_FLIPS}
    admit(fake, "train", seen)
    for hashes, split in ((fake,"val"), (fake,"train"),
                          ({**fake, next(iter(fake)): next(iter(RESERVED))},"val")):
        try:
            admit(hashes, split, seen)
        except ValueError:
            pass
        else:
            raise AssertionError("Overlap guard failed")
    print("Development split/duplicate/reserved overlap negative controls passed")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("generate", "train", "self-test"))
    p.add_argument("--captures", type=Path)
    p.add_argument("--work", type=Path)
    p.add_argument("--weights", type=Path)
    p.add_argument("--evidence", type=Path)
    a = p.parse_args()
    if a.mode == "self-test":
        self_test()
    elif a.mode == "generate":
        generate(a.captures)
    else:
        train(a.captures, a.work, a.weights, a.evidence)
