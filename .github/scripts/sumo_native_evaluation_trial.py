"""Actual Windows native-only HTTP, fixed/adaptive evaluation and retained captures."""
from pathlib import Path
import hashlib
import io
import json
import os
import subprocess
import sys
import time
from unittest.mock import patch
from zipfile import ZipFile

from sumo_migration_trial import processes
from fastapi.testclient import TestClient
from test_camera_simulation_api import build_test_app,assert_envelope
from app.routes import camera as routes
from app.services.native_evaluation import NativeEvaluationService,MAX_TICKS,MAX_BATCH
from app.services.sumo_shadow_runtime import GeneratedSession
from app.services.sumo_projection import VIEW_FLIPS
from app.services.experiment_timeline_csv import serialize_experiment_timeline

BASE="/api/camera/simulation/native-evaluation"


def arm(mode,density,out):
    sessions=[]
    def factory(seed,**kwargs):
        session=GeneratedSession(seed,**kwargs)
        sessions.append(session)
        return session
    svc=NativeEvaluationService(enabled=True,factory=factory)
    try:
        with patch.object(routes,"native_evaluation_service",svc),TestClient(build_test_app()) as client:
            init=assert_envelope(client.get(BASE))["data"]
            ident={k:init[k] for k in ("epoch","generation")}
            state=assert_envelope(client.post(BASE+"/start",json={**ident,"mode":mode,"density":density,"seed":42}))["data"]
            ident={k:state[k] for k in ("epoch","generation")}
            pids=[os.getpid(),sessions[0].proc.pid]
            before=processes(pids)
            start=time.perf_counter()
            for tick in range(0,MAX_TICKS,MAX_BATCH):
                state=assert_envelope(client.post(BASE+"/step",json={**ident,"tick":tick,"steps":MAX_BATCH}))["data"]
                snap=state["snapshot"]
                params={**ident,"tick":snap["tick"]}
                assert snap["tick"]==tick+MAX_BATCH
                for sid in VIEW_FLIPS:
                    frame=client.get(BASE+"/frame",params={**params,"source_id":sid})
                    assert frame.status_code==200 and int(frame.headers["x-frame-number"])==snap["tick"]
                    assert frame.headers["x-received-at-ms"]==str(snap["received_at_ms"])
                if tick==0:
                    paused=assert_envelope(client.post(BASE+"/pause",json={**params,"paused":True}))["data"]
                    assert paused["snapshot"]["paused"]
                    assert_envelope(client.post(BASE+"/step",json={**params,"steps":1}),expected_status=409)
                    assert_envelope(client.post(BASE+"/pause",json={**params,"paused":False}))
                    capture=client.get(BASE+"/capture",params=params)
                    assert capture.status_code==200
                    with ZipFile(io.BytesIO(capture.content)) as z:
                        for sid in VIEW_FLIPS:
                            png=client.get(BASE+"/frame",params={**params,"source_id":sid})
                            assert z.read(sid+".png")==png.content
                            assert json.loads(z.read(sid+".json"))["origin"]=="synthetic_sumo_projection"
                    (out/"capture.zip").write_bytes(capture.content)
            wall=time.perf_counter()-start
            after=processes(pids)
            result=assert_envelope(client.get(BASE+"/export",params=params))["data"]
            result.update({"digest":hashlib.sha256(json.dumps(result["timeline"],sort_keys=True).encode()).hexdigest(),
                "capture_count":4,"frame_reads":400,"resources":{"wall_s":wall,
                    "cpu_delta_s":sum(after[k]["cpu_s"]-before[k]["cpu_s"] for k in before),
                    "end_combined_working_set_bytes":sum(v["working_set_bytes"] for v in after.values())}})
            (out/"result.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
            assert len(result["timeline"])==MAX_TICKS
            assert result["summary"]["vehicle_passages"]>0 and result["summary"]["pedestrian_crossings"]>0
            assert not result["unknown_roads"]
            assert_envelope(client.post(BASE+"/step",json={**params,"steps":1}),expected_status=409)
            assert_envelope(client.get(BASE+"/frame",params={**params,"tick":MAX_TICKS-1,"source_id":"simulation_camera"}),expected_status=409)
            stop=assert_envelope(client.post(BASE+"/stop",json=ident))["data"]
            assert stop["snapshot"] is None
            assert_envelope(client.get(BASE+"/frame",params={**params,"source_id":"simulation_camera"}),expected_status=409)
            return result
    finally:
        svc.close()
        assert all(not s.proc.is_alive() for s in sessions)


def main(out):
    out.mkdir(parents=True,exist_ok=True)
    runs={}
    for mode in ("fixed","adaptive"):
        for repeat in range(2):
            folder=out/f"{mode}-{repeat}"
            folder.mkdir()
            subprocess.run([sys.executable,__file__,"--arm",mode,"normal",str(folder)],check=True,timeout=240)
            runs[(mode,repeat)]=json.loads((folder/"result.json").read_text(encoding="utf-8"))
        assert runs[(mode,0)]["digest"]==runs[(mode,1)]["digest"],mode
    pair={mode:{"timeline":runs[(mode,0)]["timeline"]} for mode in ("fixed","adaptive")}
    (out/"normalized_gate_comparison.csv").write_text(serialize_experiment_timeline(pair),encoding="utf-8")
    report={"evidence":"executed isolated native-only application fixed/adaptive trial","seed":42,
        "density":"normal","runs":[{k:v for k,v in run.items() if k!="timeline"} for run in runs.values()],
        "production_experiment_parity":False,"default_migration_allowed":False,
        "limitations":"Common normalized gate metrics, isolated controller with synthetic observations and default config. Not the existing production experiment metric contract or matched legacy HTTP/GPU workload."}
    (out/"summary.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    if sys.argv[1]=="--arm":
        arm(sys.argv[2],sys.argv[3],Path(sys.argv[4]))
    else:
        main(Path(sys.argv[1]))
