"""Persist standalone crosswalk definitions without owning camera sessions."""
from __future__ import annotations

from copy import deepcopy
import json
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
            items.append({"id": identity, "label": label.strip(), "location": location.strip(), **cameras})
        return {"schema_version": 1, "crosswalks": items}


crosswalk_service = CrosswalkService()
