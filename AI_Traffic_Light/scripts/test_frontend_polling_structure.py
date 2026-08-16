"""Static regression checks for V024 non-overlapping App-level polling."""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = PROJECT_ROOT / "apps" / "pc-studio" / "frontend" / "src" / "App.tsx"
HOOK_PATH = PROJECT_ROOT / "apps" / "pc-studio" / "frontend" / "src" / "lib" / "useSerialPolling.ts"


def main() -> int:
    app = APP_PATH.read_text(encoding="utf-8")
    hook = HOOK_PATH.read_text(encoding="utf-8")

    assert 'from "./lib/useSerialPolling"' in app
    assert app.count("useSerialPolling(") >= 2
    assert "window.setInterval" not in app

    assert "await taskRef.current()" in hook
    assert "finally" in hook
    assert "window.setTimeout" in hook
    assert "window.setInterval" not in hook
    assert hook.index("await taskRef.current()") < hook.index("finally")

    print("[PASS] App-level camera/live-context polling is routed through the shared serial hook")
    print("[PASS] serial polling schedules with setTimeout after async settlement and contains no setInterval")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
