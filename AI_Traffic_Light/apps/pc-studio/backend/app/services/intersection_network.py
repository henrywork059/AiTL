from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import re
from threading import RLock
from typing import Any

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.core.json_store import read_json, write_json_atomic
from app.core.logging_config import get_logger

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "intersections.json"
ID_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9._-]{0,63}$")
TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
MAX_INTERSECTIONS = 16
MAX_LINKS = 64
MAX_SOURCE_IDS = 16
MAX_ZONE_IDS = 64

DEFAULT_CONFIG: dict[str, Any] = {
    "schema_version": 1,
    "active_intersection_id": "intersection_main",
    "intersections": [
        {
            "id": "intersection_main",
            "label": "Main prototype junction",
            "enabled": True,
            "source_ids": ["simulation_camera"],
            "zone_ids": [],
            "signal_profile": "Normal",
        }
    ],
    "links": [],
}


class IntersectionNetworkService:
    """Persist generic prototype intersection/topology metadata.

    This service is intentionally configuration-only in V025. It does not
    coordinate phases, move vehicles between intersections, or issue physical
    signal commands. The existing single-junction controller remains the only
    active controller runtime until a later candidate explicitly adds isolated
    per-intersection controller instances.
    """

    def __init__(self, *, config_path: Path | None = None) -> None:
        configured_path = os.environ.get("AITL_INTERSECTION_NETWORK")
        self._config_path = Path(configured_path) if configured_path else (config_path or DEFAULT_CONFIG_PATH)
        self._config_path = self._config_path.expanduser().resolve()
        self._lock = RLock()
        self._cache: dict[str, Any] | None = None

    def defaults(self) -> dict[str, Any]:
        return deepcopy(DEFAULT_CONFIG)

    def get(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._load_locked())

    def save(self, payload: dict[str, Any]) -> dict[str, Any]:
        validated = self._validate(payload)
        try:
            with self._lock:
                write_json_atomic(self._config_path, validated)
                self._cache = validated
        except OSError as exc:
            logger.exception("Intersection network configuration save failed")
            raise AppError(
                ErrorCode.TRAFFIC_NETWORK_WRITE_FAILED,
                "Failed to save the intersection network configuration.",
                status_code=500,
            ) from exc
        return deepcopy(validated)

    def reset(self) -> dict[str, Any]:
        return self.save(self.defaults())

    def resolve_source(self, source_id: str | None) -> dict[str, Any]:
        """Resolve one camera/source id to a configured intersection.

        Unmapped or unavailable sources fall back to the configured active
        intersection so existing single-source V025 behavior remains stable.
        """

        with self._lock:
            config = self._load_locked()
            source = str(source_id or "").strip()
            if source:
                for intersection in config["intersections"]:
                    if source in intersection["source_ids"]:
                        return self._resolved_locked(config, intersection, source, matched=True)
            active = next(
                item for item in config["intersections"] if item["id"] == config["active_intersection_id"]
            )
            return self._resolved_locked(config, active, source or None, matched=False)

    def context(self, intersection_id: str | None = None) -> dict[str, Any]:
        with self._lock:
            config = self._load_locked()
            target_id = str(intersection_id or config["active_intersection_id"])
            intersection = next((item for item in config["intersections"] if item["id"] == target_id), None)
            if intersection is None:
                raise AppError(
                    ErrorCode.TRAFFIC_NETWORK_INVALID,
                    "The requested intersection is not configured.",
                    status_code=404,
                    details={"intersection_id": target_id},
                )
            return self._context_locked(config, intersection)

    def _load_locked(self) -> dict[str, Any]:
        if self._cache is not None:
            return self._cache
        if not self._config_path.is_file():
            self._cache = self._validate(self.defaults())
            return self._cache
        try:
            raw = read_json(self._config_path)
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            logger.exception("Intersection network configuration read failed")
            raise AppError(
                ErrorCode.TRAFFIC_NETWORK_READ_FAILED,
                "Failed to read the intersection network configuration.",
                status_code=500,
            ) from exc
        self._cache = self._validate(raw)
        return self._cache

    @classmethod
    def _validate(cls, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            cls._invalid("Intersection network configuration must be an object.")
        if int(payload.get("schema_version", 0) or 0) != 1:
            cls._invalid("Unsupported intersection network schema_version.")

        raw_intersections = payload.get("intersections")
        if not isinstance(raw_intersections, list) or not 1 <= len(raw_intersections) <= MAX_INTERSECTIONS:
            cls._invalid(f"intersections must contain 1-{MAX_INTERSECTIONS} entries.")

        intersections: list[dict[str, Any]] = []
        intersection_ids: set[str] = set()
        claimed_sources: dict[str, str] = {}
        for raw in raw_intersections:
            if not isinstance(raw, dict):
                cls._invalid("Each intersection must be an object.")
            intersection_id = cls._validate_id(raw.get("id"), "intersection id")
            if intersection_id in intersection_ids:
                cls._invalid("Intersection ids must be unique.", {"intersection_id": intersection_id})
            intersection_ids.add(intersection_id)

            label = str(raw.get("label") or "").strip()
            if not 1 <= len(label) <= 120:
                cls._invalid("Intersection labels must contain 1-120 characters.", {"intersection_id": intersection_id})

            source_ids = cls._string_id_list(raw.get("source_ids", []), "source_ids", MAX_SOURCE_IDS)
            for source_id in source_ids:
                previous = claimed_sources.get(source_id)
                if previous is not None:
                    cls._invalid(
                        "A source_id may belong to only one intersection.",
                        {"source_id": source_id, "intersections": [previous, intersection_id]},
                    )
                claimed_sources[source_id] = intersection_id

            zone_ids = cls._string_id_list(raw.get("zone_ids", []), "zone_ids", MAX_ZONE_IDS)
            signal_profile = str(raw.get("signal_profile") or "Normal").strip()
            if not 1 <= len(signal_profile) <= 64:
                cls._invalid("signal_profile must contain 1-64 characters.", {"intersection_id": intersection_id})

            intersections.append(
                {
                    "id": intersection_id,
                    "label": label,
                    "enabled": bool(raw.get("enabled", True)),
                    "source_ids": source_ids,
                    "zone_ids": zone_ids,
                    "signal_profile": signal_profile,
                }
            )

        active_id = cls._validate_id(payload.get("active_intersection_id"), "active_intersection_id")
        if active_id not in intersection_ids:
            cls._invalid("active_intersection_id must identify a configured intersection.")

        raw_links = payload.get("links", [])
        if not isinstance(raw_links, list) or len(raw_links) > MAX_LINKS:
            cls._invalid(f"links must be a list with at most {MAX_LINKS} entries.")
        links: list[dict[str, Any]] = []
        link_ids: set[str] = set()
        for raw in raw_links:
            if not isinstance(raw, dict):
                cls._invalid("Each network link must be an object.")
            link_id = cls._validate_id(raw.get("id"), "link id")
            if link_id in link_ids:
                cls._invalid("Network link ids must be unique.", {"link_id": link_id})
            link_ids.add(link_id)

            source_id = cls._validate_id(raw.get("source_intersection_id"), "source_intersection_id")
            destination_id = cls._validate_id(raw.get("destination_intersection_id"), "destination_intersection_id")
            if source_id not in intersection_ids or destination_id not in intersection_ids:
                cls._invalid(
                    "Network links must reference configured intersections.",
                    {"link_id": link_id, "source": source_id, "destination": destination_id},
                )
            if source_id == destination_id:
                cls._invalid("A network link cannot point an intersection to itself.", {"link_id": link_id})

            source_approach = cls._short_text(raw.get("source_approach"), "source_approach", link_id)
            destination_approach = cls._short_text(raw.get("destination_approach"), "destination_approach", link_id)
            try:
                travel_time = float(raw.get("travel_time_seconds", 10.0))
            except (TypeError, ValueError) as exc:
                raise AppError(
                    ErrorCode.TRAFFIC_NETWORK_INVALID,
                    "travel_time_seconds must be numeric.",
                    status_code=422,
                    details={"link_id": link_id},
                ) from exc
            if not 0.1 <= travel_time <= 300.0:
                cls._invalid("travel_time_seconds must be between 0.1 and 300 seconds.", {"link_id": link_id})

            links.append(
                {
                    "id": link_id,
                    "enabled": bool(raw.get("enabled", True)),
                    "source_intersection_id": source_id,
                    "destination_intersection_id": destination_id,
                    "source_approach": source_approach,
                    "destination_approach": destination_approach,
                    "travel_time_seconds": round(travel_time, 1),
                }
            )

        return {
            "schema_version": 1,
            "active_intersection_id": active_id,
            "intersections": intersections,
            "links": links,
        }

    @staticmethod
    def _validate_id(value: Any, label: str) -> str:
        normalized = str(value or "").strip()
        if not ID_PATTERN.fullmatch(normalized):
            raise AppError(
                ErrorCode.TRAFFIC_NETWORK_INVALID,
                f"{label} must start with a letter and contain 1-64 letters, numbers, dots, dashes, or underscores.",
                status_code=422,
                details={label.replace(" ", "_"): normalized},
            )
        return normalized

    @classmethod
    def _string_id_list(cls, value: Any, label: str, maximum: int) -> list[str]:
        if not isinstance(value, list) or len(value) > maximum:
            cls._invalid(f"{label} must be a list with at most {maximum} entries.")
        normalized: list[str] = []
        for item in value:
            item_id = str(item or "").strip()
            if not TOKEN_PATTERN.fullmatch(item_id):
                cls._invalid(
                    f"{label} entries must contain 1-64 letters, numbers, dots, dashes, or underscores.",
                    {label: item_id},
                )
            if item_id not in normalized:
                normalized.append(item_id)
        return normalized

    @classmethod
    def _short_text(cls, value: Any, label: str, link_id: str) -> str:
        text = str(value or "").strip()
        if not 1 <= len(text) <= 64:
            cls._invalid(f"{label} must contain 1-64 characters.", {"link_id": link_id})
        return text

    @staticmethod
    def _invalid(message: str, details: dict[str, Any] | None = None) -> None:
        raise AppError(ErrorCode.TRAFFIC_NETWORK_INVALID, message, status_code=422, details=details or {})

    def _resolved_locked(
        self,
        config: dict[str, Any],
        intersection: dict[str, Any],
        source_id: str | None,
        *,
        matched: bool,
    ) -> dict[str, Any]:
        return {
            "intersection_id": intersection["id"],
            "intersection_label": intersection["label"],
            "source_id": source_id,
            "source_mapping_matched": matched,
            "active_intersection": intersection["id"] == config["active_intersection_id"],
            "network_context": self._context_locked(config, intersection),
        }

    @staticmethod
    def _context_locked(config: dict[str, Any], intersection: dict[str, Any]) -> dict[str, Any]:
        neighbors: list[dict[str, Any]] = []
        for link in config["links"]:
            if link["source_intersection_id"] == intersection["id"]:
                neighbors.append(
                    {
                        "link_id": link["id"],
                        "direction": "outbound",
                        "neighbor_intersection_id": link["destination_intersection_id"],
                        "local_approach": link["source_approach"],
                        "neighbor_approach": link["destination_approach"],
                        "travel_time_seconds": link["travel_time_seconds"],
                        "enabled": link["enabled"],
                    }
                )
            elif link["destination_intersection_id"] == intersection["id"]:
                neighbors.append(
                    {
                        "link_id": link["id"],
                        "direction": "inbound",
                        "neighbor_intersection_id": link["source_intersection_id"],
                        "local_approach": link["destination_approach"],
                        "neighbor_approach": link["source_approach"],
                        "travel_time_seconds": link["travel_time_seconds"],
                        "enabled": link["enabled"],
                    }
                )
        neighbors.sort(key=lambda item: (item["neighbor_intersection_id"], item["link_id"], item["direction"]))
        return {
            "intersection": deepcopy(intersection),
            "neighbors": neighbors,
            "neighbor_count": len(neighbors),
            "cooperative_control_active": False,
            "emergency_priority_active": False,
            "prototype_only": True,
            "scope_note": "Topology metadata only; V025 does not coordinate signal timing between intersections.",
        }

    def relative_config_path(self) -> str:
        try:
            return str(self._config_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
        except ValueError:
            return str(self._config_path)


intersection_network_service = IntersectionNetworkService()
