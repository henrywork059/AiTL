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
    assert not (FRONTEND / "components/SimulationScene3D.tsx").exists()
    assert '"3D Replay"' not in (FRONTEND / "pages/SimulationLabPage.tsx").read_text(encoding="utf-8")

    print("[PASS] Live agent coordinates, all camera IDs, pause, density and disabled-state 3D scene")
    print("[PASS] 3D preview wired only for simulation; physical ESP image and AI frame services preserved")


if __name__ == "__main__":
    main()
