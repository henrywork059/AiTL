from __future__ import annotations

import csv
from collections import Counter, defaultdict
from io import StringIO
import json
import os
from pathlib import Path
from threading import RLock
from time import time
from typing import Any

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.core.logging_config import get_logger

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_FLOW_PATH = PROJECT_ROOT / "outputs" / "traffic_flow" / "events.jsonl"
DEFAULT_MAX_EVENTS = 50_000
VEHICLE_CLASSES = {"car", "bus", "truck", "motorcycle", "bicycle"}


def _bounded_int_env(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, min(maximum, value))


class TrafficFlowService:
    """Persist track-derived line/region events as bounded runtime JSONL data."""

    def __init__(self, *, flow_path: Path | None = None, max_events: int | None = None) -> None:
        configured = os.environ.get("AITL_TRAFFIC_FLOW_PATH")
        self._flow_path = Path(configured) if configured else (flow_path or DEFAULT_FLOW_PATH)
        self._flow_path = self._flow_path.expanduser().resolve()
        self.max_events = max_events or _bounded_int_env(
            "AITL_TRAFFIC_FLOW_MAX_EVENTS",
            DEFAULT_MAX_EVENTS,
            minimum=500,
            maximum=500_000,
        )
        self._lock = RLock()
        self._known_event_ids: set[str] = set()
        self._append_count = 0

    @property
    def flow_path(self) -> Path:
        return self._flow_path

    def record_events(self, events: list[dict[str, Any]]) -> int:
        """Append new tracker events, deduplicating event IDs within the process."""
        if not events:
            return 0
        recorded = 0
        with self._lock:
            for event in events:
                event_id = str(event.get("event_id") or "")
                if not event_id or event_id in self._known_event_ids:
                    continue
                self._append(event)
                self._known_event_ids.add(event_id)
                recorded += 1
        return recorded

    def status(self) -> dict[str, Any]:
        records = self._read_all()
        return self._status_from_records(records)

    def _status_from_records(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "recording": True,
            "max_events": self.max_events,
            "stored_events": len(records),
            "flow_path": "outputs/traffic_flow/events.jsonl",
            "oldest_event_at_ms": int(records[0].get("timestamp_ms", 0)) if records else None,
            "newest_event_at_ms": int(records[-1].get("timestamp_ms", 0)) if records else None,
        }

    def query(
        self,
        *,
        zones: list[dict[str, Any]],
        minutes: int = 15,
        limit: int = 10_000,
        line_id: str | None = None,
        region_id: str | None = None,
        class_name: str | None = None,
    ) -> dict[str, Any]:
        lines = {zone["id"]: zone for zone in zones if zone.get("type") == "counting_line"}
        regions = {
            zone["id"]: zone
            for zone in zones
            if zone.get("type") not in {"ignore", "counting_line"}
        }
        if line_id is not None and line_id not in lines:
            raise AppError(
                ErrorCode.ZONE_NOT_FOUND,
                "The requested counting line was not found.",
                status_code=404,
                details={"line_id": line_id},
            )
        if region_id is not None and region_id not in regions:
            raise AppError(
                ErrorCode.ZONE_NOT_FOUND,
                "The requested analytics region was not found.",
                status_code=404,
                details={"region_id": region_id},
            )

        all_records = self._read_all()
        records = all_records
        if minutes > 0:
            cutoff_ms = int(time() * 1000) - minutes * 60_000
            records = [record for record in records if int(record.get("timestamp_ms", 0)) >= cutoff_ms]
        if line_id is not None:
            records = [record for record in records if record.get("line_id") == line_id]
        if region_id is not None:
            records = [record for record in records if record.get("region_id") == region_id]
        if class_name is not None:
            records = [record for record in records if record.get("class_name") == class_name]
        if limit > 0 and len(records) > limit:
            records = records[-limit:]

        return {
            **self._status_from_records(all_records),
            "minutes": minutes,
            "filters": {"line_id": line_id, "region_id": region_id, "class_name": class_name},
            "lines": [
                {"id": zone["id"], "label": zone["label"]}
                for zone in lines.values()
            ],
            "regions": [
                {"id": zone["id"], "label": zone["label"], "type": zone["type"]}
                for zone in regions.values()
            ],
            "events": records,
            "buckets": self._minute_buckets(records),
            "summary": self._summary(records),
        }

    def export_csv(
        self,
        *,
        zones: list[dict[str, Any]],
        minutes: int = 15,
        limit: int = 50_000,
        line_id: str | None = None,
        region_id: str | None = None,
        class_name: str | None = None,
    ) -> str:
        data = self.query(
            zones=zones,
            minutes=minutes,
            limit=limit,
            line_id=line_id,
            region_id=region_id,
            class_name=class_name,
        )
        output = StringIO()
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow([
            "event_id",
            "timestamp_ms",
            "source_frame_number",
            "track_id",
            "class_id",
            "class_name",
            "event_type",
            "line_id",
            "line_label",
            "region_id",
            "region_label",
            "region_type",
            "direction",
            "dwell_ms",
            "x",
            "y",
        ])
        for event in data["events"]:
            writer.writerow([
                event.get("event_id", ""),
                event.get("timestamp_ms", ""),
                event.get("source_frame_number", ""),
                event.get("track_id", ""),
                event.get("class_id", ""),
                event.get("class_name", ""),
                event.get("event_type", ""),
                event.get("line_id", ""),
                event.get("line_label", ""),
                event.get("region_id", ""),
                event.get("region_label", ""),
                event.get("region_type", ""),
                event.get("direction", ""),
                event.get("dwell_ms", ""),
                event.get("x", ""),
                event.get("y", ""),
            ])
        return output.getvalue()

    def clear(self) -> dict[str, Any]:
        with self._lock:
            removed = 0
            if self._flow_path.is_file():
                try:
                    removed = sum(1 for line in self._flow_path.read_text(encoding="utf-8").splitlines() if line.strip())
                    self._flow_path.unlink()
                except OSError as exc:
                    logger.exception("Traffic flow clear failed", extra={"error_code": ErrorCode.TRAFFIC_FLOW_CLEAR_FAILED.value})
                    raise AppError(
                        ErrorCode.TRAFFIC_FLOW_CLEAR_FAILED,
                        "Failed to clear traffic flow events.",
                        status_code=500,
                    ) from exc
            self._known_event_ids.clear()
            self._append_count = 0
        logger.info("Traffic flow history cleared", extra={"removed_events": removed})
        return {"cleared": True, "removed_events": removed, **self.status()}

    @staticmethod
    def _minute_buckets(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        buckets: dict[int, dict[str, Any]] = {}
        for event in records:
            timestamp_ms = int(event.get("timestamp_ms", 0))
            bucket_ms = (timestamp_ms // 60_000) * 60_000
            bucket = buckets.setdefault(
                bucket_ms,
                {
                    "bucket_start_ms": bucket_ms,
                    "line_crossings": 0,
                    "vehicles": 0,
                    "pedestrians": 0,
                    "region_entries": 0,
                    "region_exits": 0,
                },
            )
            event_type = event.get("event_type")
            class_name = str(event.get("class_name") or "")
            if event_type == "line_crossing":
                bucket["line_crossings"] += 1
                if class_name == "person":
                    bucket["pedestrians"] += 1
                elif class_name in VEHICLE_CLASSES:
                    bucket["vehicles"] += 1
            elif event_type == "region_entry":
                bucket["region_entries"] += 1
            elif event_type == "region_exit":
                bucket["region_exits"] += 1
        return [buckets[key] for key in sorted(buckets)]

    @staticmethod
    def _summary(records: list[dict[str, Any]]) -> dict[str, Any]:
        crossings = [event for event in records if event.get("event_type") == "line_crossing"]
        entries = [event for event in records if event.get("event_type") == "region_entry"]
        exits = [event for event in records if event.get("event_type") == "region_exit"]
        vehicles = [event for event in crossings if event.get("class_name") in VEHICLE_CLASSES]
        pedestrians = [event for event in crossings if event.get("class_name") == "person"]
        directions = Counter(str(event.get("direction") or "unknown") for event in crossings)
        line_counts = Counter(str(event.get("line_id") or "unknown") for event in crossings)
        dwell_values = [int(event.get("dwell_ms", 0)) for event in exits if int(event.get("dwell_ms", 0)) >= 0]
        pedestrian_waits = [
            int(event.get("dwell_ms", 0))
            for event in exits
            if event.get("region_type") == "pedestrian_waiting"
            and event.get("class_name") == "person"
            and int(event.get("dwell_ms", 0)) >= 0
        ]
        per_region_dwell: dict[str, list[int]] = defaultdict(list)
        for event in exits:
            region_id = str(event.get("region_id") or "")
            if region_id and event.get("dwell_ms") is not None:
                per_region_dwell[region_id].append(int(event.get("dwell_ms") or 0))
        return {
            "unique_passages": len(crossings),
            "unique_vehicle_passages": len(vehicles),
            "unique_pedestrian_passages": len(pedestrians),
            "region_entries": len(entries),
            "region_exits": len(exits),
            "average_dwell_ms": round(sum(dwell_values) / len(dwell_values), 1) if dwell_values else 0.0,
            "average_pedestrian_wait_ms": round(sum(pedestrian_waits) / len(pedestrian_waits), 1) if pedestrian_waits else 0.0,
            "direction_counts": dict(sorted(directions.items())),
            "line_counts": dict(sorted(line_counts.items())),
            "region_average_dwell_ms": {
                region_id: round(sum(values) / len(values), 1)
                for region_id, values in sorted(per_region_dwell.items())
                if values
            },
            "unique_event_tracks": len({str(event.get("track_id")) for event in records if event.get("track_id")}),
        }

    def _append(self, event: dict[str, Any]) -> None:
        try:
            self._flow_path.parent.mkdir(parents=True, exist_ok=True)
            with self._flow_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(event, separators=(",", ":")) + "\n")
        except OSError as exc:
            logger.exception("Traffic flow write failed", extra={"error_code": ErrorCode.TRAFFIC_FLOW_WRITE_FAILED.value})
            raise AppError(
                ErrorCode.TRAFFIC_FLOW_WRITE_FAILED,
                "Failed to persist traffic flow event.",
                status_code=500,
            ) from exc
        self._append_count += 1
        if self._append_count >= 500:
            self._append_count = 0
            self._compact_if_needed()

    def _read_all(self) -> list[dict[str, Any]]:
        with self._lock:
            if not self._flow_path.is_file():
                return []
            try:
                lines = self._flow_path.read_text(encoding="utf-8").splitlines()
            except OSError as exc:
                logger.exception("Traffic flow read failed", extra={"error_code": ErrorCode.TRAFFIC_FLOW_READ_FAILED.value})
                raise AppError(
                    ErrorCode.TRAFFIC_FLOW_READ_FAILED,
                    "Failed to read traffic flow events.",
                    status_code=500,
                ) from exc
        records: list[dict[str, Any]] = []
        for line in lines:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("Skipped malformed traffic flow JSONL record")
                continue
            if isinstance(record, dict) and record.get("event_id") and record.get("timestamp_ms") is not None:
                records.append(record)
        with self._lock:
            self._known_event_ids.update(str(record["event_id"]) for record in records)
        return records[-self.max_events :]

    def _compact_if_needed(self) -> None:
        records = self._read_all()
        if len(records) < self.max_events:
            return
        try:
            self._flow_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self._flow_path.with_suffix(".tmp")
            with temporary.open("w", encoding="utf-8", newline="\n") as handle:
                for record in records[-self.max_events :]:
                    handle.write(json.dumps(record, separators=(",", ":")) + "\n")
            temporary.replace(self._flow_path)
        except OSError as exc:
            logger.exception("Traffic flow compaction failed", extra={"error_code": ErrorCode.TRAFFIC_FLOW_WRITE_FAILED.value})
            raise AppError(
                ErrorCode.TRAFFIC_FLOW_WRITE_FAILED,
                "Failed to compact traffic flow events.",
                status_code=500,
            ) from exc


traffic_flow_service = TrafficFlowService()
