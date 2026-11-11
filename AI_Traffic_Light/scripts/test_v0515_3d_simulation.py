"""Focused test: the simulated camera's 3D preview mirrors live agent state."""
from pathlib import Path
import json
import subprocess
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
        assert {vehicle["vehicle_type"] for vehicle in scene["vehicles"]} == {"car", "suv", "van", "bus"}
        assert len(scene["pedestrians"]) == 7
        assert scene["signal"]["vehicle_go"] is True
        assert scene["signal"]["pedestrian_walk"] is False
        # Compare the snapshot before another read refreshes moving agents.
        with service._lock:
            assert scene["vehicles"][0]["x"] == round(service._vehicles[0].x, 2)
            assert scene["vehicles"][0]["width"] == service._vehicles[0].width
            assert scene["pedestrians"][0]["y"] == round(service._pedestrians[0].y, 2)
        assert service.simulation_frame_for(source_id) is not None

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
    assert "sim3d-car-roof" in styles and "sim3d-car-wheel" in styles and "sim3d-car-end" in styles
    assert "sim3d-person-figure" in styles and "rotateX(-90deg)" in styles
    assert "sim3d-person-head" in component and "sim3d-person-leg" in component
    assert "sim3d-car--bus" in styles and "sim3d-car--van" in styles and "sim3d-car--suv" in styles
    assert "sim3d-car-window-band" in styles and "sim3d-person-head::before" in styles
    assert "sim3d-person.is-reentering { transition: none; }" in styles
    assert "isPedestrianReentry(previousY, pedestrian.y, sizeY)" in component
    assert ".sim3d-car.is-reentering { transition: none; }" in styles
    assert "isVehicleReentry(previousX, vehicle.x, sizeX)" in component
    motion = FRONTEND / "components/simulation3dMotion.ts"
    assert motion.is_file()
    script = """
import assert from "node:assert/strict";
import { isPedestrianReentry, isVehicleReentry, simulationSourcePoint } from MOTION_URI;
assert.equal(isVehicleReentry(undefined, -260, 1280), false);
assert.equal(isVehicleReentry(100, 140, 1280), false);
assert.equal(isVehicleReentry(1100, 1070, 1280), false);
assert.equal(isVehicleReentry(1420, -260, 1280), true);
assert.equal(isVehicleReentry(-280, 1420, 1280), true);
assert.equal(isVehicleReentry(500, 510, 1280), false);
assert.equal(isPedestrianReentry(undefined, 50, 720), false);
assert.equal(isPedestrianReentry(130, 170, 720), false);
assert.equal(isPedestrianReentry(750, 40, 720), true);
assert.equal(isPedestrianReentry(20, 745, 720), true);
assert.equal(isPedestrianReentry(674, 674, 720), false);
assert.deepEqual(simulationSourcePoint(460, 190, "simulation_camera", 1280, 720), { x: 460, y: 190 });
assert.deepEqual(simulationSourcePoint(460, 190, "simulation_camera_b", 1280, 720), { x: 460, y: 530 });
assert.deepEqual(simulationSourcePoint(460, 190, "simulation_camera_c", 1280, 720), { x: 820, y: 190 });
assert.deepEqual(simulationSourcePoint(460, 190, "simulation_camera_d", 1280, 720), { x: 820, y: 530 });
""".replace("MOTION_URI", json.dumps(motion.as_uri()))
    subprocess.run(["node", "--experimental-strip-types", "--input-type=module", "-e", script], check=True, cwd=ROOT)
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
    assert 'previewIs3d' in region_editor and 'editing={!perspectiveView}' in region_editor
    assert 'zones={previewZones}' in region_editor and 'aria-pressed={perspectiveView}' in region_editor
    assert '(!previewIs3d || !perspectiveView) && <svg' in region_editor
    assert 'className="crosswalk-region-overlay"' in region_editor
    assert 'camera?.kind === "simulation"' in ai_preview and 'showBoxes={showBoxes}' in ai_preview
    assert 'zones={regions}' in ai_preview and 'showRegions={showRegions}' in ai_preview
    assert '<CameraDetectionView' in ai_preview, "ESP AI preview must remain available"
    assert 'cameraStatus?.simulation_enabled && previewUrl' in capture
    assert 'Capture saves its original 2D synthetic image' in capture
    assert 'className="camera-frame"' in capture, "Physical camera captures must remain visible"
    assert 'simulationSourcePoint(sizeX * 0.36, sizeY * 0.26, sourceId, sizeX, sizeY)' in component
    assert 'simulationSourcePoint(sizeX * 0.61, sizeY * 0.88, sourceId, sizeX, sizeY)' in component
    assert 'left: `${vehicleSignalPoint.x / sizeX * 100}%`' in component
    assert 'top: `${pedestrianSignalPoint.y / sizeY * 100}%`' in component
    assert 'scene?.source_id === sourceId' in component  # Never display a stale source
    assert 'hasOverlay = !editing' in component
    assert 'viewBox={`0 0 ${sizeX} ${sizeY}`}' in component
    assert 'pointer-events: none;' in styles
    assert 'sim3d-preview.is-editor .sim3d-world' in styles

    assert not (FRONTEND / "components/SimulationScene3D.tsx").exists()
    assert '"3D Replay"' not in (FRONTEND / "pages/SimulationLabPage.tsx").read_text(encoding="utf-8")

    print("[PASS] Live agent coordinates, all camera IDs, pause, density and disabled-state 3D scene")
    print("[PASS] Camera Settings, Crosswalk pair, Region Editor, AI Preview and Capture share 3D simulations")
    print("[PASS] Physical ESP, source-frame AI coordinates and saved capture image files remain unchanged")
    print("[PASS] Distinct 3D vehicle models and human figures; off-screen vehicle and pedestrian respawn")


if __name__ == "__main__":
    main()
