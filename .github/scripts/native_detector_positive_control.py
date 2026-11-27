"""Positive control for reference checkpoint and production result conversion (offline)."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

import cv2
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "AI_Traffic_Light/apps/pc-studio/backend"))
from app.services.camera_frames import CameraFrame
from app.services.inference import InferenceService
from native_reference_detector_trial import MODEL_SHA

PHOTO_GIT_BLOB = "40eaaf5c330d0c498fbe1dcacf9bb8bf566797fe"
PHOTO_COMMIT = "6e43d1e1e5db72afbf686dee6745669bcb124b0a"


def run(model_path, photo_path, output):
    model_bytes = model_path.read_bytes()
    if hashlib.sha256(model_bytes).hexdigest() != MODEL_SHA:
        raise ValueError("Reference checkpoint hash mismatch")
    photo = photo_path.read_bytes()
    blob = hashlib.sha1(b"blob " + str(len(photo)).encode() + b"\0" + photo).hexdigest()
    if blob != PHOTO_GIT_BLOB or len(photo) != 137419:
        raise ValueError("Positive-control photo identity mismatch")
    from ultralytics import YOLO
    model = YOLO(str(model_path))
    if model.task != "detect":
        raise ValueError("Expected detector")
    image = cv2.imdecode(np.frombuffer(photo, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Unreadable photo")
    height, width = image.shape[:2]
    frame = CameraFrame(content=photo, content_type="image/jpeg", source_id="offline_photo_control",
                        width=width, height=height, received_at_ms=0, frame_number=0, origin="upload")
    start = perf_counter()
    results = model.predict(source=image, conf=.1, verbose=False, device="cpu", save=False)
    elapsed = (perf_counter() - start) * 1000
    result = results[0]
    raw = [{"class_id": int(c), "class_name": str(result.names[int(c)]),
            "confidence": float(s), "box_xyxy": [float(x) for x in box]}
           for box, s, c in zip(result.boxes.xyxy.cpu().tolist(),
                                result.boxes.conf.cpu().tolist(), result.boxes.cls.cpu().tolist(), strict=True)]
    converted = InferenceService._convert_results(frame, results, model)["detections"]
    # Independent conversion check: exact round-to-integer and image clipping.
    expected = []
    for row in raw:
        b = [max(0, min(limit, round(x))) for x, limit in zip(row["box_xyxy"], (width, height, width, height))]
        if b[2] > b[0] and b[3] > b[1]:
            expected.append({**row, "box_xyxy": b})
    projected = [{k: row[k] for k in ("class_id", "class_name", "confidence", "box_xyxy")} for row in converted]
    names = {row["class_name"] for row in converted}
    matched = expected == projected
    passed = matched and {"bus", "person"} <= names
    output.write_text(json.dumps({
        "model_sha256": MODEL_SHA, "photo_git_blob": blob, "photo_commit": PHOTO_COMMIT,
        "photo_sha256": hashlib.sha256(photo).hexdigest(), "image_size": [width, height],
        "confidence": .1, "latency_ms": elapsed, "raw_predictions": raw,
        "converted_predictions": converted, "conversion_matches": matched,
        "positive_control_passed": passed, "production_detector_validated": False,
        "migration_authorized": False,
        "limitations": "Known publisher sample, not a holdout, accuracy estimate, or live pipeline test."
    }, indent=2, allow_nan=False), encoding="utf-8")
    if not passed:
        raise ValueError("Positive control or coordinate conversion failed; retain report")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--photo", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    run(a.model, a.photo, a.output)
