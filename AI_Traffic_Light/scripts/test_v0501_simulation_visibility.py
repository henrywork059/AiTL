"""Focused source regression: brand-gated simulation controls."""
from pathlib import Path
SRC = Path(__file__).resolve().parents[1] / "apps/pc-studio/frontend/src"
def main():
    app = (SRC / "App.tsx").read_text(encoding="utf-8")
    shell = (SRC / "layout/AppShell.tsx").read_text(encoding="utf-8")
    assert 'const [showSimulationTools, setShowSimulationTools] = useState(false)' in app
    assert 'setShowSimulationTools((current) => !current)' in app
    assert 'showSimulationTools ? <SimulationLabPage />' in app
    assert 'aria-pressed={showSimulationTools}' in shell
    assert 'showSimulationTools || navPage.id !== "simulation_lab"' in shell
    for page in ("CameraSourcesPage", "CrosswalksPage", "JunctionNetworkPage", "CrosswalkRegionEditor"):
        assert "showSimulationTools" in (SRC / "pages" / (page+".tsx")).read_text(encoding="utf-8")
    camera = (SRC / "pages/CameraSourcesPage.tsx").read_text(encoding="utf-8")
    assert 'const effectiveCameraType = showSimulationTools ? newCameraType : "esp32"' in camera
    print("[PASS] Simulation visibility source guards")
if __name__ == "__main__":
    main()
