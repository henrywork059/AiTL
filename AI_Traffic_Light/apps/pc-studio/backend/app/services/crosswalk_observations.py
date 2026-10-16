"""Map fresh per-camera model detections into physical Crosswalk region observations.

Regions have separate Side A/B polygons. This adapter measures class occupancy;
it never infers queue, walking speed, or pedestrian crossing direction from a box.
"""
from __future__ import annotations

import time
from typing import Any

from app.services.traffic_logic import point_in_polygon
from app.services.zones import REFERENCE_WIDTH, REFERENCE_HEIGHT

MAX_FRAME_AGE_MS = 5000
MAX_SIDE_SKEW_MS = 2000


def _valid_frame(
    snapshot: dict[str, Any] | None, source_id: str, model_id: str | None, now_ms: int,
) -> dict[str, Any] | None:
    if not snapshot or snapshot.get("error") or not model_id or snapshot.get("model_id") != model_id:
        return None
    frame = snapshot.get("frame")
    if not isinstance(frame, dict) or frame.get("source_id") != source_id:
        return None
    timestamp = frame.get("timestamp_ms")
    if not isinstance(timestamp, (int, float)) or not 0 <= now_ms - timestamp <= MAX_FRAME_AGE_MS:
        return None
    if not isinstance(frame.get("detections"), list):
        return None
    return frame


def _side_polygon(region: dict[str, Any], side: str) -> list[list[int]] | None:
    if region.get("camera_side") not in (None, side):
        return None
    polygons = region.get("vertices_by_side")
    if isinstance(polygons, dict):
        return polygons.get(side)  # A region defined on only one side is not copied to the other.
    return region.get("vertices")  # Legacy region without side-specific polygons.


def _class_counts(frame: dict[str, Any], regions: list[tuple[str, list[list[int]]]]) -> dict[str, dict[str, int]]:
    counts = {region_id: {} for region_id, _ in regions}
    width = max(1, int(frame.get("image_width") or REFERENCE_WIDTH))
    height = max(1, int(frame.get("image_height") or REFERENCE_HEIGHT))
    for detected in frame["detections"]:
        try:
            x1, _, x2, y2 = detected["box_xyxy"]
            foot = ((float(x1) + float(x2)) * REFERENCE_WIDTH / (2 * width), float(y2) * REFERENCE_HEIGHT / height)
            label = str(detected.get("class_name") or "").strip()
            if not label:
                continue
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            continue
        # Overlapping polygons must not count the same detection twice on one camera.
        for region_id, polygon in regions:
            if point_in_polygon(foot, polygon):
                per_class = counts[region_id]
                per_class[label] = per_class.get(label, 0) + 1
                break
    return counts


def crosswalk_observation(
    crosswalk: dict[str, Any], snapshots: dict[str, dict[str, Any]],
    *, model_id: str | None, now_ms: int | None = None,
) -> tuple[dict[str, Any] | None, tuple[tuple[Any, ...], ...], dict[str, Any]]:
    """Return one class-only observation and frame signature for a crosswalk.

    Both camera views of the same region are averaged per class. A single
    available or single defined view uses its own count. Unsynchronised views
    use only the newest frame to avoid mixing distant points in time.
    """
    now_ms = int(time.time() * 1000) if now_ms is None else now_ms
    views: list[tuple[str, str, dict[str, Any], list[tuple[str, list[list[int]]]]]] = []
    configured = 0
    for side in ("a", "b"):
        source_id = crosswalk.get("camera_side_" + side + "_id")
        if not source_id:
            continue
        configured += 1
        frame = _valid_frame(snapshots.get(source_id), source_id, model_id, now_ms)
        if frame is None:
            continue
        regions = [(item["id"], polygon) for item in crosswalk["regions"]
                   if (polygon := _side_polygon(item, side)) is not None]
        if regions:
            views.append((side, source_id, frame, regions))

    if len(views) == 2 and abs(views[0][2]["timestamp_ms"] - views[1][2]["timestamp_ms"]) > MAX_SIDE_SKEW_MS:
        views = [max(views, key=lambda item: item[2]["timestamp_ms"])]

    if not views:
        return None, (), {"observation_provenance": "unavailable", "camera_sources": [],
                          "camera_coverage": "unavailable", "region_class_counts": {}}

    samples: dict[str, list[dict[str, int]]] = {}
    signature: list[tuple[Any, ...]] = []
    for side, source, frame, polygons in views:
        for region_id, classes in _class_counts(frame, polygons).items():
            samples.setdefault(region_id, []).append(classes)
        signature.append((source, frame["source_frame_number"], frame["timestamp_ms"], model_id))

    combined: dict[str, dict[str, float]] = {}
    for region_id, observations in samples.items():
        classes = set().union(*(counts.keys() for counts in observations))
        combined[region_id] = {
            name: round(sum(view.get(name, 0) for view in observations) / len(observations), 2)
            for name in classes
        }
    sources = [source for _, source, _, _ in views]
    latest = max(view[2]["timestamp_ms"] for view in views)
    meta = {
        "observation_provenance": "camera_ai",
        "camera_sources": sources,
        "camera_coverage": "complete" if len(sources) == configured else "partial",
        "region_class_counts": combined,
        "source_timestamp_ms": latest,
    }
    observation = {
        "zone_class_counts": {**combined, **{crosswalk["id"] + ":" + rid: counts for rid, counts in combined.items()}},
        # Region polygons describe physical occupancy, not waiting or crossing roles.
        "available_metrics": [],
        "pedestrians_waiting": 0, "pedestrians_crossing": 0, "vehicles_waiting": 0,
        "source_timestamp_ms": latest,
        "source_frame_number": max(view[2]["source_frame_number"] for view in views),
        "data_source": "crosswalk_camera_ai",
    }
    return observation, tuple(sorted(signature)), meta
