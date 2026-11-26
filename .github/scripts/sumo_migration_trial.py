"""Matched legacy vs legacy+native shadow application trial; never promotes SUMO.

Run on the pinned Windows evaluation runner. Each arm uses a fresh interpreter,
identical synthetic clock/seed and actual camera API, PNG and capture code.
Resource samples are process CPU and working-set readings, not GPU or
replacement-engine performance claims.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2] / "AI_Traffic_Light"
sys.path.insert(0, str(ROOT / "apps/pc-studio/backend"))
sys.path.insert(0, str(ROOT / "scripts"))
from fastapi.testclient import TestClient
import cv2
import numpy as np
from test_camera_simulation_api import build_test_app, assert_envelope
from app.services.camera_frames import CameraFrameService, SIMULATION_CAMERA_SOURCE_IDS
from app.services.dataset_capture import DatasetCaptureService
from app.services.signal_rules import SignalRulesService
from app.services.sumo_shadow_runtime import GeneratedSession, ShadowRuntime
from app.services.zones import ZoneService
from app.routes import camera as camera_routes

SEED = 42
SAMPLES = 100
INTERVAL_S = .4


def processes(pids):
    ids = ",".join(str(int(pid)) for pid in pids)
    cmd = f"Get-Process -Id {ids} | Select-Object Id,CPU,WorkingSet64,PeakWorkingSet64 | ConvertTo-Json -Compress"
    raw = json.loads(subprocess.check_output(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", cmd],
        text=True, timeout=20))
    rows = raw if isinstance(raw, list) else [raw]
    assert {r["Id"] for r in rows} == set(pids), rows
    return {str(r["Id"]): {"cpu_s": r["CPU"], "working_set_bytes": r["WorkingSet64"],
                           "peak_working_set_bytes": r["PeakWorkingSet64"]} for r in rows}


def wait_shadow(shadow, tick, timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = shadow.status()
        assert state["status"] != "unavailable", state
        if state["status"] == "running" and state["snapshot"] is not None:
            if state["snapshot"]["tick"] == tick:
                return state
            assert state["snapshot"]["tick"] < tick, state
        time.sleep(.005)
    raise AssertionError(f"Shadow did not reach tick {tick}: {shadow.status()}")


def arm(enabled):
    now = [0.0]
    sessions = []
    def factory(seed):
        session = GeneratedSession(seed)
        sessions.append(session)
        return session
    shadow = ShadowRuntime(factory=factory, projection_enabled=True) if enabled else None
    service = CameraFrameService(simulation_seed=SEED, simulation_monotonic=lambda: now[0], shadow=shadow)
    digest = hashlib.sha256()
    phases = set()
    max_native_agents = 0
    with tempfile.TemporaryDirectory(prefix="mesh-migration-") as tmp:
        folder = Path(tmp)
        controller = SignalRulesService(config_path=folder / "signals.json", history_path=folder / "history.json")
        config = controller.defaults()
        config["mode"] = "fixed"
        controller.save_config(config)
        capture = DatasetCaptureService(dataset_root=folder / "datasets")
        zones = ZoneService(zone_path=folder / "zones.json")
        # Actual camera routes, isolated from physical source-manager side effects.
        with patch("app.services.camera_frames.signal_rules_service", controller), \
             patch.object(camera_routes, "camera_frame_service", service), \
             patch.object(camera_routes.remote_camera_service, "sync_after_simulation_change"):
            client = TestClient(build_test_app())
            try:
                assert_envelope(client.post("/api/camera/simulation/start"))
                if shadow:
                    wait_shadow(shadow, 0)
                pids = [os.getpid()] + ([sessions[0].proc.pid] if shadow else [])
                before = processes(pids)
                start = time.perf_counter()
                for step in range(1, SAMPLES + 1):
                    now[0] = step * INTERVAL_S
                    scenes = []
                    for sid in SIMULATION_CAMERA_SOURCE_IDS:
                        scene = assert_envelope(client.get("/api/camera/simulation/scene", params={"source_id": sid}))["data"]
                        assert scene["source_id"] == sid and (scene["width"], scene["height"]) == (1280, 720)
                        assert abs(scene["simulation_time_seconds"] - now[0]) < 1e-6, scene
                        signal = scene["signal"]
                        assert not (signal["vehicle_go"] and signal["pedestrian_walk"])
                        phases.add(signal["phase"])
                        service.set_simulation_source(sid)
                        response = client.get("/api/camera/frame", headers={"X-Request-ID": "migration-fixture"})
                        assert response.status_code == 200
                        assert response.headers["x-request-id"] == "migration-fixture"
                        assert response.headers["x-camera-source"] == sid
                        assert int(response.headers["x-frame-number"]) == scene["frame_number"]
                        image = cv2.imdecode(np.frombuffer(response.content, np.uint8), cv2.IMREAD_COLOR)
                        assert image.shape == (720, 1280, 3)
                        if not scenes:
                            canonical = image
                        else:
                            flip = {"simulation_camera_b": 0, "simulation_camera_c": 1, "simulation_camera_d": -1}[sid]
                            assert np.array_equal(image, cv2.flip(canonical, flip))
                        scene.pop("received_at_ms")
                        digest.update(json.dumps(scene, sort_keys=True).encode())
                        digest.update(response.content)
                        scenes.append(scene)
                    assert all(s["vehicles"] == scenes[0]["vehicles"] and
                               s["pedestrians"] == scenes[0]["pedestrians"] for s in scenes)
                    if shadow:
                        status = wait_shadow(shadow, step * 2)
                        snap = status["snapshot"]
                        assert snap["seed"] == SEED and abs(snap["time_s"] - now[0]) < 1e-6
                        max_native_agents = max(max_native_agents, len(snap["agents"]))
                wall_s = time.perf_counter() - start
                after = processes(pids)
                assert {"vehicle_green", "vehicle_yellow", "pedestrian_green", "pedestrian_flashing", "all_red"} <= phases, phases
                if shadow:
                    assert max_native_agents > 0
                projection = assert_envelope(client.get("/api/camera/simulation/native-projection"))["data"]
                if shadow:
                    import base64
                    import csv
                    import io
                    assert projection["status"] == "running"
                    assert projection["snapshot"]["tick"] == SAMPLES * 2
                    assert projection["snapshot"]["provenance"] == "synthetic_sumo_projection"
                    assert len(list(csv.DictReader(io.StringIO(projection["agents_csv"])))) == len(projection["snapshot"]["agents"])
                    assert set(projection["views_png_base64"]) == set(SIMULATION_CAMERA_SOURCE_IDS)
                    scene_only = assert_envelope(client.get("/api/camera/simulation/native-projection?format=scene"))["data"]
                    assert scene_only["snapshot"]["agents"] == projection["snapshot"]["agents"]
                    assert scene_only["snapshot"]["lanes"] and "views_png_base64" not in scene_only
                    assert scene_only["snapshot"]["tick"] == projection["snapshot"]["tick"]
                    for encoded in projection["views_png_base64"].values():
                        image = cv2.imdecode(np.frombuffer(base64.b64decode(encoded), np.uint8), cv2.IMREAD_COLOR)
                        assert image.shape == (720, 1280, 3)
                else:
                    assert projection["status"] == "disabled" and projection["snapshot"] is None
                # Pause must freeze both clocks; native state stays diagnostic.
                paused = assert_envelope(client.post("/api/camera/simulation/settings", json={"paused": True}))["data"]
                assert paused["simulation_paused"]
                now[0] += 10
                for sid in SIMULATION_CAMERA_SOURCE_IDS:
                    scene = assert_envelope(client.get("/api/camera/simulation/scene", params={"source_id": sid}))["data"]
                    assert scene["paused"] and scene["simulation_time_seconds"] == 40
                    frame = service.simulation_frame_for(sid)
                    record = capture.capture_frame(frame, session_id="migration_fixture")
                    assert (folder / "datasets" / record.image_path).read_bytes() == frame.content
                    metadata = json.loads((folder / "datasets" / record.metadata_path).read_text(encoding="utf-8"))
                    assert metadata["origin"] == "simulation"
                if shadow:
                    assert wait_shadow(shadow, SAMPLES * 2)["snapshot"]["tick"] == SAMPLES * 2
                # Actual validated original-image coordinate persistence, not browser drag.
                region = {"id": "migration_region", "type": "counting_region", "label": "Migration fixture",
                          "polygon": [[10, 20], [480, 20], [480, 719], [10, 719]]}
                zones.save([region])
                assert ZoneService(zone_path=folder / "zones.json").status()["zones"][0]["polygon"] == region["polygon"]
                assert_envelope(client.post("/api/camera/simulation/settings", json={"paused": False}))
                now[0] += .4
                scene = assert_envelope(client.get("/api/camera/simulation/scene"))["data"]
                assert not scene["paused"] and scene["simulation_time_seconds"] == 40.4
                if shadow:
                    wait_shadow(shadow, SAMPLES * 2 + 2)
                assert_envelope(client.post("/api/camera/simulation/settings", json={"density": "busy"}))
                if shadow:
                    wait_shadow(shadow, 0)
                stopped = assert_envelope(client.post("/api/camera/simulation/stop"))["data"]
                assert not stopped["simulation_enabled"]
                assert_envelope(client.get("/api/camera/simulation/scene"), expected_status=409)
                if shadow:
                    assert shadow.status()["snapshot"] is None and shadow.status()["status"] == "idle"
                    assert assert_envelope(client.get("/api/camera/simulation/native-projection"))["data"]["snapshot"] is None
                else:
                    assert service.shadow_diagnostics()["status"] == "disabled"
                resource = {"wall_s": wall_s, "before": before, "after": after,
                            "cpu_delta_s": sum(after[p]["cpu_s"] - before[p]["cpu_s"] for p in before),
                            "end_combined_working_set_bytes": sum(row["working_set_bytes"] for row in after.values())}
                return {"arm": "legacy_plus_native_shadow" if enabled else "legacy_only",
                        "digest": digest.hexdigest(), "scene_frame_pairs": SAMPLES * 4,
                        "simulation_s": SAMPLES * INTERVAL_S, "phases": sorted(phases),
                        "native_max_agents": max_native_agents, "captures": 4,
                        "zone_round_trip": True, "pause_resume_reset_stop": True,
                        "native_projection_api": "verified" if enabled else "disabled_verified",
                        "resources": resource}
            finally:
                service.set_simulation(False)
                service.close_shadow()
                client.close()
                assert all(not s.proc.is_alive() for s in sessions)


def main(output):
    with tempfile.TemporaryDirectory() as tmp:
        runs = []
        for enabled in (False, True):
            target = Path(tmp) / f"arm-{int(enabled)}.json"
            subprocess.run([sys.executable, __file__, "--arm", str(int(enabled)), str(target)],
                           check=True, timeout=180)
            runs.append(json.loads(target.read_text(encoding="utf-8")))
    assert runs[0]["digest"] == runs[1]["digest"], "Shadow changed authoritative scene or frame"
    result = {"evidence": "executed matched synthetic application workload",
              "seed": SEED, "runs": runs, "legacy_shadow_noninterference": True,
              "replacement_parity": False, "default_migration_allowed": False,
              "limitations": "Both arms publish legacy frames; native shadow has distinct geometry and demand. CPU/working-set samples are not replacement-engine or GPU benchmarks. Browser drag/save, replacement experiment export, full owner acceptance and replacement canonical projection remain unverified."}
    Path(output).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    if sys.argv[1] == "--arm":
        Path(sys.argv[3]).write_text(json.dumps(arm(sys.argv[2] == "1")), encoding="utf-8")
    else:
        main(sys.argv[1])
