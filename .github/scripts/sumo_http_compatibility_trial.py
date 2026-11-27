"""Matched HTTP scene/frame workload; actual native/legacy and rollback isolation.

Equal 40s duration, 400 JSON and 400 PNG reads in fresh processes. Geometry,
demand and controller observation cadence differ; no migration parity claim.
"""
from pathlib import Path
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch
from zipfile import ZipFile

from sumo_migration_trial import processes, SEED, SAMPLES, INTERVAL_S
from fastapi.testclient import TestClient
import cv2
import numpy as np
from test_camera_simulation_api import build_test_app, assert_envelope
from app.routes import camera as routes
from app.routes import experiments as experiment_routes
from app.services.camera_frames import CameraFrameService,SIMULATION_CAMERA_SOURCE_IDS
from app.services.native_evaluation import NativeEvaluationService
from app.services.sumo_shadow_runtime import GeneratedSession
from app.services.signal_rules import SignalRulesService
from app.services.dataset_capture import DatasetCaptureService
from app.services.zones import ZoneService

BASE="/api/camera/simulation/native-evaluation"


def arm(native,out):
    now=[0.]
    sessions=[]
    def factory(seed,**kwargs):
        session=GeneratedSession(seed,**kwargs)
        sessions.append(session)
        return session
    legacy=CameraFrameService(simulation_seed=SEED,simulation_monotonic=lambda:now[0])
    evaluation=NativeEvaluationService(enabled=native,factory=factory)
    with tempfile.TemporaryDirectory(prefix="mesh-http-parity-") as tmp:
        folder=Path(tmp)
        policy=SignalRulesService(config_path=folder/"policy.json",history_path=folder/"history.jsonl",respect_environment=False)
        config=policy.defaults()
        config["mode"]="fixed"
        policy.save_config(config)
        capture=DatasetCaptureService(dataset_root=folder/"dataset",respect_environment=False)
        zones=ZoneService(zone_path=folder/"zones.json")
        zones.save(zones.zones())
        zone_bytes=(folder/"zones.json").read_bytes()
        policy_bytes=policy.config_path.read_bytes()
        with patch("app.services.camera_frames.signal_rules_service",policy), \
             patch("app.services.native_evaluation.signal_rules_service",policy), \
             patch.object(routes,"camera_frame_service",legacy), \
             patch.object(routes,"native_evaluation_service",evaluation), \
             patch.object(routes.remote_camera_service,"sync_after_simulation_change"), \
             TestClient(build_test_app()) as client:
            try:
                # Check the actual legacy plane before standalone native start.
                legacy.set_simulation(True)
                baseline=legacy.simulation_frame_for("simulation_camera")
                legacy_scene=legacy.simulation_scene_for("simulation_camera")
                assert baseline.origin=="simulation"
                if native:
                    init=assert_envelope(client.get(BASE))["data"]
                    identity={k:init[k] for k in ("epoch","generation")}
                    state=assert_envelope(client.post(BASE+"/start",json={**identity,"mode":"fixed","density":"normal","seed":SEED}))["data"]
                    identity={k:state[k] for k in ("epoch","generation")}
                    # Native commands cannot move legacy clock, change saved regions or source identity.
                    assert legacy.simulation_frame_for("simulation_camera").content==baseline.content
                    assert legacy.simulation_scene_for("simulation_camera")==legacy_scene
                    legacy.set_simulation(False)
                pids=[os.getpid()]+([sessions[0].proc.pid] if native else [])
                before=processes(pids)
                start=time.perf_counter()
                digest=hashlib.sha256()
                timings={"step_ms":[],"scene_ms":[],"frame_ms":[],"decode_ms":[]}
                for i in range(1,SAMPLES+1):
                    stage=time.perf_counter()
                    if native:
                        state=assert_envelope(client.post(BASE+"/step",json={**identity,"tick":2*(i-1),"steps":2}))["data"]
                        params={**identity,"tick":2*i}
                    else:
                        now[0]=i*INTERVAL_S
                    timings["step_ms"].append((time.perf_counter()-stage)*1000)
                    canonical=None
                    for sid in SIMULATION_CAMERA_SOURCE_IDS:
                        stage=time.perf_counter()
                        if native:
                            scene=assert_envelope(client.get(BASE+"/view",params={**params,"source_id":sid}))["data"]
                            timings["scene_ms"].append((time.perf_counter()-stage)*1000)
                            stage=time.perf_counter()
                            response=client.get(BASE+"/frame",params={**params,"source_id":sid})
                            assert scene["coordinate_space"]=="native_projection_v1" and not scene["legacy_editor_compatible"]
                            assert abs(scene["time_s"]-i*INTERVAL_S)<1e-6
                        else:
                            scene=assert_envelope(client.get("/api/camera/simulation/scene",params={"source_id":sid}))["data"]
                            timings["scene_ms"].append((time.perf_counter()-stage)*1000)
                            stage=time.perf_counter()
                            legacy.set_simulation_source(sid)
                            response=client.get("/api/camera/frame")
                            assert -1e-6 <= now[0]-scene["simulation_time_seconds"] <= .5+1e-6
                            assert scene["observation"]["frame_number"]==scene["frame_number"]
                            assert scene["observation"]["detector_input_eligible"]
                        timings["frame_ms"].append((time.perf_counter()-stage)*1000)
                        stage=time.perf_counter()
                        assert response.status_code==200 and response.headers["x-camera-source"]==scene["source_id"]
                        assert int(response.headers["x-frame-number"])==scene["frame_number"]
                        assert int(response.headers["x-received-at-ms"])==scene["observation"]["received_at_ms"]
                        image=cv2.imdecode(np.frombuffer(response.content,np.uint8),cv2.IMREAD_COLOR)
                        assert image.shape==(720,1280,3)
                        if canonical is None: canonical=image
                        else: assert np.array_equal(image,cv2.flip(canonical,{"simulation_camera_b":0,"simulation_camera_c":1,"simulation_camera_d":-1}[sid]))
                        digest.update(response.content)
                        timings["decode_ms"].append((time.perf_counter()-stage)*1000)
                wall=time.perf_counter()-start
                after=processes(pids)
                if native:
                    data=client.get(BASE+"/capture",params=params)
                    assert data.status_code==200
                    (out/"capture.zip").write_bytes(data.content)
                    with ZipFile(io.BytesIO(data.content)) as z:
                        for sid in SIMULATION_CAMERA_SOURCE_IDS:
                            assert z.read(sid+".png")==client.get(BASE+"/frame",params={**params,"source_id":sid}).content
                    region_evidence=[]
                    for sid in SIMULATION_CAMERA_SOURCE_IDS:
                        view=assert_envelope(client.get(BASE+"/view",params={**params,"source_id":sid}))["data"]
                        payload={**params,"source_id":sid,"coordinate_space":view["coordinate_space"],
                                 "layout_id":view["layout_id"],"polygon":[[0,0],[1279,0],[1279,719],[0,719]]}
                        region=assert_envelope(client.post(BASE+"/region",json=payload))["data"]
                        assert sorted(region["agent_ids"])==sorted(a["id"] for a in view["agents"])
                        assert not region["persisted"]
                        assert_envelope(client.post(BASE+"/region",json={**payload,"coordinate_space":"legacy_pixels"}),expected_status=409)
                        assert_envelope(client.post(BASE+"/region",json={**payload,"layout_id":"0"*64}),expected_status=409)
                        region_evidence.append(region)
                    (out/"region-evidence.json").write_text(json.dumps(region_evidence,indent=2),encoding="utf-8")
                    assert_envelope(client.post(BASE+"/stop",json=identity))
                    assert_envelope(client.post(BASE+"/region",json=payload),expected_status=409)
                    assert_envelope(client.get(BASE+"/frame",params={**params,"source_id":"simulation_camera"}),expected_status=409)
                    # Roll back to the exact initial legacy geometry and seed.
                    now[0]=0.
                    legacy.set_simulation(True)
                    assert legacy.simulation_frame_for("simulation_camera").content==baseline.content
                    rolled=legacy.simulation_scene_for("simulation_camera")
                    assert rolled["vehicles"]==legacy_scene["vehicles"] and rolled["pedestrians"]==legacy_scene["pedestrians"]
                    assert legacy.simulation_frame_for("simulation_camera").origin=="simulation"
                    # Real paired saved-policy experiment route, same native layout.
                    init=assert_envelope(client.get(BASE))["data"]
                    from fastapi import FastAPI
                    app=build_test_app()
                    app.include_router(experiment_routes.router,prefix="/api/traffic")
                    with patch.object(experiment_routes,"_native_evaluation_service",return_value=evaluation),TestClient(app) as exp:
                        comparison=exp.post("/api/traffic/native-experiments",json={"epoch":init["epoch"],"generation":init["generation"],"seed":SEED,"duration_seconds":500,"density":"normal"})
                        assert comparison.status_code==200,comparison.text[:200]
                        (out/"comparison.zip").write_bytes(comparison.content)
                        with ZipFile(io.BytesIO(comparison.content)) as z:
                            manifest=json.loads(z.read("manifest.json"))
                            assert len(manifest["demand_digest"])==64
                            assert "deltas.json" in z.namelist()
                            assert not manifest["production_experiment_parity"]
                            for mode in ("fixed","adaptive"):
                                result=json.loads(z.read(mode+".json"))
                                assert len(result["timeline"])==2500
                                assert len(result["arrived_vehicles"])==8 and len(result["arrived_pedestrians"])==7
                                assert result["summary"]["vehicle_passages"]==8 and result["summary"]["pedestrian_crossings"]==14
                else:
                    for sid in SIMULATION_CAMERA_SOURCE_IDS:
                        frame=legacy.simulation_frame_for(sid)
                        record=capture.capture_frame(frame,session_id="legacy_benchmark")
                        assert (capture.dataset_root/record.image_path).read_bytes()==frame.content
                assert (folder/"zones.json").read_bytes()==zone_bytes
                assert policy.config_path.read_bytes()==policy_bytes
                latency={name:{"count":len(values),"mean":float(np.mean(values)),"p50":float(np.percentile(values,50)),"p95":float(np.percentile(values,95)),"max":max(values)} for name,values in timings.items()}
                (out/"latency-samples.json").write_text(json.dumps(timings),encoding="utf-8")
                result={"latency_ms":latency,"arm":"native_only" if native else "legacy_only","scene_reads":400,"frame_reads":400,
                        "simulated_seconds":40,"captures":4,"digest":digest.hexdigest(),"rollback_verified":native,
                        "saved_policy_and_zone_bytes_unchanged":True,
                        "resources":{"wall_s":wall,"cpu_delta_s":sum(after[k]["cpu_s"]-before[k]["cpu_s"] for k in before),
                        "end_combined_working_set_bytes":sum(v["working_set_bytes"] for v in after.values()),"before":before,"after":after}}
                (out/"result.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
                return result
            finally:
                legacy.set_simulation(False)
                evaluation.close()
                assert all(not s.proc.is_alive() for s in sessions)


def main(out):
    out.mkdir(parents=True,exist_ok=True)
    runs=[]
    for native in (False,True):
        for repeat in range(2):
            folder=out/f"{int(native)}-{repeat}"
            folder.mkdir()
            subprocess.run([sys.executable,__file__,"--arm",str(int(native)),str(folder)],check=True,timeout=180)
            runs.append(json.loads((folder/"result.json").read_text(encoding="utf-8")))
    assert runs[0]["digest"]==runs[1]["digest"] and runs[2]["digest"]==runs[3]["digest"]
    result={"evidence":"executed matched HTTP read workload","runs":runs,
            "replacement_parity":False,"default_migration_allowed":False,
            "limitations":"Different geometry and finite versus recirculating demand, different command/read cadence, no GPU or owner hardware benchmark. Resource samples exclude captures and paired comparison."}
    (out/"summary.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    if sys.argv[1]=="--arm":arm(sys.argv[2]=="1",Path(sys.argv[3]))
    else:main(Path(sys.argv[1]))
