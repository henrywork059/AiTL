from __future__ import annotations

from dataclasses import dataclass, field
from math import hypot
from threading import RLock
from typing import Any, Callable
from time import time
from uuid import uuid4

from app.core.logging_config import get_logger
from app.services.traffic_flow import TrafficFlowService, traffic_flow_service
from app.services.intersection_network import intersection_network_service
from app.services.observation_identity import ObservationIdentity
from app.services.tracking_scope import TrackingContinuity, TrackingScope, TRACKING_MAX_GAP_MS
from app.services.zones import REFERENCE_HEIGHT, REFERENCE_WIDTH
from app.services.traffic_observations import (
    STATIONARY_RADIUS_REFERENCE_PX, STATIONARY_MIN_MS, observation_fields,
    selected_observation_is_current,
)

logger = get_logger(__name__)

MAX_MISSED_FRAMES = 4
VEHICLE_CLASSES = {"car", "bus", "truck", "motorcycle", "bicycle"}
TRACKED_CLASSES = VEHICLE_CLASSES | {"person"}


def _box_center(box: list[int] | tuple[int, int, int, int]) -> tuple[float, float]:
    x1, y1, x2, y2 = box
    return (float(x1) + float(x2)) / 2.0, (float(y1) + float(y2)) / 2.0


