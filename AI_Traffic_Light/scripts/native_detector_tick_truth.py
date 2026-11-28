"""Native sampled ground-truth diagnostics, independent of detector predictions.

Every native tick is observed; an event is still a bracket, not an exact
continuous-time crossing. No controller authority or acceptance threshold.
"""
from collections import defaultdict
import json
import math
from native_detector_temporal_metrics import KINDS, center, inside, line_events, episodes, zone_from_scene
from native_detector_temporal_review import native_centers

STEP_MS = 200
SAMPLE_TICKS = 2


def freeze_scene(scene):
    """Detach exact JSON wire representation, including tuple-to-list geometry."""
    return json.loads(json.dumps(scene,allow_nan=False))


def event_groups(events):
    groups = defaultdict(list)
    for i,event in enumerate(events):
        groups[(event["id"],event["direction"])].append(i)
    return groups


def bracket_review(native, sampled):
    """Compare references by true identity/direction, never prediction identity.

    Unique pairs may overlap, touch or be disjoint. Repeated identity/direction
    is explicitly ambiguous; no forced match or retrospective tolerance.
    """
    a,b=event_groups(native),event_groups(sampled)
    rows=[]
    for key in sorted(a.keys() | b.keys()):
        left,right=a.get(key,[]),b.get(key,[])
        if not left:
            status="sample_only"
        elif not right:
            status="native_only"
        elif len(left)!=1 or len(right)!=1:
            status="ambiguous_repeated_identity"
        else:
            x,y=native[left[0]],sampled[right[0]]
            delta=min(x["stop_ms"],y["stop_ms"])-max(x["start_ms"],y["start_ms"])
            status="overlap" if delta>0 else "touching" if delta==0 else "disjoint"
        rows.append({"id":key[0],"direction":key[1],"native_indices":left,
                     "sampled_indices":right,"status":status})
    return rows


def collisions(events, sample_times):
    """Retain all native events sharing the same sampled direction/bracket."""
    buckets=defaultdict(list)
    for i,event in enumerate(events):
        hit=[j for j in range(1,len(sample_times))
             if min(event["stop_ms"],sample_times[j])>max(event["start_ms"],sample_times[j-1])]
        if len(hit)!=1:
            raise ValueError("Every-tick event must lie in exactly one sampled bracket")
        buckets[(hit[0],event["direction"])].append(i)
    return [{"start_ms":sample_times[j-1],"stop_ms":sample_times[j],
             "direction":direction,"native_indices":ids}
            for (j,direction),ids in sorted(buckets.items()) if len(ids)>1]


def series(points, times, zone, kind):
    counts=[sum(inside(p,zone) for p in row.values()) for row in points]
    ev=[]
    for i in range(1,len(points)):
        ev.extend(line_events(points[i-1],points[i],zone,kind,times[i-1],times[i]))
    ep=episodes([n>0 for n in counts],times)
    return {"counts":counts,"occupied_samples":sum(n>0 for n in counts),
            "empty_samples":sum(n==0 for n in counts),"passages":ev,"episodes":ep,
            "complete_episodes":sum(not x["left_censored"] and not x["right_censored"] for x in ep)}


def analyze(scenes, sampled_footprints):
    """All ticks starting at zero; fixed even-tick detector sample schedule."""
    if len(scenes)<3 or (len(scenes)-1)%SAMPLE_TICKS:
        raise ValueError("Incomplete tick sequence")
    first=scenes[0]
    identity={k:first[k] for k in ("epoch","generation","layout_id","seed","geometry","density","engine","provenance","coordinate_space","demand_digest")}
    if identity["engine"]!="native" or identity["provenance"]!="synthetic_sumo_projection" or identity["coordinate_space"]!="native_projection_v1":
        raise ValueError("Not isolated native truth")
    zone=zone_from_scene(first)
    scale=first["pixels_per_m"]
    expected_samples=list(range(0,len(scenes),SAMPLE_TICKS))
    if sorted(sampled_footprints)!=expected_samples:
        raise ValueError("Incomplete sampled frame schedule")
    for tick,scene in enumerate(scenes):
        if (scene["tick"]!=tick or not math.isclose(scene["time_s"]*1000,tick*STEP_MS,abs_tol=.01)
            or any(scene[k]!=v for k,v in identity.items()) or scene["pixels_per_m"]!=scale
            or zone_from_scene(scene)!=zone or scene["paused"]):
            raise ValueError("Native tick/identity/geometry mismatch")
        if tick and scene["signal"] is None:
            raise ValueError("Missing native phase observation")
        sig=scene["signal"]
        if sig is not None and (sig["vehicle_go"] and sig["pedestrian_walk"] or
                               sig["applied_vehicle_go"] and sig["applied_pedestrian_walk"]):
            raise ValueError("Conflicting protected permission")
        if len({a["id"] for a in scene["agents"]})!=len(scene["agents"]) or any(a["kind"] not in KINDS for a in scene["agents"]):
            raise ValueError("Invalid native agents")
        if tick and scene["received_at_ms"]<scenes[tick-1]["received_at_ms"]:
            raise ValueError("Nonmonotonic native receipt time")
    times=[i*STEP_MS for i in range(len(scenes))]
    sample_times=[times[i] for i in expected_samples]
    out={}
    for kind in KINDS:
        points=[native_centers(s,kind) for s in scenes]
        raster=[]
        for tick in expected_samples:
            rows=[r for r in sampled_footprints[tick] if r["kind"]==kind]
            pts={r["agent_id"]:center(r) for r in rows}
            if len(pts)!=len(rows) or pts.keys()!=points[tick].keys():
                raise ValueError("Sampled raster/native identities differ")
            raster.append(pts)
        full=series(points,times,zone,kind)
        sampled=series([points[i] for i in expected_samples],sample_times,zone,kind)
        ras=series(raster,sample_times,zone,kind)
        # Full episodes with no occupied sample are unobservable on this grid.
        hidden=[i for i,e in enumerate(full["episodes"])
                if not any(e["first"]<=tick<e["stop"] for tick in expected_samples)]
        out[kind]={"every_tick_native":full,"sampled_native":sampled,"sampled_raster":ras,
                   "native_vs_sampled_brackets":bracket_review(full["passages"],sampled["passages"]),
                   "native_vs_raster_brackets":bracket_review(full["passages"],ras["passages"]),
                   "same_direction_bracket_collisions":collisions(full["passages"],sample_times),
                   "hidden_occupancy_episode_indices":hidden,
                   "sampled_boundary_count_disagreements":[tick for j,tick in enumerate(expected_samples)
                       if sampled["counts"][j]!=ras["counts"][j]]}
    return {"identity":identity,"zone":zone,"scale":scale,"tick_count":len(scenes),
            "sample_count":len(expected_samples),"native_step_ms":STEP_MS,
            "sample_interval_ms":STEP_MS*SAMPLE_TICKS,"classes":out,
            "formal_holdout_used":False,"absolute_qualification":False,"physical_output_allowed":False}
