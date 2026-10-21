"""Focused test: the simulated camera's 3D preview mirrors live agent state."""
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "apps/pc-studio/frontend/src"
BACKEND = ROOT / "apps/pc-studio/backend"
sys.path.insert(0, str(BACKEND))

from app.services.camera_frames import CameraFrameService, SIMULATION_CAMERA_SOURCE_IDS  # noqa: E402


def main() -> None:
    service = CameraFrameService()
    assert service.simulation_scene_for("simulation_camera") is None

    try:
        service.simulation_scene_for("esp32_cam_01")
        raise AssertionError("A physical camera was treated as simulation")
    except ValueError:
        pass

    service._simulation_seed = 42
    service.set_simulation(True)
    for source_id in SIMULATION_CAMERA_SOURCE_IDS:
        scene = service.simulation_scene_for(source_id)
        assert scene is not None and scene["source_id"] == source_id
        assert scene["width"] == 1280 and scene["height"] == 720
        assert scene["frame_number"] > 0
        assert scene["density"] == "normal"
        assert len(scene["vehicles"]) == 8
        assert len(scene["pedestrians"]) == 7
        assert scene["signal"]["vehicle_go"] is True
        assert scene["signal"]["pedestrian_walk"] is False
        assert service.simulation_frame_for(source_id) is not None
        with service._lock:
            assert scene["vehicles"][0]["x"] == round(service._vehicles[0].x, 2)
            assert scene["vehicles"][0]["width"] == service._vehicles[0].width
            assert scene["pedestrians"][0]["y"] == round(service._pedestrians[0].y, 2)

    service.configure_simulation(paused=True)
    stopped = service.simulation_scene_for("simulation_camera_b")
    time.sleep(0.55)
    still_stopped = service.simulation_scene_for("simulation_camera_b")
    assert stopped == still_stopped, "3D scene moved while simulation was paused"

    service.configure_simulation(density="busy")
    busy = service.simulation_scene_for("simulation_camera")
    assert busy and len(busy["vehicles"]) == 12 and len(busy["pedestrians"]) == 11

    service.set_simulation(False)
    assert service.simulation_scene_for("simulation_camera") is None

    page = (FRONTEND / "pages/CameraSourcesPage.tsx").read_text(encoding="utf-8")
    component = (FRONTEND / "components/SimulationCamera3D.tsx").read_text(encoding="utf-8")
    styles = (FRONTEND / "components/simulationCamera3D.css").read_text(encoding="utf-8")
    api = (FRONTEND / "lib/remoteCameraApi.ts").read_text(encoding="utf-8")
    route = (BACKEND / "app/routes/camera.py").read_text(encoding="utf-8")

    assert "use3dPreview" in page and "selectedSimulation" in page
    assert "<SimulationCamera3D key={sceneSourceId} sourceId={sceneSourceId} />" in page
    assert "showSimulationTools && status?.simulation_enabled" in page
    assert "<img" in page, "Physical ESP camera images must remain unchanged"
    assert "fetchSimulationScene(sourceId)" in component
    assert "useSerialPolling" in component and "restartKey: sourceId" in component
    assert "setScene(null)" in component, "Old source must not remain visible after failed polling"
    assert "setOrbit" in component and "setPitch" in component and "setZoom" in component
    assert "sim3d-world" in styles and "transform-style: preserve-3d" in styles
    assert "requestJsonStrict<SimulationScene>" in api
    assert '@router.get("/simulation/scene")' in route
    assert "source_id not in SIMULATION_SOURCE_IDS" in route
    assert "return ok(scene, request_id=request.state.request_id)" in route
    # Every LIVE synthetic camera image surface displays the shared 3D component.
    # Unmodified physical ESP frames and persisted image-coordinate editors remain usable.
    crosswalks = (FRONTEND / "pages/CrosswalksPage.tsx").read_text(encoding="utf-8")
    region_editor = (FRONTEND / "pages/CrosswalkRegionEditor.tsx").read_text(encoding="utf-8")
    ai_preview = (FRONTEND / "pages/LiveAiPage.tsx").read_text(encoding="utf-8")
    capture = (FRONTEND / "pages/DatasetCapturePage.tsx").read_text(encoding="utf-8")
    assert 'sourceId={selected.camera_side_a_id!}' in crosswalks
    assert 'sourceId={selected.camera_side_b_id!}' in crosswalks
    assert '<SimulationCamera3D' in crosswalks and 'liveCameraMjpegUrl()' not in crosswalks
    assert 'previewIs3d' in region_editor and 'sourceId={sourceId} editing' in region_editor
    assert 'className="crosswalk-region-overlay"' in region_editor
    assert 'camera?.kind === "simulation"' in ai_preview and 'showBoxes={showBoxes}' in ai_preview
    assert 'zones={regions}' in ai_preview and 'showRegions={showRegions}' in ai_preview
    assert '<CameraDetectionView' in ai_preview, "ESP AI preview must remain available"
    assert 'cameraStatus?.simulation_enabled && previewUrl' in capture
    assert 'Capture saves its original 2D synthetic image' in capture
    assert 'className="camera-frame"' in capture, "Physical camera captures must remain visible"
    assert 'sourcePoint(x: number, y: number, sourceId: string' in component
    assert 'hasOverlay = !editing' in component
    assert 'viewBox={`0 0 ${sizeX} ${sizeY}`}' in component
    assert 'pointer-events: none;' in styles
    assert 'sim3d-preview.is-editor .sim3d-world' in styles

    assert not (FRONTEND / "components/SimulationScene3D.tsx").exists()
    assert '"3D Replay"' not in (FRONTEND / "pages/SimulationLabPage.tsx").read_text(encoding="utf-8")

    print("[PASS] Live agent coordinates, all camera IDs, pause, density and disabled-state 3D scene")
    print("[PASS] Camera Settings, Crosswalk pair, Region Editor, AI Preview and Capture share 3D simulations")
    print("[PASS] Physical ESP, source-frame AI coordinates and saved capture image files remain unchanged")


if __name__ == "__main__":
    main()
