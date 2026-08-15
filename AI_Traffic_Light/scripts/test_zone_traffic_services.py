"""Checks for persistent zones and live-detection-based prototype traffic decisions."""
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

        saved = service.save(defaults["zones"][:3])
        assert saved["source"] == "persisted"
        assert zone_path.is_file()
        reloaded = ZoneService(zone_path=zone_path).status()
        assert len(reloaded["zones"]) == 3

        try:
            service.save([
                {"id": "bad", "type": "crossing", "label": "Bad", "polygon": [[0, 0], [1, 1]]}
            ])
        except AppError as exc:
            assert exc.code == ErrorCode.ZONE_CONFIG_INVALID
        else:
            raise AssertionError("Invalid two-point polygon was accepted")

        zones = defaults["zones"]
        frame = {
            "image_width": 1280,
            "image_height": 720,
            "source_frame_number": 12,
            "detections": [
                detection("person", [590, 300, 650, 420], 0),
                detection("car", [120, 300, 300, 420], 1),
            ],
        }
        state = evaluate_traffic_state(frame, zones)
        assert state["pedestrians_crossing"] == 1
        assert state["vehicles_waiting"] == 1
        assert state["phase"] == "pedestrian_green"
        assert state["decision"] == "hold_pedestrian_phase"
        assert state["evaluated_frame_number"] == 12

        waiting_frame = {
            "image_width": 1280,
            "image_height": 720,
            "source_frame_number": 13,
            "detections": [detection("person", [590, 45, 650, 145], 2)],
        }
        waiting_state = evaluate_traffic_state(waiting_frame, zones)
        assert waiting_state["pedestrians_waiting"] == 1
        assert waiting_state["pedestrians_crossing"] == 0
        assert waiting_state["phase"] == "vehicle_yellow"
        assert waiting_state["decision"] == "prepare_pedestrian_green"

    print("[PASS] zone defaults can be saved and reloaded persistently")
    print("[PASS] invalid polygons use the stable zone error code")
    print("[PASS] live detection centres are counted in crossing and queue zones")
    print("[PASS] zone counts drive simulation-only traffic recommendations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
