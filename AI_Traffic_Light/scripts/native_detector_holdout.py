"""Explicit, offline synthetic holdout admission and non-authoritative verdicts."""
import hashlib
import json
import math
from pathlib import Path
import re

KINDS = ("vehicle", "pedestrian")
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def _digest(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("Expected lowercase SHA-256 digest")
    return value


def _unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("Duplicate manifest key")
        obj[key] = value
    return obj


def load_holdout(content, capture_names, model_digest, confidence, iou):
    """Check an operator-supplied plan; declarations are not authenticated facts."""
    plan = json.loads(content, object_pairs_hook=_unique_object)
    if not isinstance(plan, dict) or type(plan.get("schema_version")) is not int or plan["schema_version"] != 1:
        raise ValueError("Unsupported holdout manifest")
    if _digest(plan.get("model_sha256")) != model_digest:
        raise ValueError("Holdout model digest mismatch")
    for key in ("model_provenance", "training_separation", "holdout_selection"):
        if not isinstance(plan.get(key), str) or not plan[key].strip():
            raise ValueError("Missing holdout declaration: " + key)
    for key, actual in (("confidence", confidence), ("iou_threshold", iou)):
        value = plan.get(key)
        if type(value) not in (int, float) or not 0 < value <= 1 or value != actual:
            raise ValueError("Holdout threshold mismatch: " + key)
    captures = plan.get("captures")
    if not isinstance(captures, dict) or not captures or set(captures) != set(capture_names):
        raise ValueError("Holdout capture set mismatch")
    for digest in captures.values():
        _digest(digest)
    training = plan.get("known_training_canonical_pixel_sha256")
    if not isinstance(training, list) or len(set(_digest(x) for x in training)) != len(training):
        raise ValueError("Invalid known training pixel digest list")
    criteria = plan.get("criteria")
    if not isinstance(criteria, dict) or set(criteria) != set(KINDS):
        raise ValueError("Both traffic kinds require predeclared criteria")
    for kind, rule in criteria.items():
        if not isinstance(rule, dict) or set(rule) != {"min_truth", "min_precision", "min_recall"}:
            raise ValueError("Invalid criteria for " + kind)
        if type(rule["min_truth"]) is not int or rule["min_truth"] < 1:
            raise ValueError("Positive integer support required")
        for key in ("min_precision", "min_recall"):
            if type(rule[key]) not in (int, float) or not 0 < rule[key] <= 1:
                raise ValueError("Positive precision/recall criteria required")
    return plan


def read_pinned_archive(path, expected):
    """Hash the exact bounded bytes subsequently consumed by ZipFile."""
    with Path(path).open("rb") as stream:
        content = stream.read(MAX_ARCHIVE_BYTES + 1)
    if len(content) > MAX_ARCHIVE_BYTES or sha256(content) != expected:
        raise ValueError("Holdout archive size or digest mismatch: " + str(path))
    return content


def admit_pixels(pixel_digest, seen, known_training):
    _digest(pixel_digest)
    if pixel_digest in seen or pixel_digest in known_training:
        raise ValueError("Duplicate holdout or known training canonical pixels")
    seen.add(pixel_digest)


def verdict(plan, views, expected_views):
    if set(views) != set(expected_views) or not views:
        raise ValueError("Incomplete holdout views")
    checks = {}
    for view, result in views.items():
        checks[view] = {}
        for kind in KINDS:
            counts = result["micro"][kind]
            rule = plan["criteria"][kind]
            precision, recall = counts["precision"], counts["recall"]
            checks[view][kind] = bool(
                counts["truth_count"] >= rule["min_truth"]
                and type(precision) in (int, float) and math.isfinite(precision)
                and rule["min_precision"] <= precision <= 1
                and type(recall) in (int, float) and math.isfinite(recall)
                and rule["min_recall"] <= recall <= 1
            )
    return {"criteria_met": all(all(row.values()) for row in checks.values()),
            "by_view_and_kind": checks, "criteria": plan["criteria"],
            "training_separation_independently_verified": False,
            "production_detector_validated": False,
            "migration_authorized": False}
