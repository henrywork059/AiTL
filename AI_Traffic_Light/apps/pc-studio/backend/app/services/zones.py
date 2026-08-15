from __future__ import annotations

import json
import os
from pathlib import Path
import re
from threading import Lock
from typing import Any

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.core.logging_config import get_logger

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_ZONE_PATH = PROJECT_ROOT / "config" / "zones.json"
REFERENCE_WIDTH = 1280
REFERENCE_HEIGHT = 720
ZONE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
ZONE_TYPES = {"pedestrian_waiting", "crossing", "vehicle_queue", "counting_region", "counting_line", "ignore"}

DEFAULT_ZONES: list[dict[str, Any]] = [
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


class ZoneService:
    """Persist and validate editable prototype traffic zones."""

    def __init__(self, *, zone_path: Path | None = None) -> None:
        configured = os.environ.get("AITL_ZONE_CONFIG")
        self._zone_path = Path(configured) if configured else (zone_path or DEFAULT_ZONE_PATH)
        self._zone_path = self._zone_path.expanduser().resolve()
        self._lock = Lock()

    def status(self) -> dict[str, Any]:
        zones, source = self._load_zones()
        return {
            "zones": zones,
            "editable": True,
            "status": "ready",
            "source": source,
            "reference_resolution": {"width": REFERENCE_WIDTH, "height": REFERENCE_HEIGHT},
            "config_path": "config/zones.json",
        }

    def zones(self) -> list[dict[str, Any]]:
        zones, _ = self._load_zones()
        return zones

    def save(self, zones: list[dict[str, Any]]) -> dict[str, Any]:
        validated = self._validate_zones(zones)
        payload = {
            "reference_resolution": {"width": REFERENCE_WIDTH, "height": REFERENCE_HEIGHT},
            "zones": validated,
        }
        try:
            self._zone_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self._zone_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            temporary.replace(self._zone_path)
        except OSError as exc:
            logger.exception("Zone configuration save failed", extra={"error_code": ErrorCode.ZONE_SAVE_FAILED.value})
            raise AppError(
                ErrorCode.ZONE_SAVE_FAILED,
                "Failed to save the zone configuration.",
                status_code=500,
            ) from exc
        logger.info("Zone configuration saved", extra={"zone_count": len(validated)})
        return self.status()

    def reset_defaults(self) -> dict[str, Any]:
        return self.save([dict(zone) for zone in DEFAULT_ZONES])

    def _load_zones(self) -> tuple[list[dict[str, Any]], str]:
        with self._lock:
            if not self._zone_path.is_file():
                return ([dict(zone) for zone in DEFAULT_ZONES], "defaults")
            try:
                payload = json.loads(self._zone_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                logger.exception("Zone configuration read failed", extra={"error_code": ErrorCode.ZONE_CONFIG_INVALID.value})
                raise AppError(
                    ErrorCode.ZONE_CONFIG_INVALID,
                    "The saved zone configuration could not be read.",
                    status_code=500,
                ) from exc
            zones = payload.get("zones") if isinstance(payload, dict) else None
            if not isinstance(zones, list):
                raise AppError(
                    ErrorCode.ZONE_CONFIG_INVALID,
                    "The saved zone configuration does not contain a zones list.",
                    status_code=500,
                )
            return (self._validate_zones(zones), "persisted")

    @staticmethod
    def _validate_zones(zones: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(zones) > 32:
            raise AppError(
                ErrorCode.ZONE_CONFIG_INVALID,
                "A maximum of 32 prototype zones is supported.",
                status_code=422,
            )
        seen: set[str] = set()
        validated: list[dict[str, Any]] = []
        for zone in zones:
            zone_id = str(zone.get("id", "")).strip()
            zone_type = str(zone.get("type", "")).strip()
            label = str(zone.get("label", "")).strip()
            polygon = zone.get("polygon")
            if not ZONE_ID_PATTERN.fullmatch(zone_id) or zone_id in seen:
                raise AppError(
                    ErrorCode.ZONE_CONFIG_INVALID,
                    "Zone IDs must be unique and contain only letters, numbers, underscores, or dashes.",
                    status_code=422,
                    details={"zone_id": zone_id},
                )
            if zone_type not in ZONE_TYPES:
                raise AppError(
                    ErrorCode.ZONE_CONFIG_INVALID,
                    "Zone type is not supported.",
                    status_code=422,
                    details={"zone_id": zone_id, "zone_type": zone_type},
                )
            if not label or len(label) > 80:
                raise AppError(
                    ErrorCode.ZONE_CONFIG_INVALID,
                    "Zone labels must contain 1-80 characters.",
                    status_code=422,
                    details={"zone_id": zone_id},
                )
            minimum_points = 2 if zone_type == "counting_line" else 3
            maximum_points = 2 if zone_type == "counting_line" else 32
            if not isinstance(polygon, list) or not minimum_points <= len(polygon) <= maximum_points:
                expected = "exactly 2 points" if zone_type == "counting_line" else "3-32 points"
                raise AppError(
                    ErrorCode.ZONE_CONFIG_INVALID,
                    f"Zone geometry for {zone_type} must contain {expected}.",
                    status_code=422,
                    details={"zone_id": zone_id, "zone_type": zone_type},
                )
            points: list[list[int]] = []
            for point in polygon:
                if not isinstance(point, (list, tuple)) or len(point) != 2:
                    raise AppError(
                        ErrorCode.ZONE_CONFIG_INVALID,
                        "Zone polygon points must be [x, y] coordinate pairs.",
                        status_code=422,
                        details={"zone_id": zone_id},
                    )
                try:
                    x, y = int(point[0]), int(point[1])
                except (TypeError, ValueError) as exc:
                    raise AppError(
                        ErrorCode.ZONE_CONFIG_INVALID,
                        "Zone polygon coordinates must be integers.",
                        status_code=422,
                        details={"zone_id": zone_id},
                    ) from exc
                if not 0 <= x < REFERENCE_WIDTH or not 0 <= y < REFERENCE_HEIGHT:
                    raise AppError(
                        ErrorCode.ZONE_CONFIG_INVALID,
                        "Zone coordinates must stay inside the 1280 x 720 reference frame.",
                        status_code=422,
                        details={"zone_id": zone_id, "point": [x, y]},
                    )
                points.append([x, y])
            if zone_type == "counting_line" and points[0] == points[1]:
                raise AppError(
                    ErrorCode.ZONE_CONFIG_INVALID,
                    "A counting line must use two different points.",
                    status_code=422,
                    details={"zone_id": zone_id},
                )
            seen.add(zone_id)
            validated.append({"id": zone_id, "type": zone_type, "label": label, "polygon": points})
        return validated


zone_service = ZoneService()
