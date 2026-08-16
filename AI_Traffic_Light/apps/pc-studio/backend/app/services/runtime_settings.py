from __future__ import annotations

import os
from pathlib import Path
from threading import Lock
from typing import Any

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.core.json_store import read_json, write_json_atomic
from app.core.logging_config import get_logger, set_runtime_log_level

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_SETTINGS_PATH = PROJECT_ROOT / "config" / "runtime_settings.json"
DEFAULT_SETTINGS: dict[str, Any] = {
    "default_confidence": 0.10,
    "live_poll_interval_ms": 500,
    "training_patience": 5,
    "log_level": "INFO",
}
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}


class RuntimeSettingsService:
    """Persist the small set of prototype runtime settings that affect active features."""

    def __init__(self, *, settings_path: Path | None = None) -> None:
        configured = os.environ.get("AITL_RUNTIME_SETTINGS")
        self._settings_path = Path(configured) if configured else (settings_path or DEFAULT_SETTINGS_PATH)
        self._settings_path = self._settings_path.expanduser().resolve()
        self._lock = Lock()

    def get(self) -> dict[str, Any]:
        with self._lock:
            if not self._settings_path.is_file():
                settings = dict(DEFAULT_SETTINGS)
            else:
                try:
                    payload = read_json(self._settings_path)
                except (OSError, ValueError) as exc:
                    raise AppError(
                        ErrorCode.SETTINGS_READ_FAILED,
                        "Failed to read the persisted runtime settings.",
                        status_code=500,
                    ) from exc
                settings = {**DEFAULT_SETTINGS, **(payload if isinstance(payload, dict) else {})}
            settings = self._validate(settings, error_code=ErrorCode.SETTINGS_READ_FAILED)
        set_runtime_log_level(settings["log_level"])
        return settings

    def save(self, settings: dict[str, Any]) -> dict[str, Any]:
        validated = self._validate(settings, error_code=ErrorCode.SETTINGS_WRITE_FAILED)
        try:
            with self._lock:
                write_json_atomic(self._settings_path, validated)
        except (OSError, TypeError, ValueError) as exc:
            logger.exception("Runtime settings save failed", extra={"error_code": ErrorCode.SETTINGS_WRITE_FAILED.value})
            raise AppError(
                ErrorCode.SETTINGS_WRITE_FAILED,
                "Failed to save runtime settings.",
                status_code=500,
            ) from exc
        set_runtime_log_level(validated["log_level"])
        logger.info("Runtime settings saved", extra={"log_level": validated["log_level"]})
        return validated

    @staticmethod
    def _validate(settings: dict[str, Any], *, error_code: ErrorCode) -> dict[str, Any]:
        try:
            confidence = float(settings.get("default_confidence", 0.10))
            poll_ms = int(settings.get("live_poll_interval_ms", 500))
            patience = int(settings.get("training_patience", 5))
            log_level = str(settings.get("log_level", "INFO")).upper()
        except (TypeError, ValueError) as exc:
            raise AppError(error_code, "Runtime settings contain invalid values.", status_code=422) from exc
        if not 0.01 <= confidence <= 1.0 or not 250 <= poll_ms <= 5000 or not 1 <= patience <= 100:
            raise AppError(
                error_code,
                "Runtime settings are outside the supported prototype limits.",
                status_code=422,
            )
        if log_level not in VALID_LOG_LEVELS:
            raise AppError(
                error_code,
                "log_level must be DEBUG, INFO, WARNING, or ERROR.",
                status_code=422,
            )
        return {
            "default_confidence": round(confidence, 2),
            "live_poll_interval_ms": poll_ms,
            "training_patience": patience,
            "log_level": log_level,
        }


runtime_settings_service = RuntimeSettingsService()
