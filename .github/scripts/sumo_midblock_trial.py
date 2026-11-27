"""Pinned actual midblock network, cyclic runtime and HTTP isolation trial.

Not a physical calibration or matched legacy demand assertion.
Retain actual generated topology even if runtime validation fails.
"""
from pathlib import Path
import hashlib
import io
import json
import os
import shutil
import sys
import time
from unittest.mock import patch
from zipfile import ZipFile
import cv2
import numpy as np

from sumo_migration_trial import processes
from fastapi.testclient import TestClient
from test_camera_simulation_api import build_test_app, assert_envelope
from app.routes import camera as routes
from app.services.camera_frames import CameraFrameService
from app.services.native_evaluation import NativeEvaluationService
from app.services.sumo_midblock_fixture import generate_midblock
from app.services.sumo_midblock_session import CyclicMidblockSession
from app.services.sumo_projection import VIEW_FLIPS
from app.services.inference import InferenceService
from app.core.exceptions import AppError

BASE="/api/camera/simulation/native-evaluation"


def verify_export(result,expected_slots,horizon):
    assert result["geometry"]=="midblock" and result["demand_model"]=="native_cyclic_slots_v1"
    assert len(result["timeline"])==horizon and not result["unknown_roads"]
    assert len(result["current_visits"])==expected_slots==len(result["demand_manifest"])
    assert len(set(result["current_visits"].values()))==expected_slots
    a=result["trip_accounting"]
    parts=[set(a[k]) for k in ("active","arrived","not_observed_due","not_yet_due","retired_without_arrival")]
    assert sum(map(len,parts))==len(set().union(*parts))==len(a["offered"])
    assert set().union(*parts)==set(a["offered"])
    assert not a["retired_without_arrival"]
    assert len(a["offered"])==expected_slots+len(a["arrived"])
    assert sum(result["slot_visits"].values())==len(a["arrived"])
    assert set(result["current_visits"].values())==set(a["offered"])-set(a["arrived"])
    assert len(result["journey_manifest"])==len(a["offered"])
    assert result["summary"]["vehicle_passages"]>0 and result["summary"]["pedestrian_crossings"]>0
    assert len(result["arrived_vehicles"])>0 and len(result["arrived_pedestrians"])>0
    assert max(result["slot_visits"].values())>=2
    for kind in ("vehicle","pedestrian"):
        waits=result["waiting_episodes"][kind]
        assert abs(sum(row[kind+"_queue"] for row in result["timeline"])*.2-waits["observed_agent_seconds"])<1e-6
    # An arrival without the required gate in the observed route is not a
    # valid midblock journey. Validate BOTH pedestrian approach directions.
    trips={j["ident"]:j for j in result["journey_manifest"]}
    for ident in a["arrived"]:
        gate=next(s["road_id"] for s in trips[ident]["path"] if s["kind"]==trips[ident]["kind"]+"_gate")
        assert gate in result["observed_routes"][ident]
    assert {trips[i]["path"][0]["road_id"] for i in result["arrived_pedestrians"]}=={"NC","CS"}


