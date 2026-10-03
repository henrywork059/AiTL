"""Static regression checks for single-flight frontend polling."""
from __future__ import annotations

from pathlib import Path

from check_structure import SERIAL_POLLING_SURFACES

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = PROJECT_ROOT / "apps" / "pc-studio" / "frontend" / "src"
HOOK_PATH = FRONTEND_ROOT / "lib" / "useSerialPolling.ts"


def read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def main() -> int:
    hook = HOOK_PATH.read_text(encoding="utf-8")

    for marker in (
        "inFlightRef",
        "const runNow = useCallback",
        "const waitForIdle = useCallback",
        "await waitForIdle()",
        "await runNow()",
        "window.setTimeout",
        "finally",
        "return { runNow, waitForIdle }",
    ):
        assert marker in hook, marker
    assert "window.setInterval" not in hook

    checked: list[str] = []
    for relative_path in SERIAL_POLLING_SURFACES:
        content = read(relative_path)
        assert "useSerialPolling" in content, f"{relative_path} must use the shared serial polling hook"
        assert "window.setInterval" not in content, f"{relative_path} must not use overlapping setInterval polling"
        checked.append(relative_path)

    live_ai = read("apps/pc-studio/frontend/src/pages/LiveAiPage.tsx")
    assert "pollDetections" not in live_ai
    assert "window.setTimeout" not in live_ai
    assert live_ai.count("useSerialPolling(") >= 2

    logs = read("apps/pc-studio/frontend/src/pages/LogsPage.tsx")
    assert "runNow: refreshLogs" in logs
    assert "void refreshLogs()" in logs

    dataset = read("apps/pc-studio/frontend/src/pages/DatasetCapturePage.tsx")
    assert "waitForIdle: waitForDatasetStatusIdle" in dataset
    assert "enabled: !saving && !deleting" in dataset
    assert dataset.count("await waitForDatasetStatusIdle()") == 2

    analytics = read("apps/pc-studio/frontend/src/pages/TrafficAnalyticsPage.tsx")
    assert "runNow: refreshAnalytics" in analytics
    assert "waitForIdle: waitForAnalyticsIdle" in analytics
    assert "enabled: !clearing" in analytics
    assert "await waitForAnalyticsIdle()" in analytics

    training = read("apps/pc-studio/frontend/src/pages/TrainExportPage.tsx")
    assert "waitForIdle: waitForTrainingStatusIdle" in training
    assert "enabled: !starting" in training
    assert "await waitForTrainingStatusIdle()" in training

    app = read("apps/pc-studio/frontend/src/App.tsx")
    assert "waitForIdle: waitForCameraStatusIdle" in app
    assert "&& !changingCameraMode" in app
    assert "await waitForCameraStatusIdle()" in app

    print(f"[PASS] shared single-flight polling validated across {len(checked)} periodic frontend surfaces")
    print("[PASS] restarts/manual refreshes reuse one in-flight task")
    print("[PASS] mutations drain conflicting status polls before changing state")
    print("[PASS] Live AI duplicate page-local detection timer is removed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
