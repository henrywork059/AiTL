"""Focused static wiring regression for the dedicated ESP Camera Settings page."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "apps" / "pc-studio" / "frontend" / "src"


def main() -> int:
    app = (ROOT / "App.tsx").read_text(encoding="utf-8")
    page = (ROOT / "pages" / "CameraSourcesPage.tsx").read_text(encoding="utf-8")
    nav = (ROOT / "constants" / "appNavigation.ts").read_text(encoding="utf-8")
    types = (ROOT / "types" / "app.ts").read_text(encoding="utf-8")

    assert '"camera_settings"' in types
    assert 'camera_settings: { id: "camera_settings"' in nav
    assert "PAGE_DETAILS.camera_settings" in nav
    assert 'case "camera_settings":' in app
    assert '<CameraSettingsPage' in app
    poll_pages = app.split("const CAMERA_POLL_PAGES:", 1)[1].split("];", 1)[0]
    assert all(f'"{page}"' in poll_pages for page in ("camera_settings", "dataset_capture"))

    # Both routes share one camera registry, rather than duplicating state or transport.
    assert 'view="settings"' in page
    assert "cameraSettingsView && (" in page
    assert "!cameraSettingsView && (" in page
    assert page.count("fetchRemoteCameraStatus()") == 1
    for call in ("saveRemoteCamera(", "selectRemoteCamera(", "connectRemoteCamera(",
                 "startRemoteCamera(", "stopRemoteCamera(", "deleteRemoteCamera("):
        assert call in page, call
    assert "key={cameraSettingsView ? remote?.active_source_id" in page
    assert "selectedSaved && selectedStreaming && !status?.simulation_enabled" in page
    assert "Measured stream FPS" in page and "Frame age" in page
    assert "cameraIndicator(camera)" in page
    for marker in ("camera.streaming", "camera.stream_connected", "camera.connected",
                   "camera.device_reachable", "camera.paused_for_simulation"):
        assert marker in page, marker
    for state in ("Streaming", "Reconnecting", "Paused", "Connected", "Unreachable", "Saved"):
        assert f'label: "{state}"' in page, state
    assert "remote?.cameras.map((camera) => {" in page
    assert "camera-status-entry" in page and "camera.selected" in page
    assert 'role="list"' in page and 'role="listitem"' in page
    assert 'className="camera-fold"' in page
    assert 'className="panel compact-panel training-form camera-fold"' in page
    assert 'className="panel compact-panel camera-fold"' in page
    assert "Manage IP addresses and connections" in page
    assert "Detailed camera & stream status" in page
    assert "Each saved ESP keeps its own OV2640 settings" not in page
    assert "V037 R6" not in page
    assert '{!cameraSettingsView && <FunctionChecklist area="Camera" />}' in page
    print("[PASS] Camera Settings status strip, collapsible controls, navigation and preview are wired")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
