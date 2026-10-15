"""V0418: camera selection, simulation feed and region controls remain separated."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "apps" / "pc-studio" / "frontend" / "src"
BACKEND = ROOT / "apps" / "pc-studio" / "backend" / "app" / "services"


def ui(path: str) -> str:
    return (FRONTEND / path).read_text(encoding="utf-8")


def css_rule(css: str, selector: str) -> str:
    found = list(re.finditer(re.escape(selector) + r"\s*\{([^{}]*)\}", css))
    assert found, f"Missing selector {selector}"
    return found[-1].group(1)


def main() -> None:
    cameras = ui("pages/CameraSourcesPage.tsx")
    saved = cameras.split('<div className="camera-status-strip-items" role="list">', 1)[1].split("!remote &&", 1)[0]
    assert 'role="listitem"' in saved
    assert 'type="button"' in saved
    assert 'onClick={() => void chooseSavedCamera(camera.source_id)}' in saved
    assert 'aria-pressed={camera.selected}' in saved
    assert 'disabled={busy}' in saved
    assert 'className={`camera-status-entry' in saved
    assert "const next = await selectRemoteCamera(nextSourceId)" in cameras
    assert "loadSelectedProfile(next)" in cameras

    editor = ui("pages/CrosswalkRegionEditor.tsx")
    assert 'role="group" aria-label="Camera side"' in editor
    assert 'aria-pressed={side === "camera_side_a_id"}' in editor
    assert 'aria-pressed={side === "camera_side_b_id"}' in editor
    assert 'onClick={() => setSide("camera_side_a_id")}' in editor
    assert 'onClick={() => setSide("camera_side_b_id")}' in editor
    assert "<label>Camera side" not in editor
    assert 'fill="none"' in editor and 'fillOpacity={0}' in editor
    assert "onVertexDown(event, region.id, index)" in editor
    region_css = ui("pages/crosswalkRegionEditor.css")
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in css_rule(region_css, ".crosswalk-region-side-toggle")
    assert "border-color: var(--color-primary);" in css_rule(region_css, '.crosswalk-region-side-toggle button[aria-pressed="true"]')
    for selector in (".crosswalk-region-polygon", ".crosswalk-region-polygon.is-selected"):
        assert "fill: none;" in css_rule(region_css, selector)

    shared = ui("styles/components.css")
    pill = css_rule(shared, ".status-pill,\n.status-placeholder")
    for value in ("display: inline-flex;", "align-items: center;", "justify-content: center;", "text-align: center;"):
        assert value in pill
    entry = css_rule(shared, ".camera-status-entry")
    assert "cursor: pointer;" in entry
    assert ".camera-status-entry:focus-visible" in shared

    source = (BACKEND / "camera_frames.py").read_text(encoding="utf-8")
    render = source.split("def _refresh_simulation_locked(", 1)[1].split('encoded_ok, encoded = cv2.imencode(".png", canvas)', 1)[0]
    agents = source.split("def _initialize_agents_locked(", 1)[1].split("def _advance_simulation_locked(", 1)[0]
    assert 'vehicle_type = "car"' in agents
    assert 'vehicle_type = "bus"' not in agents
    assert "cv2.putText(" not in render
    assert "_draw_signal_heads(" not in render
    assert "self._simulation_signal_state_locked()" in source  # real signal policy still runs
    assert "_advance_pedestrians_locked(step)" in source
    assert "_advance_vehicles_locked(step)" in source

    backup = ROOT / "docs" / "backups" / "V0417_PRE_V0418_CODE.md"
    assert backup.is_file()
    text = backup.read_text(encoding="utf-8")
    assert "Error-prevention reminders" in text
    assert "85eb480a09be8d140ef065eec073e88ef3a5b9d7" in text
    for path in ("camera_frames.py", "CameraSourcesPage.tsx", "CrosswalkRegionEditor.tsx"):
        assert path in text
    print("[PASS] Saved camera cards select via existing camera service")
    print("[PASS] Region camera sides toggle, polygons transparent and selected outline retained")
    print("[PASS] Simulation frame omits banners and signal drawings but keeps traffic policy")
    print("[PASS] Status pills centered and pre-patch source backup available")


if __name__ == "__main__":
    main()