def _iou(a: list[int], b: list[int]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    intersection = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if intersection <= 0:
        return 0.0
    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
    union = area_a + area_b - intersection
    return intersection / union if union > 0 else 0.0


def _point_in_polygon(point: tuple[float, float], polygon: list[list[int]]) -> bool:
    if len(polygon) < 3:
        return False
    x, y = point
    inside = False
    px, py = polygon[-1]
    for cx, cy in polygon:
        if (cy > y) != (py > y):
            denominator = py - cy
            if denominator != 0:
                intersection_x = (px - cx) * (y - cy) / denominator + cx
                if x < intersection_x:
                    inside = not inside
        px, py = cx, cy
    return inside


def _orientation(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _movement_crosses_line(
    previous: tuple[float, float],
    current: tuple[float, float],
    line_a: tuple[float, float],
    line_b: tuple[float, float],
) -> bool:
    if previous == current or line_a == line_b:
        return False
    o1 = _orientation(previous, current, line_a)
    o2 = _orientation(previous, current, line_b)
    o3 = _orientation(line_a, line_b, previous)
    o4 = _orientation(line_a, line_b, current)
    epsilon = 1e-6
    return (o1 * o2 <= epsilon) and (o3 * o4 <= epsilon)


def _direction(previous: tuple[float, float], current: tuple[float, float]) -> str:
    dx = current[0] - previous[0]
    dy = current[1] - previous[1]
    if abs(dx) >= abs(dy):
        return "left_to_right" if dx >= 0 else "right_to_left"
    return "top_to_bottom" if dy >= 0 else "bottom_to_top"


def _reference_point(point: tuple[float, float], width: int, height: int) -> tuple[float, float]:
    return point[0] * REFERENCE_WIDTH / max(1, width), point[1] * REFERENCE_HEIGHT / max(1, height)


@dataclass
class Track:
    track_id: str
    class_id: int
    class_name: str
    box_xyxy: list[int]
    center: tuple[float, float]
    reference_center: tuple[float, float]
    first_seen_ms: int
    last_seen_ms: int
    first_frame_number: int
    last_frame_number: int
    age_frames: int = 1
    missed_frames: int = 0
    inside_regions: set[str] = field(default_factory=set)
    region_entered_at_ms: dict[str, int] = field(default_factory=dict)
    crossed_lines: set[str] = field(default_factory=set)
    stationary_anchor: tuple[float, float] | None = None
    stationary_since_ms: int = 0
    stationary_regions: set[str] = field(default_factory=set)

    def public(self) -> dict[str, Any]:
        return {
            "track_id": self.track_id,
            "class_id": self.class_id,
            "class_name": self.class_name,
            "box_xyxy": list(self.box_xyxy),
            "center_xy": [round(self.center[0], 1), round(self.center[1], 1)],
            "first_seen_ms": self.first_seen_ms,
            "last_seen_ms": self.last_seen_ms,
            "age_frames": self.age_frames,
            "missed_frames": self.missed_frames,
            "inside_regions": sorted(self.inside_regions),
            "stationary_regions": sorted(self.stationary_regions) if (
                self.missed_frames == 0 and self.last_seen_ms - self.stationary_since_ms >= STATIONARY_MIN_MS
            ) else [],
        }


class ObjectTrackingService:
    """Lightweight class-aware centroid/IoU tracker for prototype flow analytics."""

    def __init__(self, *, flow_service: TrafficFlowService | None = None,
                 intersection_resolver: Callable[[str], dict] | None = None,
                 clock_ms: Callable[[], int] = lambda: int(time() * 1000),
                 observation_validator: Callable[[ObservationIdentity], bool] | None = None) -> None:
        self._lock = RLock()
        self._flow_service = flow_service or traffic_flow_service
        self._intersection_resolver = intersection_resolver
        self._clock_ms = clock_ms
        self._observation_validator = observation_validator
        self._continuity = TrackingContinuity()
        self._live_timestamp: int | None = None
        self._session_tag = uuid4().hex[:6]
        self._counter = 0
        self._tracks: dict[str, Track] = {}
        self._last_source_id: str | None = None
        self._last_frame_number: int | None = None
        self._total_tracks_created = 0
        self._events_recorded = 0

    def reset_active(self) -> None:
        with self._lock:
            self._tracks.clear()
            self._last_source_id = None
            self._last_frame_number = None
            self._continuity.reset_active()
            self._live_timestamp = None

    def _scope_for(self, source_id: str, width: int, height: int,
                   observation: ObservationIdentity | None) -> TrackingScope:
        resolution = self._intersection_resolver(source_id) if self._intersection_resolver else {}
        junction = resolution.get("intersection_id") if resolution.get("source_mapping_matched") else None
        return TrackingScope(
            source_id, junction, width, height,
            observation.provenance if observation else None,
            observation.session_generation if observation else None,
            observation.source_epoch if observation else None,
            observation.mode_generation if observation else None,
        )

    def _empty_tracking_locked(self) -> dict[str, Any]:
        status = self._status_locked()
        status.update(active_track_count=0, active_vehicle_tracks=0,
                      active_pedestrian_tracks=0, last_source_id=None,
                      last_frame_number=None, tracks=[])
        return status

    def _without_tracking_locked(self, detection_frame: dict[str, Any]) -> dict[str, Any]:
        result = dict(detection_frame)
        result["detections"] = [
            {key: value for key, value in item.items() if key not in {"track_id", "track_age_frames"}}
            for item in detection_frame.get("detections", [])
        ]
        result["tracking"] = self._empty_tracking_locked()
        result["traffic_observation_identity"] = None
        return result

    def _expire_locked(self) -> None:
        if self._live_timestamp is not None and not 0 <= self._clock_ms() - self._live_timestamp <= TRACKING_MAX_GAP_MS:
            self.reset_active()

    def update(self, detection_frame: dict[str, Any], zones: list[dict[str, Any]], *,
               observation: ObservationIdentity | None = None) -> dict[str, Any]:
        source_id = str(detection_frame.get("source_id") or "unknown")
        frame_number = int(detection_frame.get("source_frame_number") or 0)
        timestamp_ms = int(detection_frame.get("timestamp_ms") or 0)
        frame_key = (source_id, frame_number, timestamp_ms)
        width = int(detection_frame.get("image_width") or REFERENCE_WIDTH)
        height = int(detection_frame.get("image_height") or REFERENCE_HEIGHT)

        with self._lock:
            self._expire_locked()
            if observation is not None and (
                observation.frame_key != frame_key
                or (observation.width, observation.height) != (width, height)
                or not 0 <= self._clock_ms() - timestamp_ms <= TRACKING_MAX_GAP_MS
                or (self._observation_validator is not None and not self._observation_validator(observation))
            ):
                return self._without_tracking_locked(detection_frame)
            scope = self._scope_for(source_id, width, height, observation)
            decision = self._continuity.classify(scope, timestamp_ms, frame_number)
            if decision == "repeat":
                # Multiple callers may use different confidence thresholds on one frame.
                result = self._annotate_without_advancing(detection_frame, width=width, height=height)
                result["traffic_observation_identity"] = observation_fields(observation, scope) if observation else None
                return result
            if decision == "replay":
                # Never expose another source's tracks or count an old observation again.
                if scope != self._continuity.scope:
                    self.reset_active()
                return self._without_tracking_locked(detection_frame)
            if decision == "reset":
                self._tracks.clear()
            self._last_source_id = source_id
            self._last_frame_number = frame_number
            self._live_timestamp = timestamp_ms if observation is not None else None

            detections = [
                dict(detection)
                for detection in detection_frame.get("detections", [])
                if str(detection.get("class_name") or "") in TRACKED_CLASSES
                and isinstance(detection.get("box_xyxy"), (list, tuple))
                and len(detection.get("box_xyxy")) == 4
            ]
            assignments = self._assign(detections, width=width, height=height)
            matched_tracks: set[str] = set()
            events: list[dict[str, Any]] = []
            tracked_detections: list[dict[str, Any]] = []

            for detection_index, detection in enumerate(detections):
                box = [int(value) for value in detection["box_xyxy"]]
                center = _box_center(box)
                reference_center = _reference_point(center, width, height)
                track_id = assignments.get(detection_index)
                had_gap = False
                if track_id is None:
                    track = self._new_track(
                        detection=detection,
                        box=box,
                        center=center,
                        reference_center=reference_center,
                        timestamp_ms=timestamp_ms,
                        frame_number=frame_number,
                        zones=zones,
                    )
                    zone_by_id = {zone["id"]: zone for zone in zones}
                    for region_id in sorted(track.inside_regions):
                        zone = zone_by_id.get(region_id)
                        if zone is not None:
                            events.append(self._region_event(
                                track,
                                zone,
                                "region_entry",
                                timestamp_ms,
                                frame_number,
                                dwell_ms=None,
                            ))
                else:
                    track = self._tracks[track_id]
                    previous_reference = track.reference_center
                    previous_regions = set(track.inside_regions)
                    had_gap = track.missed_frames > 0
                    track.box_xyxy = box
                    track.center = center
                    track.reference_center = reference_center
                    track.last_seen_ms = timestamp_ms
                    track.last_frame_number = frame_number
                    track.age_frames += 1
                    track.missed_frames = 0
                    events.extend(
                        self._events_for_move(
                            track,
                            previous_reference=previous_reference,
                            previous_regions=previous_regions,
                            zones=zones,
                            timestamp_ms=timestamp_ms,
                            frame_number=frame_number,
                        )
                    )
                if (track.stationary_anchor is None or had_gap
                    or hypot(reference_center[0] - track.stationary_anchor[0],
                             reference_center[1] - track.stationary_anchor[1]) > STATIONARY_RADIUS_REFERENCE_PX):
                    track.stationary_anchor = reference_center
                    track.stationary_since_ms = timestamp_ms
                    track.stationary_regions = set(track.inside_regions)
                else:
                    track.stationary_regions.intersection_update(track.inside_regions)
                matched_tracks.add(track.track_id)
                enriched = dict(detection)
                enriched["track_id"] = track.track_id
                enriched["track_age_frames"] = track.age_frames
                tracked_detections.append(enriched)

            for track_id, track in list(self._tracks.items()):
                if track_id in matched_tracks:
                    continue
                track.missed_frames += 1
                if track.missed_frames > MAX_MISSED_FRAMES:
                    self._tracks.pop(track_id, None)

            identity = observation_fields(observation, scope) if observation else None
            if identity is not None:
                if self._observation_validator is not None and not self._observation_validator(observation):
                    self.reset_active()
                    return self._without_tracking_locked(detection_frame)
                events = [{**event, **identity} for event in events]
            self._events_recorded += self._flow_service.record_events(events)
            result = dict(detection_frame)
            # Keep untracked classes in the frame while adding IDs only to supported traffic classes.
            by_detection_id = {str(item.get("id")): item for item in tracked_detections}
            result["detections"] = [
                by_detection_id.get(str(item.get("id")), dict(item))
                for item in detection_frame.get("detections", [])
            ]
            result["tracking"] = self._status_locked()
            result["traffic_observation_identity"] = identity
            return self._copy_result(result)


    def _annotate_without_advancing(
        self,
        detection_frame: dict[str, Any],
        *,
        width: int,
        height: int,
    ) -> dict[str, Any]:
        supported: list[dict[str, Any]] = []
        supported_positions: list[int] = []
        original = [dict(item) for item in detection_frame.get("detections", [])]
        for position, detection in enumerate(original):
            if (
                str(detection.get("class_name") or "") in TRACKED_CLASSES
                and isinstance(detection.get("box_xyxy"), (list, tuple))
                and len(detection.get("box_xyxy")) == 4
            ):
                supported.append(detection)
                supported_positions.append(position)

        assignments = self._assign(supported, width=width, height=height)
        for detection_index, track_id in assignments.items():
            position = supported_positions[detection_index]
            track = self._tracks.get(track_id)
            if track is None:
                continue
            original[position]["track_id"] = track.track_id
            original[position]["track_age_frames"] = track.age_frames

        result = dict(detection_frame)
        result["detections"] = original
        result["tracking"] = self._status_locked()
        return self._copy_result(result)

    def status(self) -> dict[str, Any]:
        with self._lock:
            self._expire_locked()
            return self._status_locked()

    def status_for_observation(self, observation: ObservationIdentity | None) -> dict[str, Any]:
        """Project only tracks belonging to the currently selected, fresh scope."""
        with self._lock:
            self._expire_locked()
            if observation is None or not 0 <= self._clock_ms() - observation.received_at_ms <= TRACKING_MAX_GAP_MS:
                return self._empty_tracking_locked()
            scope = self._scope_for(observation.source_id, observation.width, observation.height, observation)
            if scope != self._continuity.scope or (
                self._observation_validator is not None and not self._observation_validator(observation)
            ):
                return self._empty_tracking_locked()
            return self._status_locked()

    def _status_locked(self) -> dict[str, Any]:
        active = [track.public() for track in self._tracks.values() if track.missed_frames <= MAX_MISSED_FRAMES]
        active.sort(key=lambda item: item["track_id"])
        return {
            "session_id": self._session_tag,
            "active_track_count": len(active),
            "active_vehicle_tracks": sum(1 for item in active if item["class_name"] in VEHICLE_CLASSES),
            "active_pedestrian_tracks": sum(1 for item in active if item["class_name"] == "person"),
            "total_tracks_created": self._total_tracks_created,
            "events_recorded": self._events_recorded,
            "last_source_id": self._last_source_id,
            "last_frame_number": self._last_frame_number,
            "tracks": active,
            "prototype_tracker": "centroid_iou_v1",
        }

    def _assign(self, detections: list[dict[str, Any]], *, width: int, height: int) -> dict[int, str]:
        max_distance = max(45.0, hypot(width, height) * 0.11)
        candidates: list[tuple[float, int, str]] = []
        for detection_index, detection in enumerate(detections):
            box = [int(value) for value in detection["box_xyxy"]]
            center = _box_center(box)
            class_name = str(detection.get("class_name") or "")
            for track_id, track in self._tracks.items():
                if track.class_name != class_name or track.missed_frames > MAX_MISSED_FRAMES:
                    continue
                distance = hypot(center[0] - track.center[0], center[1] - track.center[1])
                overlap = _iou(box, track.box_xyxy)
                if distance <= max_distance or overlap >= 0.10:
                    score = distance - overlap * max_distance * 0.75 + track.missed_frames * 20.0
                    candidates.append((score, detection_index, track_id))
        assignments: dict[int, str] = {}
        used_tracks: set[str] = set()
        for _, detection_index, track_id in sorted(candidates, key=lambda item: item[0]):
            if detection_index in assignments or track_id in used_tracks:
                continue
            assignments[detection_index] = track_id
            used_tracks.add(track_id)
        return assignments

    def _new_track(
        self,
        *,
        detection: dict[str, Any],
        box: list[int],
        center: tuple[float, float],
        reference_center: tuple[float, float],
        timestamp_ms: int,
        frame_number: int,
        zones: list[dict[str, Any]],
    ) -> Track:
        self._counter += 1
        track_id = f"trk_{self._session_tag}_{self._counter:05d}"
        inside_regions = {
            zone["id"]
            for zone in zones
            if zone.get("type") not in {"ignore", "counting_line"}
            and _point_in_polygon(reference_center, zone.get("polygon", []))
        }
        track = Track(
            track_id=track_id,
            class_id=int(detection.get("class_id") or 0),
            class_name=str(detection.get("class_name") or "unknown"),
            box_xyxy=box,
            center=center,
            reference_center=reference_center,
            first_seen_ms=timestamp_ms,
            last_seen_ms=timestamp_ms,
            first_frame_number=frame_number,
            last_frame_number=frame_number,
            inside_regions=inside_regions,
            region_entered_at_ms={region_id: timestamp_ms for region_id in inside_regions},
        )
        self._tracks[track_id] = track
        self._total_tracks_created += 1
        return track

    def _events_for_move(
        self,
        track: Track,
        *,
        previous_reference: tuple[float, float],
        previous_regions: set[str],
        zones: list[dict[str, Any]],
        timestamp_ms: int,
        frame_number: int,
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        current_regions = {
            zone["id"]
            for zone in zones
            if zone.get("type") not in {"ignore", "counting_line"}
            and _point_in_polygon(track.reference_center, zone.get("polygon", []))
        }
        zone_by_id = {zone["id"]: zone for zone in zones}

        for region_id in sorted(current_regions - previous_regions):
            zone = zone_by_id[region_id]
            track.region_entered_at_ms[region_id] = timestamp_ms
            events.append(self._region_event(track, zone, "region_entry", timestamp_ms, frame_number, dwell_ms=None))
        for region_id in sorted(previous_regions - current_regions):
            zone = zone_by_id.get(region_id)
            if zone is None:
                continue
            entered_at = track.region_entered_at_ms.pop(region_id, track.first_seen_ms)
            dwell_ms = max(0, timestamp_ms - entered_at)
            events.append(self._region_event(track, zone, "region_exit", timestamp_ms, frame_number, dwell_ms=dwell_ms))
        track.inside_regions = current_regions

        for zone in zones:
            if zone.get("type") != "counting_line" or zone["id"] in track.crossed_lines:
                continue
            points = zone.get("polygon", [])
            if len(points) != 2:
                continue
            line_a = (float(points[0][0]), float(points[0][1]))
            line_b = (float(points[1][0]), float(points[1][1]))
            if _movement_crosses_line(previous_reference, track.reference_center, line_a, line_b):
                direction = _direction(previous_reference, track.reference_center)
                event_id = f"{track.track_id}:line:{zone['id']}"
                events.append(
                    {
                        "event_id": event_id,
                        "event_type": "line_crossing",
                        "timestamp_ms": timestamp_ms,
                        "source_frame_number": frame_number,
                        "track_id": track.track_id,
                        "class_id": track.class_id,
                        "class_name": track.class_name,
                        "line_id": zone["id"],
                        "line_label": zone.get("label", zone["id"]),
                        "direction": direction,
                        "x": round(track.reference_center[0], 1),
                        "y": round(track.reference_center[1], 1),
                    }
                )
                track.crossed_lines.add(zone["id"])
        return events

    @staticmethod
    def _region_event(
        track: Track,
        zone: dict[str, Any],
        event_type: str,
        timestamp_ms: int,
        frame_number: int,
        *,
        dwell_ms: int | None,
    ) -> dict[str, Any]:
        event = {
            "event_id": f"{track.track_id}:{event_type}:{zone['id']}:{frame_number}",
            "event_type": event_type,
            "timestamp_ms": timestamp_ms,
            "source_frame_number": frame_number,
            "track_id": track.track_id,
            "class_id": track.class_id,
            "class_name": track.class_name,
            "region_id": zone["id"],
            "region_label": zone.get("label", zone["id"]),
            "region_type": zone.get("type", "region"),
            "x": round(track.reference_center[0], 1),
            "y": round(track.reference_center[1], 1),
        }
        if dwell_ms is not None:
            event["dwell_ms"] = dwell_ms
        return event

    @staticmethod
    def _copy_result(result: dict[str, Any]) -> dict[str, Any]:
        copied = dict(result)
        copied["detections"] = [dict(item) for item in result.get("detections", [])]
        if isinstance(result.get("tracking"), dict):
            tracking = dict(result["tracking"])
            tracking["tracks"] = [dict(item) for item in tracking.get("tracks", [])]
            copied["tracking"] = tracking
        return copied


object_tracking_service = ObjectTrackingService(
    intersection_resolver=intersection_network_service.resolve_source,
    observation_validator=selected_observation_is_current,
)
