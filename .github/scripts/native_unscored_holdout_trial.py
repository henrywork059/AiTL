"""Freeze a new unscored synthetic detector cohort; no model or training access."""
import hashlib
import io
import json
from pathlib import Path
import sys
from zipfile import ZipFile
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "AI_Traffic_Light/apps/pc-studio/backend"))
from app.services.native_evaluation import NativeEvaluationService, MAX_BATCH
from app.services.native_detector_validation import qualified_capture
from app.services.sumo_projection import VIEW_FLIPS
from native_reference_detector_trial import CAPTURES

# Fixed before model evaluation. Separate scenario seeds from historical cohort.
ARMS = ((101, "light", "midblock_compact", "fixed"),
        (211, "normal", "midblock", "adaptive"),
        (307, "busy", "midblock_wide", "fixed"))
TICKS = (125, 375)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run(root):
    root.mkdir(parents=True, exist_ok=False)
    historical = {pair[1] for pair in CAPTURES.values()}
    seen = set()
    records = {}
    for seed, density, geometry, mode in ARMS:
        service = NativeEvaluationService(enabled=True)
        try:
            state = service.start(epoch=service.epoch, generation=service.generation,
                                  seed=seed, density=density, geometry=geometry, mode=mode)
            identity = {k: state[k] for k in ("epoch", "generation")}
            tick = 0
            for target in TICKS:
                while tick < target:
                    steps = min(MAX_BATCH, target - tick)
                    service.step(**identity, tick=tick, steps=steps, _return_scene=False)
                    tick += steps
                raw = service.capture(**identity, tick=tick)
                with ZipFile(io.BytesIO(raw)) as z:
                    annotations, images, integrity = qualified_capture(z)
                if not integrity["hash_manifest_verified"] or annotations["tick"] != target:
                    raise ValueError("Capture identity or integrity invalid")
                image = cv2.imdecode(np.frombuffer(images[next(iter(VIEW_FLIPS))], np.uint8), cv2.IMREAD_COLOR)
                pixel_hash = sha(image.tobytes())
                if pixel_hash in historical or pixel_hash in seen:
                    raise ValueError("Duplicate or historical overlap in predeclared cohort")
                seen.add(pixel_hash)
                relative = f"{seed}-{density}-{geometry}-{mode}-tick{tick}/capture.zip"
                path = root / relative
                path.parent.mkdir(parents=True)
                path.write_bytes(raw)
                records[relative] = {"archive_sha256": sha(raw), "canonical_pixel_sha256": pixel_hash,
                                     "seed": seed, "density": density, "geometry": geometry, "mode": mode,
                                     "tick": tick, "layout_id": annotations["layout_id"],
                                     "truth_support": {v: {kind: sum(r["kind"] == kind for r in rows)
                                                           for kind in ("vehicle", "pedestrian")}
                                                       for v, rows in annotations["views"].items()}}
        finally:
            service.close()
    if len(records) != len(ARMS) * len(TICKS):
        raise ValueError("Incomplete frozen cohort")
    (root / "cohort.json").write_text(json.dumps({
        "schema_version": 1, "evidence_class": "executed_synthetic_unscored_capture",
        "selection": {"arms": ARMS, "ticks": TICKS, "step_seconds": .2},
        "historical_canonical_pixel_sha256": sorted(historical),
        "captures": records, "model_evaluated": False, "acceptance_criteria": None,
        "training_separation_independently_verified": False,
        "production_detector_validated": False, "migration_authorized": False,
        "limitations": "Frames within a seed and four mirrored views are correlated; distinct hashes do not establish training separation.",
    }, indent=2), encoding="utf-8")
    print(f"Frozen {len(records)} distinct unscored captures; no holdout performance claim")


if __name__ == "__main__":
    run(Path(sys.argv[1]))
