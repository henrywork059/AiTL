"""Focused V022 tests for cross-frame IDs, counting lines, region events, dwell, persistence, and CSV."""
from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pc-studio" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.error_codes import ErrorCode  # noqa: E402
from app.core.exceptions import AppError  # noqa: E402
from app.services.object_tracking import ObjectTrackingService  # noqa: E402
from app.services.traffic_flow import TrafficFlowService  # noqa: E402


ZONES = [
    {
        "id": "vehicle_line",
        "type": "counting_line",
        "label": "Vehicle flow line",
        "polygon": [[500, 180], [500, 620]],
    },
    {
        "id": "pedestrian_line",
        "type": "counting_line",
        "label": "Pedestrian flow line",
        "polygon": [[520, 350], [760, 350]],
    },
    {
        "id": "vehicle_region",
        "type": "counting_region",
        "label": "Vehicle dwell region",
        "polygon": [[400, 180], [600, 180], [600, 620], [400, 620]],
    },
    {
        "id": "ped_wait",
        "type": "pedestrian_waiting",
        "label": "Pedestrian waiting region",
        "polygon": [[520, 80], [760, 80], [760, 300], [520, 300]],
    },
]


def det(identifier: str, class_name: str, center_x: int, center_y: int, *, width: int = 80, height: int = 80) -> dict:
    return {
        "id": identifier,
        "class_id": 0 if class_name == "person" else 1,
        "class_name": class_name,
        "confidence": 0.95,
        "box_xyxy": [
            center_x - width // 2,
            center_y - height // 2,
            center_x + width // 2,
            center_y + height // 2,
        ],
    }


def frame(number: int, timestamp_ms: int, detections: list[dict]) -> dict:
    return {
        "frame_id": f"test-{number}",
        "source_id": "tracking_test",
        "image_width": 1280,
        "image_height": 720,
        "timestamp_ms": timestamp_ms,
        "source_frame_number": number,
        "detections": detections,
    }


