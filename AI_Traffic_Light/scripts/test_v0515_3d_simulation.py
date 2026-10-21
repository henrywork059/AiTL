"""Offline regression for the optional Simulation Lab 3D replay wiring and boundaries."""
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "apps/pc-studio/frontend/src"


def main() -> None:
    page = (SRC / "pages/SimulationLabPage.tsx").read_text(encoding="utf-8")
    scene = (SRC / "components/SimulationScene3D.tsx").read_text(encoding="utf-8")
    styles = (SRC / "components/simulationScene3D.css").read_text(encoding="utf-8")

    assert 'import { SimulationScene3D }' in page
    assert '["scene", "3D Replay"]' in page
    assert '"scene", "summary", "waiting"' in page  # keyboard tab order
    assert "<SimulationScene3D samples={sampleSource} mode={sampleMode} />" in page
    assert 'setSampleMode("fixed")' in page and 'setSampleMode("adaptive")' in page

    for token in ("vehicle_queue", "pedestrian_queue", "phase_key", "phase",
                  "setIndex", "setPlaying", "setAngle", "setTilt", "setZoom",
                  "window.clearInterval(timer)", "illustrative"):
        assert token in scene, token
    assert "fetch(" not in scene and "setCameraSimulationSettings" not in scene
    assert "transform-style:preserve-3d" in styles
    assert "perspective:900px" in styles
    print("[PASS] Simulation Lab optional 3D replay wiring and presentation boundary")


if __name__ == "__main__":
    main()
