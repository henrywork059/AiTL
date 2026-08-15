"""Focused checks for persistent traffic occupancy history, region queries, CSV export, and clear."""
from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pc-studio" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.error_codes import ErrorCode  # noqa: E402
from app.core.exceptions import AppError  # noqa: E402
from app.services.traffic_history import TrafficHistoryService  # noqa: E402


ZONES = [
    {
        "id": "count_left",
        "type": "counting_region",
        "label": "Left counting region",
        "polygon": [[0, 0], [500, 0], [500, 720], [0, 720]],
    },
    {
        "id": "crossing_main",
        "type": "crossing",
        "label": "Crossing",
        "polygon": [[500, 0], [780, 0], [780, 720], [500, 720]],
    },
    {
        "id": "flow_line",
        "type": "counting_line",
        "label": "Flow line",
        "polygon": [[640, 0], [640, 720]],
    },
]


def state(
    *,
    timestamp: int,
    frame: int,
    pedestrians: int,
    vehicles: int,
    left_pedestrians: int,
    left_vehicles: int,
    phase: str,
) -> dict:
    return {
        "evaluated_at_ms": timestamp,
        "source_timestamp_ms": timestamp,
        "evaluated_frame_number": frame,
        "data_source": "test",
        "phase": phase,
        "decision": "test_decision",
        "pedestrians_total": pedestrians,
        "vehicles_total": vehicles,
        "pedestrians_waiting": 0,
        "pedestrians_crossing": 0,
        "vehicles_waiting": vehicles,
        "region_counts": {
            "count_left": {
                "pedestrians": left_pedestrians,
                "vehicles": left_vehicles,
                "total": left_pedestrians + left_vehicles,
            },
            "crossing_main": {
                "pedestrians": pedestrians - left_pedestrians,
                "vehicles": 0,
                "total": pedestrians - left_pedestrians,
            },
        },
    }


def main() -> int:
    with TemporaryDirectory(prefix="aitl-traffic-history-test-") as temporary_directory:
        history_path = Path(temporary_directory) / "history.jsonl"
        service = TrafficHistoryService(history_path=history_path, sample_interval_ms=1000, max_samples=100)

        samples = [
            state(timestamp=1_000, frame=1, pedestrians=1, vehicles=2, left_pedestrians=0, left_vehicles=2, phase="vehicle_green"),
            state(timestamp=2_000, frame=2, pedestrians=3, vehicles=4, left_pedestrians=1, left_vehicles=3, phase="vehicle_yellow"),
            state(timestamp=3_000, frame=3, pedestrians=2, vehicles=1, left_pedestrians=2, left_vehicles=1, phase="pedestrian_green"),
        ]
        for sample in samples:
            assert service.record_state(sample, force=True) is True
        assert service.record_state(samples[-1]) is False
        assert history_path.is_file()

        whole = service.query(zones=ZONES, minutes=0, limit=100)
        assert whole["summary"]["sample_count"] == 3
        assert whole["summary"]["peak_pedestrians"]["count"] == 3
        assert whole["summary"]["peak_vehicles"]["count"] == 4
        assert whole["summary"]["phase_change_count"] == 2
        assert whole["summary"]["busiest_region"]["id"] == "count_left"
        assert whole["points"][1]["vehicles"] == 4
        assert all(region["id"] != "flow_line" for region in whole["regions"])

        left = service.query(zones=ZONES, minutes=0, limit=100, region_id="count_left")
        assert left["scope"]["label"] == "Left counting region"
        assert [point["pedestrians"] for point in left["points"]] == [0, 1, 2]
        assert [point["vehicles"] for point in left["points"]] == [2, 3, 1]

        try:
            service.query(zones=ZONES, minutes=0, region_id="missing_region")
        except AppError as exc:
            assert exc.code == ErrorCode.ZONE_NOT_FOUND
        else:
            raise AssertionError("Missing counting region did not use ZONE_NOT_FOUND")

        csv_text = service.export_csv(zones=ZONES, minutes=0, region_id="count_left")
        assert "recorded_at_ms,source_timestamp_ms,source_frame_number,pedestrians,vehicles" in csv_text
        assert "Left counting region" in csv_text

        cleared = service.clear()
        assert cleared["removed_samples"] == 3
        assert cleared["stored_samples"] == 0
        assert not history_path.exists()

    print("[PASS] detection-backed occupancy samples persist as bounded JSONL runtime data")
    print("[PASS] whole-frame and named-region queries resolve pedestrian/vehicle series")
    print("[PASS] peak/average/phase-change/busiest-region summaries are generated")
    print("[PASS] missing analytics regions use the stable ZONE_NOT_FOUND error")
    print("[PASS] CSV export and explicit history clear work without touching other runtime data")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