def main() -> int:
    with TemporaryDirectory(prefix="aitl-v022-track-test-") as temporary_directory:
        flow_path = Path(temporary_directory) / "events.jsonl"
        flow = TrafficFlowService(flow_path=flow_path, max_events=1000)
        tracker = ObjectTrackingService(flow_service=flow)

        sequence = [
            frame(1, 1_000, [det("car-1", "car", 350, 400), det("person-1", "person", 640, 120)]),
            frame(2, 2_000, [det("car-2", "car", 450, 400), det("person-2", "person", 640, 220)]),
            frame(3, 3_000, [det("car-3", "car", 550, 400), det("person-3", "person", 640, 320)]),
            frame(4, 4_000, [det("car-4", "car", 650, 400), det("person-4", "person", 640, 420)]),
        ]

        tracked = [tracker.update(item, ZONES) for item in sequence]
        car_ids = [next(d["track_id"] for d in item["detections"] if d["class_name"] == "car") for item in tracked]
        person_ids = [next(d["track_id"] for d in item["detections"] if d["class_name"] == "person") for item in tracked]
        assert len(set(car_ids)) == 1, car_ids
        assert len(set(person_ids)) == 1, person_ids
        assert car_ids[0] != person_ids[0]
        assert tracked[-1]["tracking"]["active_track_count"] == 2
        assert tracked[-1]["tracking"]["total_tracks_created"] == 2

        # Replaying an already processed physical frame cannot advance/count twice. A caller
        # using a different confidence threshold still receives its own detection list.
        replay = tracker.update(sequence[-1], ZONES)
        assert replay["detections"][0]["track_id"] == tracked[-1]["detections"][0]["track_id"]
        replay_events = replay["tracking"]["events_recorded"]
        same_frame_extra = dict(sequence[-1])
        same_frame_extra["detections"] = [
            *sequence[-1]["detections"],
            {
                "id": "low-confidence-extra",
                "class_id": 1,
                "class_name": "car",
                "confidence": 0.05,
                "box_xyxy": [1100, 220, 1170, 280],
            },
        ]
        same_frame_result = tracker.update(same_frame_extra, ZONES)
        assert len(same_frame_result["detections"]) == len(same_frame_extra["detections"])
        assert same_frame_result["tracking"]["events_recorded"] == replay_events

        data = flow.query(zones=ZONES, minutes=0, limit=1000)
        summary = data["summary"]
        assert summary["unique_passages"] == 2, data["events"]
        assert summary["unique_vehicle_passages"] == 1
        assert summary["unique_pedestrian_passages"] == 1
        assert summary["direction_counts"]["left_to_right"] == 1
        assert summary["direction_counts"]["top_to_bottom"] == 1
        assert summary["region_entries"] >= 2
        assert summary["region_exits"] >= 2
        assert summary["average_dwell_ms"] > 0
        assert summary["average_pedestrian_wait_ms"] > 0
        assert data["buckets"][0]["vehicles"] == 1
        assert data["buckets"][0]["pedestrians"] == 1

        line_events = flow.query(zones=ZONES, minutes=0, line_id="vehicle_line")
        assert line_events["summary"]["unique_vehicle_passages"] == 1
        assert line_events["summary"]["unique_pedestrian_passages"] == 0

        region_events = flow.query(zones=ZONES, minutes=0, region_id="ped_wait")
        assert region_events["summary"]["average_pedestrian_wait_ms"] > 0

        try:
            flow.query(zones=ZONES, minutes=0, line_id="missing_line")
        except AppError as exc:
            assert exc.code == ErrorCode.ZONE_NOT_FOUND
        else:
            raise AssertionError("Missing counting line was accepted")

        csv_text = flow.export_csv(zones=ZONES, minutes=0)
        assert "event_id,timestamp_ms,source_frame_number,track_id,class_id,class_name,event_type" in csv_text
        assert "line_crossing" in csv_text
        assert "region_exit" in csv_text
        assert flow_path.is_file()

        reloaded = TrafficFlowService(flow_path=flow_path, max_events=1000)
        persisted = reloaded.query(zones=ZONES, minutes=0)
        assert persisted["stored_events"] == data["stored_events"]
        assert persisted["summary"]["unique_passages"] == 2

        cleared = reloaded.clear()
        assert cleared["removed_events"] == data["stored_events"]
        assert cleared["stored_events"] == 0
        assert not flow_path.exists()

        reverse_flow_path = Path(temporary_directory) / "reverse-events.jsonl"
        reverse_flow = TrafficFlowService(flow_path=reverse_flow_path, max_events=1000)
        reverse_tracker = ObjectTrackingService(flow_service=reverse_flow)
        reverse_tracker.update(
            frame(10, 10_000, [det("reverse-car-a", "car", 650, 500), det("reverse-person-a", "person", 640, 430)]),
            ZONES,
        )
        reverse_tracker.update(
            frame(11, 11_000, [det("reverse-car-b", "car", 550, 500), det("reverse-person-b", "person", 640, 370)]),
            ZONES,
        )
        reverse_tracker.update(
            frame(12, 12_000, [det("reverse-car-c", "car", 450, 500), det("reverse-person-c", "person", 640, 300)]),
            ZONES,
        )
        reverse_summary = reverse_flow.query(zones=ZONES, minutes=0)["summary"]
        assert reverse_summary["direction_counts"]["right_to_left"] == 1
        assert reverse_summary["direction_counts"]["bottom_to_top"] == 1

    print("[PASS] stable cross-frame IDs are retained for matched vehicle/pedestrian detections")
    print("[PASS] each track generates at most one unique event per configured counting line")
    print("[PASS] line crossings record all four cardinal movement directions and separate vehicle/pedestrian passages")
    print("[PASS] region entry/exit events record dwell and pedestrian-wait duration")
    print("[PASS] flow events persist as bounded JSONL and support filters, minute buckets, CSV, and clear")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
