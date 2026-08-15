"""Checks for persistent zones, counting regions, and live-detection-based prototype traffic decisions."""
from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pc-studio" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.error_codes import ErrorCode  # noqa: E402
from app.core.exceptions import AppError  # noqa: E402
from app.services.traffic_logic import evaluate_traffic_state  # noqa: E402
from app.services.zones import ZoneService  # noqa: E402


def detection(class_name: str, box: list[int], index: int) -> dict:
    return {
        "id": f"det-{index}",
        "class_id": index,
        "class_name": class_name,
        "confidence": 0.9,
        "box_xyxy": box,
    }


def main() -> int:
    with TemporaryDirectory(prefix="aitl-zone-test-") as temporary_directory:
        zone_path = Path(temporary_directory) / "zones.json"
        service = ZoneService(zone_path=zone_path)
        defaults = service.status()
        assert defaults["source"] == "defaults"
        assert len(defaults["zones"]) >= 4

        counting_region = {
            "id": "analytics_left",
            "type": "counting_region",
            "label": "Analytics Left",
            "polygon": [[0, 0], [480, 0], [480, 719], [0, 719]],
        }
        saved = service.save([*defaults["zones"][:3], counting_region])
        assert saved["source"] == "persisted"
        assert any(zone["type"] == "counting_region" for zone in saved["zones"])
        assert zone_path.is_file()
        reloaded = ZoneService(zone_path=zone_path).status()
        assert len(reloaded["zones"]) == 4

        try:
            service.save([
                {"id": "bad", "type": "crossing", "label": "Bad", "polygon": [[0, 0], [1, 1]]}
            ])
        except AppError as exc:
            assert exc.code == ErrorCode.ZONE_CONFIG_INVALID
        else:
            raise AssertionError("Invalid two-point polygon was accepted")

        zones = [*defaults["zones"], counting_region]
        frame = {
            "image_width": 1280,
            "image_height": 720,
            "timestamp_ms": 123456,
            "source_frame_number": 12,
            "detections": [
                detection("person", [590, 300, 650, 420], 0),
                detection("car", [120, 300, 300, 420], 1),
                detection("bus", [220, 240, 430, 390], 2),
            ],
        }
        state = evaluate_traffic_state(frame, zones)
        assert state["pedestrians_crossing"] == 1
        assert state["vehicles_waiting"] == 2
        assert state["pedestrians_total"] == 1
        assert state["vehicles_total"] == 2
        assert state["region_counts"]["analytics_left"]["vehicles"] == 2
        assert state["region_counts"]["analytics_left"]["pedestrians"] == 0
        assert state["zone_counts"]["analytics_left"] == 2
        assert state["phase"] == "pedestrian_green"
        assert state["decision"] == "hold_pedestrian_phase"
        assert state["evaluated_frame_number"] == 12
        assert state["source_timestamp_ms"] == 123456

        waiting_frame = {
            "image_width": 1280,
            "image_height": 720,
            "timestamp_ms": 123457,
            "source_frame_number": 13,
            "detections": [detection("person", [590, 45, 650, 145], 3)],
        }
        waiting_state = evaluate_traffic_state(waiting_frame, zones)
        assert waiting_state["pedestrians_waiting"] == 1
        assert waiting_state["pedestrians_crossing"] == 0
        assert waiting_state["phase"] == "vehicle_yellow"
        assert waiting_state["decision"] == "prepare_pedestrian_green"

    print("[PASS] zone defaults and analytics counting regions can be saved/reloaded")
    print("[PASS] invalid polygons use the stable zone error code")
    print("[PASS] whole-frame pedestrian/vehicle occupancy is counted")
    print("[PASS] per-region pedestrian/vehicle counts are independent of traffic-phase rules")
    print("[PASS] existing crossing and vehicle-queue decisions remain simulation-only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
