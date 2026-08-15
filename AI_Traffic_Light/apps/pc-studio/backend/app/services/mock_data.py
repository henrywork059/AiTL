"""Offline/smoke fallback fixtures.

Working V017 pages use receiver/simulation, persistent zones, trained-model
inference, and live prototype services. These fixtures remain only for the
backward-compatible /api/mock endpoints and frontend-offline rendering.
"""

from app.core.logging_config import get_logger

logger = get_logger(__name__)


def get_mock_detection_frame() -> dict:
    """Return a stable fallback frame aligned to the V016/V017 reference scene."""
    frame = {
        "frame_id": "fallback_cam_000001",
        "source_id": "fallback_camera",
        "image_width": 1280,
        "image_height": 720,
        "timestamp_ms": 0,
        "detections": [
            {
                "id": "fallback_person_waiting",
                "class_id": 0,
                "class_name": "person",
                "confidence": 0.93,
                "box_xyxy": [585, 70, 645, 165],
            },
            {
                "id": "fallback_person_crossing",
                "class_id": 0,
                "class_name": "person",
                "confidence": 0.88,
                "box_xyxy": [625, 300, 690, 430],
            },
            {
                "id": "fallback_car_left",
                "class_id": 1,
                "class_name": "car",
                "confidence": 0.91,
                "box_xyxy": [250, 350, 430, 455],
            },
            {
                "id": "fallback_bus_right",
                "class_id": 2,
                "class_name": "bus",
                "confidence": 0.84,
                "box_xyxy": [860, 430, 1160, 565],
            },
        ],
    }
    logger.debug("Generated fallback detection frame", extra={"frame_id": frame["frame_id"]})
    return frame


def get_mock_zones() -> list[dict]:
    """Return fallback zones aligned with the persistent V017 defaults."""
    zones = [
        {
            "id": "ped_waiting_top",
            "type": "pedestrian_waiting",
            "label": "Pedestrian Waiting Zone",
            "polygon": [[500, 0], [780, 0], [780, 178], [500, 178]],
        },
        {
            "id": "crossing_main",
            "type": "crossing",
            "label": "Crossing Zone",
            "polygon": [[500, 179], [780, 179], [780, 625], [500, 625]],
        },
        {
            "id": "vehicle_queue_left",
            "type": "vehicle_queue",
            "label": "Left Vehicle Queue",
            "polygon": [[0, 190], [500, 190], [500, 615], [0, 615]],
        },
        {
            "id": "vehicle_queue_right",
            "type": "vehicle_queue",
            "label": "Right Vehicle Queue",
            "polygon": [[780, 190], [1279, 190], [1279, 615], [780, 615]],
        },
    ]
    logger.debug("Generated fallback zones", extra={"zone_count": len(zones)})
    return zones
