"""Static regression checks for non-overlapping periodic frontend polling."""
from __future__ import annotations

from pathlib import Path

from check_structure import SERIAL_POLLING_SURFACES

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = PROJECT_ROOT / "apps" / "pc-studio" / "frontend" / "src" / "lib" / "useSerialPolling.ts"


def main() -> int:
    hook = HOOK_PATH.read_text(encoding="utf-8")

    assert "await taskRef.current()" in hook
    assert "finally" in hook
    assert "window.setTimeout" in hook
    assert "window.setInterval" not in hook
    assert hook.index("await taskRef.current()") < hook.index("finally")

    checked: list[str] = []
    for relative_path in SERIAL_POLLING_SURFACES:
        path = PROJECT_ROOT / relative_path
        content = path.read_text(encoding="utf-8")
        assert "useSerialPolling" in content, f"{relative_path} must use the shared serial polling hook"
        assert "window.setInterval" not in content, f"{relative_path} must not use overlapping setInterval polling"
        checked.append(relative_path)

    print(f"[PASS] shared serial polling hook validated across {len(checked)} periodic frontend surfaces")
    print("[PASS] periodic async polling schedules only after the previous task settles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
