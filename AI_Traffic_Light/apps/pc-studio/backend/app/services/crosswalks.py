"""Persist standalone crosswalk definitions without owning camera sessions."""
from __future__ import annotations

from copy import deepcopy
import json
import math
import os
from pathlib import Path
from threading import RLock
from typing import Any

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.core.json_store import read_json, write_json_atomic
from app.services.intersection_network import ID_PATTERN, TOKEN_PATTERN

DEFAULT_PATH = Path(__file__).resolve().parents[5] / "config" / "crosswalks.json"
CAMERA_FIELDS = ("camera_side_a_id", "camera_side_b_id")
MAX_CROSSWALKS = 32
MAX_REGIONS = 24
MAX_CROSSWALK_LINKS = 64
CROSSWALK_NETWORK_EDGES = ("1", "2", "3", "4")
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720


def _quadrilateral(points: Any) -> bool:
    """Four bounded integer vertices in a simple, non-degenerate convex outline."""
    if not isinstance(points, list) or len(points) != 4:
        return False
    if any(
        not isinstance(point, list) or len(point) != 2
        or any(type(value) is not int for value in point)
        or not 0 <= point[0] <= FRAME_WIDTH or not 0 <= point[1] <= FRAME_HEIGHT
        for point in points
    ):
        return False
    cross = [
        (points[(i + 1) % 4][0] - points[i][0]) * (points[(i + 2) % 4][1] - points[(i + 1) % 4][1])
        - (points[(i + 1) % 4][1] - points[i][1]) * (points[(i + 2) % 4][0] - points[(i + 1) % 4][0])
        for i in range(4)
    ]
    return all(value > 0 for value in cross) or all(value < 0 for value in cross)



