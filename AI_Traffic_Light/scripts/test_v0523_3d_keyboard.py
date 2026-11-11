"""Static 3D interface contract; frontend build tests TypeScript and JSX."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "apps/pc-studio/frontend/src/components/SimulationCamera3D.tsx"
CSS = ROOT / "apps/pc-studio/frontend/src/components/simulationCamera3D.css"


def main() -> None:
    code = COMPONENT.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    assert "function keyboardCamera(event: KeyboardEvent<HTMLDivElement>)" in code
    for key in ("ArrowLeft:", "ArrowRight:", "ArrowUp:", "ArrowDown:", '"+"', '"-"', "Home:"):
        assert key in code, key
    assert "tabIndex={editing ? undefined : 0}" in code
    assert "onKeyDown={editing ? undefined : keyboardCamera}" in code
    assert "event.preventDefault()" in code
    assert "sim3d-viewport:focus-visible" in css
    # The shared camera-mirror helper moved out of this presentation component.
    motion = (ROOT / "apps/pc-studio/frontend/src/components/simulation3dMotion.ts").read_text(encoding="utf-8")
    assert "export function simulationSourcePoint(" in motion
    assert "simulationSourcePoint(" in code
    assert "editing={!perspectiveView}" in (ROOT / "apps/pc-studio/frontend/src/pages/CrosswalkRegionEditor.tsx").read_text(encoding="utf-8")
    print("[PASS] keyboard-only 3D camera controls and non-editable region-safe view")


if __name__ == "__main__":
    main()
