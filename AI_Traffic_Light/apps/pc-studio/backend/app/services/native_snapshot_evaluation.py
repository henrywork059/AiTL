"""Evaluate one freshly generated native synthetic capture, offline palette control.

No user-supplied files, trained weights, holdout selection, live inference or
authority. Timings are measured for this invocation, not controller latency.
"""
from hashlib import sha256
from io import BytesIO
from time import perf_counter
from zipfile import ZipFile

from app.services.native_detector_validation import qualified_capture, palette_predictions, score_footprints


def evaluate_native_snapshot(archive: bytes) -> dict:
    started = perf_counter()
    with ZipFile(BytesIO(archive)) as capture:
        annotations, images, integrity = qualified_capture(capture)
    if not integrity["hash_manifest_verified"]:
        raise ValueError("Fresh native snapshot must have a verified hash manifest")
    views = {}
    for sid, content in images.items():
        start = perf_counter()
        predictions = palette_predictions(content)
        prediction_ms = (perf_counter() - start) * 1000
        views[sid] = {
            "truth": annotations["views"][sid], "predictions": predictions,
            "score": score_footprints(annotations["views"][sid], predictions, .5),
            "palette_prediction_ms": prediction_ms,
        }
    return {
        "schema_version": 1, "method": "exact_palette_components_not_trained_model",
        "provenance": annotations["provenance"], "coordinate_space": annotations["coordinate_space"],
        "epoch": annotations["epoch"], "generation": annotations["generation"],
        "tick": annotations["tick"], "layout_id": annotations["layout_id"],
        "capture_sha256": sha256(archive).hexdigest(), "capture_integrity": integrity,
        "iou_threshold": .5, "confidence_threshold": None, "model_sha256": None,
        "views": views, "evaluation_ms": (perf_counter() - started) * 1000,
        "formal_holdout_used": False, "production_detector_validated": False,
        "physical_output_allowed": False, "migration_authorized": False,
        "limitations": "One current synthetic snapshot; four correlated mirrored views; full raster footprints; greedy same-class IoU. Palette timing excludes capture generation. Not trained-model accuracy, mAP, live latency, or field qualification.",
    }