class CrosswalkService:
    def __init__(self, *, config_path: Path | None = None) -> None:
        configured = os.environ.get("AITL_CROSSWALKS_CONFIG")
        self._path = Path(configured) if configured else (config_path or DEFAULT_PATH)
        self._path = self._path.expanduser().resolve()
        self._lock = RLock()
        self._cache: dict[str, Any] | None = None

    def get(self) -> dict[str, Any]:
        with self._lock:
            if self._cache is None:
                if not self._path.exists():
                    self._cache = {"schema_version": 1, "crosswalks": []}
                else:
                    try:
                        self._cache = self.validate(read_json(self._path))
                    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
                        raise AppError(ErrorCode.CROSSWALK_READ_FAILED, status_code=500) from exc
            return deepcopy(self._cache)

    def save(self, payload: dict[str, Any]) -> dict[str, Any]:
        valid = self.validate(payload)
        with self._lock:
            try:
                write_json_atomic(self._path, valid)
            except OSError as exc:
                raise AppError(ErrorCode.CROSSWALK_WRITE_FAILED, status_code=500) from exc
            self._cache = valid
        return deepcopy(valid)

    @staticmethod
    def validate(payload: Any) -> dict[str, Any]:
        def invalid(message: str) -> None:
            raise AppError(ErrorCode.CROSSWALK_INVALID, message, status_code=422)

        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            invalid("Crosswalk schema_version must be 1.")
        raw_items = payload.get("crosswalks")
        if not isinstance(raw_items, list) or len(raw_items) > MAX_CROSSWALKS:
            invalid(f"crosswalks must contain at most {MAX_CROSSWALKS} entries.")

        items: list[dict[str, Any]] = []
        identifiers: set[str] = set()
        for raw in raw_items:
            if not isinstance(raw, dict):
                invalid("Each crosswalk must be an object.")
            identity = raw.get("id")
            if not isinstance(identity, str) or not ID_PATTERN.fullmatch(identity):
                invalid("Crosswalk id must begin with a letter and contain up to 64 valid characters.")
            if identity in identifiers:
                invalid("Crosswalk ids must be unique.")
            identifiers.add(identity)
            label = raw.get("label")
            if not isinstance(label, str) or not 1 <= len(label.strip()) <= 120:
                invalid("Crosswalk name must contain 1–120 characters.")
            location = raw.get("location", "")
            if not isinstance(location, str) or len(location.strip()) > 160:
                invalid("Crosswalk location must contain at most 160 characters.")
            cameras: dict[str, str | None] = {}
            for field in CAMERA_FIELDS:
                value = raw.get(field)
                if value is None or value == "":
                    cameras[field] = None
                elif isinstance(value, str) and TOKEN_PATTERN.fullmatch(value):
                    cameras[field] = value
                else:
                    invalid(f"{field} must be a source ID or null.")
            if cameras["camera_side_a_id"] is not None and cameras["camera_side_a_id"] == cameras["camera_side_b_id"]:
                invalid("Use different cameras on Side A and Side B.")
            raw_regions = raw.get("regions", [])
            if not isinstance(raw_regions, list) or len(raw_regions) > MAX_REGIONS:
                invalid(f"regions must be a list of at most {MAX_REGIONS} entries per crosswalk.")
            regions: list[dict[str, Any]] = []
            region_ids: set[str] = set()
            for region in raw_regions:
                if not isinstance(region, dict):
                    invalid("Each region must be an object.")
                region_id = region.get("id")
                region_label = region.get("label")
                if not isinstance(region_id, str) or not ID_PATTERN.fullmatch(region_id) or region_id in region_ids:
                    invalid("Region ids must be valid and unique within the crosswalk.")
                if not isinstance(region_label, str) or not 1 <= len(region_label.strip()) <= 120:
                    invalid("Region name must contain 1–120 characters.")
                if not _quadrilateral(region.get("vertices")):
                    invalid("Region must have four bounded integer vertices forming a convex quadrilateral.")
                side = region.get("camera_side")
                if side not in (None, "a", "b"):
                    invalid("Region camera_side must be a, b or omitted.")
                side_vertices = region.get("vertices_by_side")
                if side_vertices is not None and (
                    not isinstance(side_vertices, dict) or not side_vertices
                    or any(key not in ("a", "b") or not _quadrilateral(points)
                           for key, points in side_vertices.items())
                ):
                    invalid("vertices_by_side must have valid convex quadrilaterals for Side A and/or B.")
                region_ids.add(region_id)
                regions.append({
                    "id": region_id,
                    "label": region_label.strip(),
                    "vertices": deepcopy(region["vertices"]),
                    **({"camera_side": side} if side is not None else {}),
                    **({"vertices_by_side": deepcopy(side_vertices)} if side_vertices is not None else {}),
                })
            items.append({"id": identity, "label": label.strip(), "location": location.strip(), **cameras, "regions": regions})
        result = {"schema_version": 1, "crosswalks": items}
        if "network" in payload:
            raw_network = payload["network"]
            if not isinstance(raw_network, dict):
                invalid("Crosswalk network must be an object.")
            raw_positions = raw_network.get("positions", {})
            if not isinstance(raw_positions, dict) or len(raw_positions) > MAX_CROSSWALKS:
                invalid("Network positions must be keyed by saved crosswalk IDs.")
            positions: dict[str, dict[str, float]] = {}
            for crosswalk_id, point in raw_positions.items():
                if not isinstance(crosswalk_id, str) or crosswalk_id not in identifiers or not isinstance(point, dict):
                    invalid("Network positions must reference saved crosswalks.")
                x, y = point.get("x"), point.get("y")
                if any(type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 100 for value in (x, y)):
                    invalid("Network position x/y must be finite percentages from 0 to 100.")
                positions[crosswalk_id] = {"x": round(float(x), 2), "y": round(float(y), 2)}
            raw_links = raw_network.get("links", [])
            if not isinstance(raw_links, list) or len(raw_links) > MAX_CROSSWALK_LINKS:
                invalid(f"Crosswalk network links must contain at most {MAX_CROSSWALK_LINKS} entries.")
            links: list[dict[str, str]] = []
            link_ids: set[str] = set()
            connected_edges: set[tuple[str, str, str, str]] = set()
            for link in raw_links:
                if not isinstance(link, dict):
                    invalid("Each crosswalk connection must be an object.")
                link_id = link.get("id")
                source_id = link.get("source_crosswalk_id")
                destination_id = link.get("destination_crosswalk_id")
                source_edge = link.get("source_edge")
                destination_edge = link.get("destination_edge")
                if not isinstance(link_id, str) or not ID_PATTERN.fullmatch(link_id) or link_id in link_ids:
                    invalid("Crosswalk connection IDs must be valid and unique.")
                if not isinstance(source_id, str) or not isinstance(destination_id, str) or source_id not in identifiers or destination_id not in identifiers or source_id == destination_id:
                    invalid("Connections must reference two different saved crossings.")
                if source_edge not in CROSSWALK_NETWORK_EDGES or destination_edge not in CROSSWALK_NETWORK_EDGES:
                    invalid("Connection edge labels must be 1, 2, 3 or 4.")
                endpoints = (source_id, source_edge, destination_id, destination_edge)
                opposite = (destination_id, destination_edge, source_id, source_edge)
                if endpoints in connected_edges or opposite in connected_edges:
                    invalid("Duplicate crosswalk connection.")
                link_ids.add(link_id)
                connected_edges.add(endpoints)
                links.append({
                    "id": link_id,
                    "source_crosswalk_id": source_id,
                    "destination_crosswalk_id": destination_id,
                    "source_edge": source_edge,
                    "destination_edge": destination_edge,
                })
            result["network"] = {"positions": positions, "links": links}
        return result


crosswalk_service = CrosswalkService()
