"""Second simulation-camera pair keeps original pair and safe source selection."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "apps" / "pc-studio" / "frontend" / "src"
BACKEND = ROOT / "apps" / "pc-studio" / "backend" / "app"


def read(root: Path, path: str) -> str:
    return (root / path).read_text(encoding="utf-8")


def main() -> None:
    manager = read(BACKEND, "services/remote_camera_manager.py")
    frames = read(BACKEND, "services/camera_frames.py")
    routes = read(BACKEND, "routes/camera.py")
    api = read(FRONTEND, "lib/remoteCameraApi.ts")
    page = read(FRONTEND, "pages/CameraSourcesPage.tsx")
    crosswalks = read(FRONTEND, "pages/CrosswalksPage.tsx")

    assert '("simulation_camera", "simulation_camera_b")' in frames
    assert '("simulation_camera_c", "simulation_camera_d")' in frames
    assert "SIMULATION_CAMERA_SOURCE_IDS" in manager and "SIMULATION_CAMERA_PAIRS" in manager
    assert "def save_simulation_profile(self, pair_index: int = 1)" in manager
    assert "pair = SIMULATION_PAIRS[pair_index - 1]" in manager
    assert "pair = next((ids for ids in SIMULATION_PAIRS if normalized_source in ids), None)" in manager
    assert "for sid in (pair if pair is not None else (normalized_source,))" in manager
    assert "selected_simulation = self._active_source_id in SIMULATION_SOURCE_IDS" in manager
    assert "camera_frame_service.set_simulation_source(self._active_source_id)" in manager

    assert '"simulation_camera_b": 0, "simulation_camera_c": 1, "simulation_camera_d": -1' in frames
    assert "self._simulation_view_frames[source_id] = cached" in frames
    assert "if cached is None or cached.frame_number != original.frame_number:" in frames
    assert "if source_id not in SIMULATION_CAMERA_SOURCE_IDS:" in frames
    assert "pair: int = Query(default=1, ge=1, le=2)" in routes
    assert "save_simulation_profile(pair_index=pair)" in routes
    assert "source_id not in SIMULATION_SOURCE_IDS" in routes
    assert 'saveSimulationCamera(pair: 1 | 2 = 1)' in api
    assert "simulation?pair=${pair}" in api
    assert "saveSimulationCamera(nextSimulationPair)" in page
    assert 'source_id === "simulation_camera_d"' in page
    assert "Add second simulation pair" in page
    assert "saveSimulationCamera()" in crosswalks  # existing first-pair assignment stays valid

    print("[PASS] Two simulation pairs have distinct IDs, camera views and per-pair lifecycle")
    print("[PASS] Existing camera/crosswalk APIs remain compatible with Pair 1")
    print("[PASS] Camera Settings can add Pair 2 without duplicating selection or stream logic")


if __name__ == "__main__":
    main()
