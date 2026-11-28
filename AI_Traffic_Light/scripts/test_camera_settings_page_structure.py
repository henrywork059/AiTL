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
    assert "!cameraSettingsView && showSimulationTools && (" in page
    assert page.count("fetchRemoteCameraStatus()") == 1
    for call in ("saveRemoteCamera(", "selectRemoteCamera(", "connectRemoteCamera(",
                 "startRemoteCamera(", "stopRemoteCamera(", "deleteRemoteCamera("):
        assert call in page, call
    assert "key={cameraSettingsView ? remote?.active_source_id" in page
    assert "selectedSimulation && status?.simulation_enabled" in page
    assert "selectedSaved && !selectedSimulation && selectedStreaming && !status?.simulation_enabled" in page
    assert "Measured stream FPS" in page and "Frame age" in page
    assert "cameraIndicator(camera)" in page
    assert "Add simulation pair" in page
    assert "simulation_camera_b" in page
    assert "simulation_camera_d" in page
    assert "nextSimulationPair" in page
    assert "Add second simulation pair" in page
    assert "saveSimulationCamera(nextSimulationPair)" in page
    assert "New camera type" in page
    assert "showSimulationTools && selectedSimulation && <SimulationControls" in page
    for marker in ("camera.streaming", "camera.stream_connected", "camera.connected",
                   "camera.device_reachable", "camera.paused_for_simulation"):
        assert marker in page, marker
    for state in ("Streaming", "Reconnecting", "Paused", "Connected", "Unreachable", "Saved"):
        assert f'label: "{state}"' in page, state
    assert "visibleCameras.map((camera) => {" in page
    assert 'showSimulationTools || camera.kind !== "simulation"' in page
    assert "camera-status-entry" in page and "camera.selected" in page
    assert 'role="list"' in page and 'role="listitem"' in page
    assert 'className="camera-fold"' in page
    assert 'className="panel compact-panel training-form camera-fold"' in page
    assert 'className="panel compact-panel camera-fold"' in page
    assert "Manage IP addresses and connections" in page
    # The ESP-only form uses effectiveCameraType so concealed simulation tools
    # cannot accidentally select the simulator save path.
    assert 'const effectiveCameraType = showSimulationTools ? newCameraType : "esp32"' in page
    esp_form = page.split('effectiveCameraType === "esp32" && <details className="camera-fold" open>', 1)[1].split("</details>", 1)[0]
    assert 'effectiveCameraType === "simulation"' not in esp_form
    assert esp_form.count('disabled={busy || changingMode || !host.trim() || !sourceId.trim() || selectedStreaming || Boolean(setupError)}') == 2
    assert 'disabled={busy || !readyToStart}' in page
    assert 'disabled={busy || !selectedActive || !selectedStreaming}' in page
    assert 'remote?.active_source_id === selectedId' in page
    assert 'epoch !== actionEpochRef.current' in page
    assert 'loadSelectedProfile(savedStatus)' in page
    assert page.index('loadSelectedProfile(savedStatus)') < page.index('const next = await connectRemoteCamera(')
    assert 'Retry connection' in page and 'Saved profile retained' in page
    assert 'label: "Stale"' in page and 'label: "Waiting for frame"' in page
    assert 'selectedProfile?.device_contract?.health.frame_fresh === true' in page
    assert 'Number.isInteger(value)' in page and 'Use a private LAN IP address' in page
    assert 'That IP address is already assigned to another saved camera.' in page
    assert 'Camera status unavailable. Check PC Studio backend.' in page
    assert 'matchesSelectedCameraFrame(status, selectedId' in page
    assert 'registryCurrent && camera.selected' in page
    assert 'onStatusChange(null);' in page
    assert 'Camera action completed, but preview status refresh failed' in page
    assert "Detailed camera & stream status" in page
    assert "Each saved ESP keeps its own OV2640 settings" not in page
    assert "V037 R6" not in page
    assert '{!cameraSettingsView && <FunctionChecklist area="Camera" />}' in page
    print("[PASS] Camera Settings status strip, collapsible controls, navigation and preview are wired")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
