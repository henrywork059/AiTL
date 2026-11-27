"""Actual legacy and native motion with the same requested phases and gate metrics.

Normalized geometry is shared only in the measurement space. Actual physical
geometry/demand and admission algorithms differ, so no performance ranking.
"""
from pathlib import Path
import csv
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time

from sumo_migration_trial import processes
from app.services.camera_frames import CameraFrameService
from app.services.sumo_shadow_runtime import GeneratedSession
from app.services.simulation_gate_metrics import GateMetrics, STEP_S
from app.services.simulation_gate_adapters import legacy_observations, NativeGateAdapter

SEED=42
TICKS=2500
CYCLE=["vehicle_green"]*100+["vehicle_yellow"]*15+["all_red"]*10+["pedestrian_green"]*150+["pedestrian_flashing"]*50+["all_red"]*10


def arm(native):
    session=GeneratedSession(SEED,density="normal") if native else None
    try:
        if native:
            adapter=NativeGateAdapter(session.network_path)
        else:
            service=CameraFrameService(simulation_seed=SEED)
            service._initialize_agents_locked()
        pids=[os.getpid()]+([session.proc.pid] if session else [])
        before=processes(pids)
        start=time.perf_counter()
        metrics=GateMetrics()
        timeline=[]
        for tick in range(1,TICKS+1):
            phase=CYCLE[(tick-1)%len(CYCLE)]
            if native:
                session.set_phase(phase)
                session.advance()
                rows=adapter.observations(session.agents())
            else:
                # Existing legacy movement functions, four committed 50 ms steps
                # per sample. No live controller or physical outputs touched.
                for _ in range(4):
                    service._advance_vehicles_locked(.05,phase)
                    service._advance_pedestrians_locked(.05,phase)
                rows=legacy_observations(service._vehicles,service._pedestrians)
            timeline.append({**metrics.sample(tick,rows),"requested_phase":phase})
        wall=time.perf_counter()-start
        after=processes(pids)
        summary=metrics.summary()
        assert summary["samples"]==TICKS and summary["vehicle_passages"]>0
        assert summary["pedestrian_crossings"]>0, summary
        result={"engine":"native" if native else "legacy","summary":summary,
                "timeline":timeline,"digest":hashlib.sha256(json.dumps(timeline,sort_keys=True).encode()).hexdigest(),
                "resources":{"wall_s":wall,"cpu_delta_s":sum(after[k]["cpu_s"]-before[k]["cpu_s"] for k in before),
                             "end_combined_working_set_bytes":sum(v["working_set_bytes"] for v in after.values())}}
        if session:
            result["native_trip_arrivals"]={"vehicles":len(session.arrived),"pedestrians":len(session.person_arrived)}
        return result
    finally:
        if session:
            session.close()
            assert not session.proc.is_alive()


def main(output):
    out=Path(output)
    out.mkdir(parents=True,exist_ok=True)
    results=[]
    for native in (False,True):
        runs=[]
        for repeat in range(2):
            path=out/f"arm-{int(native)}-{repeat}.json"
            subprocess.run([sys.executable,__file__,"--arm",str(int(native)),str(path)],check=True,timeout=180)
            runs.append(json.loads(path.read_text(encoding="utf-8")))
        assert runs[0]["digest"]==runs[1]["digest"],runs[0]["engine"]
        for i,run in enumerate(runs):
            rows=run.pop("timeline")
            with (out/f"{run['engine']}-{i}.csv").open("w",newline="",encoding="utf-8") as f:
                writer=csv.DictWriter(f,fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
        results.extend(runs)
    result={"evidence":"executed actual motion, normalized gate definitions, repeated seed",
            "seed":SEED,"step_s":STEP_S,"horizon_s":TICKS*STEP_S,"runs":results,
            "physical_geometry_matched":False,"demand_matched":False,"replacement_parity":False,
            "default_migration_allowed":False,
            "limitations":"Shared normalized gate coordinate and stop threshold only. Legacy recirculating slots differ from finite native trips; native pedestrian approach uses nearest curb and can censor ambiguous visits. Requested phases matched; native occupancy may restrict applied permissions. Legacy motion helper is not an independent safety controller. Motion and measurement only; no camera rendering, HTTP, GPU or owner benchmark."}
    (out/"result.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    if sys.argv[1]=="--arm":
        Path(sys.argv[3]).write_text(json.dumps(arm(sys.argv[2]=="1")),encoding="utf-8")
    else:
        main(sys.argv[1])
