"""Native normalized-gate experiment contract; not the legacy per-visit metric schema."""
from __future__ import annotations
from collections import Counter
from app.services.simulation_gate_metrics import STEP_S


def summarize_timeline(timeline,summary):
    n=len(timeline)
    duration=n*STEP_S
    phases=Counter(row["phase"] for row in timeline)
    return {"duration_s":round(duration,6),
            "mean_vehicle_queue":round(sum(row["vehicle_queue"] for row in timeline)/n,6) if n else None,
            "mean_pedestrian_queue":round(sum(row["pedestrian_queue"] for row in timeline)/n,6) if n else None,
            "vehicle_passages_per_min":round(summary["vehicle_passages"]*60/duration,6) if n else None,
            "pedestrian_crossing_events_per_min":round(summary["pedestrian_crossings"]*60/duration,6) if n else None,
            "vehicle_queue_occupied_s":round(sum(row["vehicle_queue"]>0 for row in timeline)*STEP_S,6),
            "pedestrian_queue_occupied_s":round(sum(row["pedestrian_queue"]>0 for row in timeline)*STEP_S,6),
            "simultaneous_queue_s":round(sum(row["vehicle_queue"]>0 and row["pedestrian_queue"]>0 for row in timeline)*STEP_S,6),
            "requested_phase_s":{key:round(count*STEP_S,6) for key,count in sorted(phases.items())}}


def validate_pair(fixed,adaptive):
    keys=("seed","density","geometry","layout_id","demand_digest","metric_contract","step_s")
    if any(fixed.get(k)!=adaptive.get(k) or fixed.get(k) is None for k in keys):
        raise ValueError("Native comparison arms are not matched")
    if fixed.get("engine") != adaptive.get("engine"):
        raise ValueError("Comparison engines differ")
    if fixed["mode"]!="fixed" or adaptive["mode"]!="adaptive":
        raise ValueError("Incorrect comparison mode")
    if len(fixed["timeline"])!=len(adaptive["timeline"]) or not fixed["timeline"]:
        raise ValueError("Native comparison horizons differ")
    for f,a in zip(fixed["timeline"],adaptive["timeline"]):
        if f["tick"]!=a["tick"] or f["t"]!=a["t"]:
            raise ValueError("Native comparison sample times differ")
    if fixed.get("demand_manifest") != adaptive.get("demand_manifest"):
        raise ValueError("Native comparison demand manifests differ")
    deltas={}
    for key in ("vehicle_wait_agent_s","pedestrian_wait_agent_s","vehicle_passages","pedestrian_crossings","peak_vehicle_queue","peak_pedestrian_queue","censored_pedestrian_visits"):
        first,second=fixed["summary"][key],adaptive["summary"][key]
        deltas[key]={"difference":round(second-first,6),"percent_change":round((second-first)*100/first,6) if first else None}
    return deltas
