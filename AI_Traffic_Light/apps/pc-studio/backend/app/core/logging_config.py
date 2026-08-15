from collections import deque
from datetime import datetime, timezone
import logging
from threading import Lock
from typing import Any
import sys

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
_RECENT_LOGS: deque[dict[str, Any]] = deque(maxlen=500)
_RECENT_LOG_LOCK = Lock()


class RecentLogHandler(logging.Handler):
    """Keep a small in-memory copy of project log records for the PC Studio log page."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            entry = {
                "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec="seconds"),
                "level": record.levelname.lower(),
                "code": getattr(record, "error_code", "ATL-LOG-EVENT"),
                "scope": record.name.removeprefix("aitl.app.").removeprefix("aitl."),
                "message": record.getMessage(),
                "request_id": getattr(record, "request_id", None),
            }
            with _RECENT_LOG_LOCK:
                _RECENT_LOGS.append(entry)
        except Exception:
            self.handleError(record)


def configure_logging(level: str = "INFO") -> None:
    """Configure console logging and the bounded PC Studio recent-log buffer."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter(LOG_FORMAT))
    recent = RecentLogHandler(level=logging.DEBUG)
    logging.basicConfig(level=numeric_level, handlers=[console, recent], force=True)


def set_runtime_log_level(level: str) -> None:
    """Apply a validated runtime log level without restarting the backend."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.getLogger().setLevel(numeric_level)


def recent_log_entries(limit: int = 100) -> list[dict[str, Any]]:
    """Return newest project log entries first."""
    with _RECENT_LOG_LOCK:
        items = list(_RECENT_LOGS)
    return [dict(item) for item in reversed(items[-max(1, min(limit, 200)):])]


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced project logger."""
    if name.startswith("app."):
        return logging.getLogger(f"aitl.{name}")
    return logging.getLogger(f"aitl.app.{name}")
