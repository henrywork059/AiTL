"""Run actual SUMO and a separate finite legacy-style reference over one manifest."""
from pathlib import Path
import csv
import hashlib
import json
import os
import sys
import time

from sumo_migration_trial import processes
from app.services.sumo_shadow_runtime import GeneratedSession
from app.services.simulation_finite_fixture import load_trips,FiniteReference,RouteGateAdapter
from app.services.simulation_gate_metrics import GateMetrics,STEP_S

SEED=42
TICKS=2500
CYCLE=["vehicle_green"]*100+["vehicle_yellow"]*15+["all_red"]*10+["pedestrian_green"]*150+["pedestrian_flashing"]*50+["all_red"]*10


def execute(trips,session=None):
    native=session is not None
    reference=None if native else FiniteReference(trips)
    adapter=RouteGateAdapter(trips)
    metrics=GateMetrics()
    pids=[os.getpid()]+([session.proc.pid] if native else [])
    before=processes(pids)
    start=time.perf_counter()
    timeline=[]
    seen=set()
    for tick in range(1,TICKS+1):
        phase=CYCLE[(tick-1)%len(CYCLE)]
        if native:
            session.set_phase(phase)
            session.advance()
            agents=session.agents()
        else:
            agents=reference.advance(phase)
        seen.update(a.engine_id for a in agents)
        timeline.append({**metrics.sample(tick,adapter.observations(agents)),"requested_phase":phase})
    wall=time.perf_counter()-start
    after=processes(pids)
    arrived=(session.arrived|session.person_arrived) if native else reference.arrived
    completion_ok = arrived==seen=={t.ident for t in trips}
    expected={t.ident:[s.road_id for s in t.path] for t in trips}
    route_mismatches={i:{"expected":expected[i],"observed":adapter.seen_roads.get(i,[])}
                      for i in expected if adapter.seen_roads.get(i)!=expected[i]}
    allowed={t.ident:[[s.road_id for s in path] for path in (t.path,*t.alternatives)] for t in trips}
    unsupported={i:adapter.seen_roads.get(i,[]) for i in allowed
                 if adapter.seen_roads.get(i,[]) not in allowed[i]}
    # Preserve discrepancies as evidence; never declare route parity if native
    # traverses a different route or sampling misses a short segment.
    summary=metrics.summary()
    return {"engine":"native" if native else "finite_reference","summary":summary,
            "timeline":timeline,"digest":hashlib.sha256(json.dumps(timeline,sort_keys=True).encode()).hexdigest(),
            "arrived":sorted(arrived),"completion_ok":completion_ok,"seen":sorted(seen),
            "route_mismatches":route_mismatches,"unsupported_routes":unsupported,
            "unknown_roads":sorted(adapter.unknown_roads),
            "resources":{"wall_s":wall,"cpu_delta_s":sum(after[k]["cpu_s"]-before[k]["cpu_s"] for k in before),
                         "end_combined_working_set_bytes":sum(v["working_set_bytes"] for v in after.values())}}


def main(output):
    out=Path(output)
    out.mkdir(parents=True,exist_ok=True)
    results=[]
    manifest=None
    for repeat in range(2):
        session=GeneratedSession(SEED,density="normal")
        try:
            trips=load_trips(session.network_path,session.network_path.parent/"routes.xml")
            from dataclasses import asdict
            current=[asdict(t) for t in trips]
            if manifest is None:
                manifest=current
                (out/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
                (out/"network.xml").write_bytes(session.network_path.read_bytes())
                (out/"routes.xml").write_bytes((session.network_path.parent/"routes.xml").read_bytes())
            else:
                assert manifest==current
            run=execute(trips,session)
        finally:
            session.close()
            assert not session.proc.is_alive()
        # Native process is reaped before reference measurements.
        for result in (run,execute(trips)):
            rows=result.pop("timeline")
            with (out/f"{result['engine']}-{repeat}.csv").open("w",newline="",encoding="utf-8") as f:
                writer=csv.DictWriter(f,fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            results.append(result)
            (out/f"{result['engine']}-{repeat}-summary.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    result={"evidence":"executed finite-demand reference and native route-aware measurement",
            "seed":SEED,"step_s":STEP_S,"horizon_s":TICKS*STEP_S,"runs":results,
            "offered_demand_matched":True,
            "observed_road_sequence_matched":all(not r["route_mismatches"] and not r["unknown_roads"] for r in results),
            "allowed_route_sequences_verified":all(not r["unsupported_routes"] and not r["unknown_roads"] for r in results),
            "physical_service_gate_geometry_matched":True,
            "full_pedestrian_path_geometry_matched":False,
            "replacement_parity":False,"default_migration_allowed":False,
            "limitations":"One generated road manifest and finite offers; vehicle lane polylines and crossing gates shared. Reference walking areas use chords; native pedestrian dynamics differ. Reference is a new isolated legacy-style constant-speed model, not production legacy engine. Same requested phases, not necessarily same occupancy-limited permissions. Resource samples sequential in same interpreter, not fresh-process replacement or GPU benchmarks."}
    (out/"result.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))
    assert results[0]["digest"]==results[2]["digest"]
    assert results[1]["digest"]==results[3]["digest"]
    assert all(r["completion_ok"] and r["summary"]["vehicle_passages"]==8 and r["summary"]["pedestrian_crossings"]==14 for r in results), "Expected eight passages and fourteen observed crossing completions per arm"
    assert result["allowed_route_sequences_verified"], "Unrecognized observed road sequences"


if __name__=="__main__":
    main(sys.argv[1])
