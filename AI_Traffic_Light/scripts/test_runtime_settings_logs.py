"""Checks for persistent runtime settings and the real recent-log buffer."""
from __future__ import annotations

import logging
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "apps" / "pc-studio" / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.logging_config import configure_logging, get_logger, recent_log_entries  # noqa: E402
from app.services.runtime_settings import RuntimeSettingsService  # noqa: E402


def main() -> int:
    configure_logging("DEBUG")
    logger = get_logger("test.runtime")
    logger.warning("runtime log buffer test", extra={"request_id": "req_test", "error_code": "ATL-TEST-001"})
    recent = recent_log_entries(20)
    assert any(item["message"] == "runtime log buffer test" for item in recent)
    matching = next(item for item in recent if item["message"] == "runtime log buffer test")
    assert matching["request_id"] == "req_test"
    assert matching["code"] == "ATL-TEST-001"

    with TemporaryDirectory(prefix="aitl-settings-test-") as temporary_directory:
        settings_path = Path(temporary_directory) / "runtime_settings.json"
        service = RuntimeSettingsService(settings_path=settings_path)
        defaults = service.get()
        assert defaults["default_confidence"] == 0.10
        saved = service.save({
            "default_confidence": 0.25,
            "live_poll_interval_ms": 750,
            "training_patience": 7,
            "log_level": "WARNING",
        })
        assert saved["training_patience"] == 7
        assert settings_path.is_file()
        assert RuntimeSettingsService(settings_path=settings_path).get()["live_poll_interval_ms"] == 750
        assert logging.getLogger().level == logging.WARNING

    print("[PASS] real backend logging records are captured with request/error metadata")
    print("[PASS] runtime settings persist and reload")
    print("[PASS] saved log level is applied without restarting")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