def run_arm(out,seed,density,mode,*,read_workload=False):
    out.mkdir(parents=True,exist_ok=True)
    sessions=[]
    def factory(seed,*,density):
        try:
            session=CyclicMidblockSession(seed,density=density)
        except Exception:
            import traceback
            (out/"startup-failure.txt").write_text(traceback.format_exc(),encoding="utf-8")
            raise
        sessions.append(session)
        for name in ("nodes.xml","edges.xml","connections.xml","routes.xml","slots.json","network.xml","first_visits.xml"):
            shutil.copyfile(session.network_path.parent/name,out/name)
        return session
    svc=NativeEvaluationService(enabled=True,midblock_factory=factory)
    legacy=CameraFrameService(simulation_seed=seed,simulation_monotonic=lambda:0.)
    legacy.set_simulation(True)
    legacy.configure_simulation(paused=True)
    baseline=legacy.latest_frame()
    token=legacy.observation_mode_token
    try:
        with patch.object(routes,"native_evaluation_service",svc),patch.object(routes,"camera_frame_service",legacy),TestClient(build_test_app()) as client:
            init=svc.scene()
            identity={k:init[k] for k in ("epoch","generation")}
            response=client.post(BASE+"/start",json={**identity,"geometry":"midblock","seed":seed,"mode":mode,"density":density})
            if response.status_code!=200 and (out/"startup-failure.txt").exists():
                print((out/"startup-failure.txt").read_text(),flush=True)
            state=assert_envelope(response)["data"]
            identity={k:state[k] for k in ("epoch","generation")}
            pids=[os.getpid(),sessions[0].proc.pid]
            before=processes(pids)
            start=time.perf_counter()
            timings={"scene_ms":[],"frame_ms":[]}
            digest=hashlib.sha256()
            # 100 two-step batches: same 40 seconds, 400 scene/PNG pairs as
            # existing HTTP benchmark. Remaining horizon is scene-only.
            for tick in range(0,200,2):
                state=assert_envelope(client.post(BASE+"/step",json={**identity,"tick":tick,"steps":2}))["data"]
                params={**identity,"tick":tick+2}
                if read_workload:
                    canonical=None
                    for sid,flip in VIEW_FLIPS.items():
                        t=time.perf_counter()
                        scene=assert_envelope(client.get(BASE+"/view",params={**params,"source_id":sid}))["data"]
                        timings["scene_ms"].append((time.perf_counter()-t)*1000)
                        t=time.perf_counter()
                        response=client.get(BASE+"/frame",params={**params,"source_id":sid})
                        timings["frame_ms"].append((time.perf_counter()-t)*1000)
                        assert response.status_code==200 and int(response.headers["x-frame-number"])==params["tick"]
                        assert not scene["observation"]["detector_input_eligible"] and not scene["legacy_editor_compatible"]
                        pixels=cv2.imdecode(np.frombuffer(response.content,np.uint8),cv2.IMREAD_COLOR)
                        if flip is None: canonical=pixels
                        else: assert np.array_equal(cv2.flip(canonical,flip),pixels)
                        digest.update(response.content)
                if tick==0:
                    assert_envelope(client.post(BASE+"/pause",json={**params,"paused":True}))
                    assert_envelope(client.post(BASE+"/step",json={**params,"steps":1}),expected_status=409)
                    assert_envelope(client.post(BASE+"/pause",json={**params,"paused":False}))
            after=processes(pids)
            if read_workload:
                resources={"wall_s":time.perf_counter()-start,"cpu_delta_s":sum(after[k]["cpu_s"]-before[k]["cpu_s"] for k in before),
                           "end_combined_working_set_bytes":sum(x["working_set_bytes"] for x in after.values()),
                           "scene_reads":400,"frame_reads":400,"simulated_seconds":40,
                           "image_digest":digest.hexdigest(),
                           "latency_ms":{k:{"mean":float(np.mean(v)),"p95":float(np.percentile(v,95)),"count":len(v)} for k,v in timings.items()}}
                (out/"resources.json").write_text(json.dumps(resources,indent=2),encoding="utf-8")
                (out/"latency-samples.json").write_text(json.dumps(timings),encoding="utf-8")
            capture=client.get(BASE+"/capture",params=params)
            assert capture.status_code==200
            (out/"capture.zip").write_bytes(capture.content)
            with ZipFile(io.BytesIO(capture.content)) as z:
                scene=json.loads(z.read("scene.json"))
                assert scene["demand_model"]=="native_cyclic_slots_v1"
                assert "slot_id,visit" in z.read("agents.csv").decode()
                for sid in VIEW_FLIPS:
                    assert z.read(sid+".png")==client.get(BASE+"/frame",params={**params,"source_id":sid}).content
            try:
                InferenceService().detect_frame(svc.frame(**params,source_id="simulation_camera"))
            except AppError as exc:
                assert exc.status_code==409
            else:
                raise AssertionError("Native image entered detector")
            # Advance another 200 seconds with bounded actual child steps.
            horizon=1200
            for tick in range(200,horizon,25):
                svc.step(**identity,tick=tick,steps=min(25,horizon-tick),_return_scene=False)
            result=svc.export(**identity,tick=horizon)
            (out/"result.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
            verify_export(result,{"light":8,"normal":15,"busy":23}[density],horizon)
            assert legacy.latest_frame() is baseline and legacy.observation_mode_token==token
            assert_envelope(client.post(BASE+"/stop",json=identity))
            assert_envelope(client.get(BASE+"/frame",params={**identity,"tick":horizon,"source_id":"simulation_camera"}),expected_status=409)
            assert legacy.latest_frame() is baseline
            return result
    finally:
        svc.close()
        legacy.set_simulation(False)
        assert all(not s.proc.is_alive() for s in sessions)


def main(out):
    out.mkdir(parents=True,exist_ok=True)
    topology=out/"topology"
    topology.mkdir()
    # Preserve the generated input/output topology even on a strict map rejection.
    try:
        generate_midblock(topology,42,"normal")
    except Exception as exc:
        (topology/"failure.txt").write_text(repr(exc)+"\n"+str(getattr(exc,"stderr","")),encoding="utf-8")
        raise
    results={}
    for seed,density in ((42,"normal"),(73,"busy")):
        for mode in ("fixed","adaptive"):
            key=f"{seed}-{density}-{mode}"
            results[key]=run_arm(out/key,seed,density,mode,read_workload=(seed==42))
        f,a=(results[f"{seed}-{density}-{mode}"] for mode in ("fixed","adaptive"))
        assert f["layout_id"]==a["layout_id"] and f["demand_manifest"]==a["demand_manifest"]
        assert f["demand_digest"]==a["demand_digest"]
    repeat=run_arm(out/"42-normal-fixed-repeat",42,"normal","fixed")
    assert repeat==results["42-normal-fixed"]
    # Actual saved-policy pair uses the same cyclic evaluation lifecycle.
    svc=NativeEvaluationService(enabled=True)
    try:
        archive=svc.compare(epoch=svc.epoch,generation=svc.generation,density="normal",seed=42,
                            duration_seconds=240,geometry="midblock")
        (out/"paired-comparison.zip").write_bytes(archive)
        with ZipFile(io.BytesIO(archive)) as z:
            manifest=json.loads(z.read("manifest.json"))
            assert manifest["demand_model"]=="native_cyclic_slots_v1"
            for mode in ("fixed","adaptive"):
                verify_export(json.loads(z.read(mode+".json")),15,1200)
    finally:
        svc.close()
    (out/"summary.json").write_text(json.dumps({"evidence":"executed native midblock cyclic trials",
        "arms":{k:{"demand_digest":a["demand_digest"],"summary":a["summary"],"slot_visits":a["slot_visits"]} for k,a in results.items()},
        "deterministic_repeat":True,"physical_output_allowed":False,"production_geometry_matched":False},indent=2),encoding="utf-8")


if __name__=="__main__":
    main(Path(sys.argv[1]))
