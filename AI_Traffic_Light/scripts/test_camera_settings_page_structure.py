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
    assert '"camera_settings", "dataset_capture"' in app

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
    print("[PASS] Camera Settings navigation, saved ESP selection, preview and controls are wired")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
