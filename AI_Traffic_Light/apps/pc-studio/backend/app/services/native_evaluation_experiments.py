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


def vehicle_braking_sample(before,after):
    """Same-journey finite-difference deceleration, not a collision or comfort test.
    Exclude insertions/arrivals: there is no consecutive speed sample.
    Thresholds are diagnostic, not approved traffic-engineering limits.
    """
    previous={a.id:a for a in before if a.kind=="vehicle"}
    events=[]
    count=0
    peak=0.
    for a in after:
        old=previous.get(a.id)
        if a.kind!="vehicle" or old is None:
            continue
        count+=1
        deceleration=max(0.,(old.speed_m_s-a.speed_m_s)/STEP_S)
        peak=max(peak,deceleration)
        if deceleration>4.5+1e-6:
            events.append({"agent_id":a.id,"from_road":old.road_id,"to_road":a.road_id,
                           "deceleration_m_s2":round(deceleration,6)})
    return {"vehicle_speed_pairs":count,"peak_vehicle_deceleration_m_s2":round(peak,6),
            "braking_events":sorted(events,key=lambda e:e["agent_id"])}


def summarize_braking(timeline):
    events=[(row,event) for row in timeline for event in row["braking_events"]]
    return {"contract":"consecutive_native_vehicle_speed_v1","step_s":STEP_S,
            "threshold_m_s2":4.5,"severe_threshold_m_s2":9.,
            "speed_pairs":sum(row["vehicle_speed_pairs"] for row in timeline),
            "peak_deceleration_m_s2":max((row["peak_vehicle_deceleration_m_s2"] for row in timeline),default=0.),
            "threshold_exceedance_samples":len(events),
            "severe_exceedance_samples":sum(event["deceleration_m_s2"]>9. for _,event in events),
            "affected_journeys":len({event["agent_id"] for _,event in events}),
            "by_requested_phase":dict(sorted(Counter(row["phase"] for row,_ in events).items())),
            "physical_safety_validated":False}

