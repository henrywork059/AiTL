from __future__ import annotations

import csv
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
DEFAULT_HISTORY_PATH = PROJECT_ROOT / "outputs" / "traffic_history" / "history.jsonl"
DEFAULT_SAMPLE_INTERVAL_MS = 1000
DEFAULT_MAX_SAMPLES = 21600


def _positive_int_env(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, min(maximum, value))


class TrafficHistoryService:
    """Persist sampled traffic occupancy metrics as bounded JSONL runtime data."""

    def __init__(
        self,
        *,
        history_path: Path | None = None,
        sample_interval_ms: int | None = None,
        max_samples: int | None = None,
    ) -> None:
        configured_path = os.environ.get("AITL_TRAFFIC_HISTORY_PATH")
        self._history_path = Path(configured_path) if configured_path else (history_path or DEFAULT_HISTORY_PATH)
        self._history_path = self._history_path.expanduser().resolve()
        self.sample_interval_ms = sample_interval_ms or _positive_int_env(
            "AITL_TRAFFIC_HISTORY_INTERVAL_MS",
            DEFAULT_SAMPLE_INTERVAL_MS,
            minimum=250,
            maximum=60_000,
        )
        self.max_samples = max_samples or _positive_int_env(
            "AITL_TRAFFIC_HISTORY_MAX_SAMPLES",
            DEFAULT_MAX_SAMPLES,
            minimum=100,
            maximum=200_000,
        )
        self._lock = RLock()
        self._last_recorded_at_ms: int | None = None
        self._last_source_key: tuple[Any, Any] | None = None
        self._append_count = 0

    @property
    def history_path(self) -> Path:
        return self._history_path

    def record_state(self, state: dict[str, Any], *, force: bool = False) -> bool:
        """Record one valid detection-backed occupancy sample if it is new and due."""
        frame_number = state.get("evaluated_frame_number")
        source_timestamp_ms = state.get("source_timestamp_ms")
        if frame_number is None or source_timestamp_ms is None:
            return False

        recorded_at_ms = int(state.get("evaluated_at_ms") or time() * 1000)
        source_key = (frame_number, source_timestamp_ms)
        with self._lock:
            if not force:
                if source_key == self._last_source_key:
                    return False
                if (
                    self._last_recorded_at_ms is not None
                    and recorded_at_ms - self._last_recorded_at_ms < self.sample_interval_ms
                ):
                    return False

            sample = {
                "recorded_at_ms": recorded_at_ms,
                "source_timestamp_ms": int(source_timestamp_ms),
                "source_frame_number": int(frame_number),
                "data_source": str(state.get("data_source") or "unknown"),
                "phase": str(state.get("phase") or "unknown"),
                "decision": str(state.get("decision") or "unknown"),
                "pedestrians": int(state.get("pedestrians_total") or 0),
                "vehicles": int(state.get("vehicles_total") or 0),
                "pedestrians_waiting": int(state.get("pedestrians_waiting") or 0),
                "pedestrians_crossing": int(state.get("pedestrians_crossing") or 0),
                "vehicles_waiting": int(state.get("vehicles_waiting") or 0),
                "region_counts": state.get("region_counts") if isinstance(state.get("region_counts"), dict) else {},
            }
            self._append(sample)
            self._last_recorded_at_ms = recorded_at_ms
            self._last_source_key = source_key
            return True

    def status(self) -> dict[str, Any]:
        return self._status_from_records(self._read_all())

    def _status_from_records(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "recording": True,
            "sample_interval_ms": self.sample_interval_ms,
            "max_samples": self.max_samples,
            "stored_samples": len(records),
            "history_path": "outputs/traffic_history/history.jsonl",
            "oldest_recorded_at_ms": records[0]["recorded_at_ms"] if records else None,
            "newest_recorded_at_ms": records[-1]["recorded_at_ms"] if records else None,
        }

    def query(
        self,
        *,
        zones: list[dict[str, Any]],
        minutes: int = 15,
        limit: int = 2000,
        region_id: str | None = None,
    ) -> dict[str, Any]:
        """Return a bounded time series plus summary statistics for the whole frame or one region."""
        zone_by_id = {zone["id"]: zone for zone in zones if zone.get("type") != "ignore"}
        if region_id is not None and region_id not in zone_by_id:
            raise AppError(
                ErrorCode.ZONE_NOT_FOUND,
                "The requested counting region was not found.",
                status_code=404,
                details={"region_id": region_id},
            )

        all_records = self._read_all()
        records = all_records
        if minutes > 0:
            cutoff_ms = int(time() * 1000) - minutes * 60_000
            records = [record for record in records if int(record.get("recorded_at_ms", 0)) >= cutoff_ms]
        if limit > 0 and len(records) > limit:
            records = records[-limit:]

        points = [self._resolve_point(record, region_id=region_id) for record in records]
        scope_zone = zone_by_id.get(region_id) if region_id is not None else None
        return {
            **self._status_from_records(all_records),
            "scope": {
                "region_id": region_id,
                "label": scope_zone.get("label") if scope_zone else "Whole frame",
                "type": scope_zone.get("type") if scope_zone else "whole_frame",
            },
            "minutes": minutes,
            "regions": [
                {"id": zone["id"], "label": zone["label"], "type": zone["type"]}
                for zone in zones
                if zone.get("type") != "ignore"
            ],
            "points": points,
            "summary": self._summary(points, records, zone_by_id),
        }

    def export_csv(
        self,
        *,
        zones: list[dict[str, Any]],
        minutes: int = 15,
        limit: int = 5000,
        region_id: str | None = None,
    ) -> str:
        data = self.query(zones=zones, minutes=minutes, limit=limit, region_id=region_id)
        output = StringIO()
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow([
            "recorded_at_ms",
            "source_timestamp_ms",
            "source_frame_number",
            "pedestrians",
            "vehicles",
            "phase",
            "decision",
            "scope_region_id",
            "scope_label",
        ])
        for point in data["points"]:
            writer.writerow([
                point["recorded_at_ms"],
                point["source_timestamp_ms"],
                point["source_frame_number"],
                point["pedestrians"],
                point["vehicles"],
                point["phase"],
                point["decision"],
                data["scope"]["region_id"] or "",
                data["scope"]["label"],
            ])
        return output.getvalue()

    def clear(self) -> dict[str, Any]:
        with self._lock:
            removed = 0
            if self._history_path.is_file():
                try:
                    removed = sum(1 for line in self._history_path.read_text(encoding="utf-8").splitlines() if line.strip())
                    self._history_path.unlink()
                except OSError as exc:
                    logger.exception(
                        "Traffic history clear failed",
                        extra={"error_code": ErrorCode.TRAFFIC_HISTORY_CLEAR_FAILED.value},
                    )
                    raise AppError(
                        ErrorCode.TRAFFIC_HISTORY_CLEAR_FAILED,
                        "Failed to clear traffic history.",
                        status_code=500,
                    ) from exc
            self._last_recorded_at_ms = None
            self._last_source_key = None
            self._append_count = 0
        logger.info("Traffic history cleared", extra={"removed_samples": removed})
        return {"cleared": True, "removed_samples": removed, **self.status()}

    def _append(self, sample: dict[str, Any]) -> None:
        try:
            self._history_path.parent.mkdir(parents=True, exist_ok=True)
            with self._history_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(sample, separators=(",", ":")) + "\n")
        except OSError as exc:
            logger.exception(
                "Traffic history write failed",
                extra={"error_code": ErrorCode.TRAFFIC_HISTORY_WRITE_FAILED.value},
            )
            raise AppError(
                ErrorCode.TRAFFIC_HISTORY_WRITE_FAILED,
                "Failed to persist traffic history sample.",
                status_code=500,
            ) from exc

        self._append_count += 1
        if self._append_count >= 250:
            self._append_count = 0
            self._compact_if_needed()

    def _read_all(self) -> list[dict[str, Any]]:
        with self._lock:
            if not self._history_path.is_file():
                return []
            try:
                lines = self._history_path.read_text(encoding="utf-8").splitlines()
            except OSError as exc:
                logger.exception(
                    "Traffic history read failed",
                    extra={"error_code": ErrorCode.TRAFFIC_HISTORY_READ_FAILED.value},
                )
                raise AppError(
                    ErrorCode.TRAFFIC_HISTORY_READ_FAILED,
                    "Failed to read traffic history.",
                    status_code=500,
                ) from exc

        records: list[dict[str, Any]] = []
        for line_number, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                logger.warning(
                    "Skipping malformed traffic history line",
                    extra={"line_number": line_number},
                )
                continue
            if isinstance(payload, dict) and "recorded_at_ms" in payload:
                records.append(payload)
        records.sort(key=lambda record: int(record.get("recorded_at_ms", 0)))
        return records

    def _compact_if_needed(self) -> None:
        records = self._read_all()
        if len(records) <= self.max_samples:
            return
        retained = records[-self.max_samples :]
        temporary = self._history_path.with_suffix(".tmp")
        try:
            temporary.write_text(
                "".join(json.dumps(record, separators=(",", ":")) + "\n" for record in retained),
                encoding="utf-8",
            )
            temporary.replace(self._history_path)
        except OSError as exc:
            logger.exception(
                "Traffic history compaction failed",
                extra={"error_code": ErrorCode.TRAFFIC_HISTORY_WRITE_FAILED.value},
            )
            raise AppError(
                ErrorCode.TRAFFIC_HISTORY_WRITE_FAILED,
                "Failed to compact traffic history.",
                status_code=500,
            ) from exc

    @staticmethod
    def _resolve_point(record: dict[str, Any], *, region_id: str | None) -> dict[str, Any]:
        if region_id is None:
            pedestrians = int(record.get("pedestrians") or 0)
            vehicles = int(record.get("vehicles") or 0)
        else:
            region = record.get("region_counts", {}).get(region_id, {})
            pedestrians = int(region.get("pedestrians") or 0)
            vehicles = int(region.get("vehicles") or 0)
        return {
            "recorded_at_ms": int(record.get("recorded_at_ms") or 0),
            "source_timestamp_ms": int(record.get("source_timestamp_ms") or 0),
            "source_frame_number": int(record.get("source_frame_number") or 0),
            "pedestrians": pedestrians,
            "vehicles": vehicles,
            "phase": str(record.get("phase") or "unknown"),
            "decision": str(record.get("decision") or "unknown"),
        }

    @staticmethod
    def _summary(
        points: list[dict[str, Any]],
        raw_records: list[dict[str, Any]],
        zone_by_id: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        if not points:
            return {
                "sample_count": 0,
                "average_pedestrians": 0.0,
                "average_vehicles": 0.0,
                "peak_pedestrians": {"count": 0, "recorded_at_ms": None},
                "peak_vehicles": {"count": 0, "recorded_at_ms": None},
                "phase_change_count": 0,
                "latest_phase_change": None,
                "busiest_region": None,
            }

        peak_pedestrians = max(points, key=lambda point: point["pedestrians"])
        peak_vehicles = max(points, key=lambda point: point["vehicles"])
        phase_changes: list[dict[str, Any]] = []
        previous_phase: str | None = None
        for point in points:
            phase = point["phase"]
            if previous_phase is not None and phase != previous_phase:
                phase_changes.append({
                    "recorded_at_ms": point["recorded_at_ms"],
                    "from": previous_phase,
                    "to": phase,
                })
            previous_phase = phase

        region_totals: dict[str, int] = {}
        region_samples: dict[str, int] = {}
        for record in raw_records:
            for region_id, counts in record.get("region_counts", {}).items():
                if region_id not in zone_by_id or not isinstance(counts, dict):
                    continue
                region_totals[region_id] = region_totals.get(region_id, 0) + int(counts.get("total") or 0)
                region_samples[region_id] = region_samples.get(region_id, 0) + 1
        busiest_region = None
        if region_totals:
            region_id = max(
                region_totals,
                key=lambda item: region_totals[item] / max(1, region_samples.get(item, 1)),
            )
            zone = zone_by_id[region_id]
            busiest_region = {
                "id": region_id,
                "label": zone.get("label", region_id),
                "type": zone.get("type", "unknown"),
                "average_total": round(region_totals[region_id] / max(1, region_samples.get(region_id, 1)), 2),
            }

        return {
            "sample_count": len(points),
            "average_pedestrians": round(sum(point["pedestrians"] for point in points) / len(points), 2),
            "average_vehicles": round(sum(point["vehicles"] for point in points) / len(points), 2),
            "peak_pedestrians": {
                "count": peak_pedestrians["pedestrians"],
                "recorded_at_ms": peak_pedestrians["recorded_at_ms"],
            },
            "peak_vehicles": {
                "count": peak_vehicles["vehicles"],
                "recorded_at_ms": peak_vehicles["recorded_at_ms"],
            },
            "phase_change_count": len(phase_changes),
            "latest_phase_change": phase_changes[-1] if phase_changes else None,
            "busiest_region": busiest_region,
        }


traffic_history_service = TrafficHistoryService()
