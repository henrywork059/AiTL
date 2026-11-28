"""Evaluation-only temporal diagnostics. No camera, controller or output authority."""
import math

KINDS = ("vehicle", "pedestrian")


def center(row):
    a,b,c,d = row["box_xyxy"]
    if not all(math.isfinite(v) for v in (a,b,c,d)) or not (0<=a<c<=1280 and 0<=b<d<=720):
        raise ValueError("Invalid original-coordinate box")
    return ((a+c)/2,(b+d)/2)


def zone_from_scene(scene):
    crossings = [lane for lane in scene["lanes"] if lane["kind"]=="crossing"]
    if len(crossings)!=1:
        raise ValueError("Expected one native midblock crossing")
    lane = crossings[0]
    xs,ys = zip(*lane["points"])
    half = lane["width_px"]/2
    zone = [min(xs)-half,min(ys)-half,max(xs)+half,max(ys)+half]
    if not (0<=zone[0]<zone[2]<=1280 and 0<=zone[1]<zone[3]<=720):
        raise ValueError("Invalid crossing zone")
    return zone


def inside(point, zone):
    x,y=point
    return zone[0]<=x<zone[2] and zone[1]<=y<zone[3]


def presence(truth, predicted):
    if len(truth)!=len(predicted) or not truth:
        raise ValueError("Empty or misaligned temporal samples")
    tp=sum(a and b for a,b in zip(truth,predicted))
    tn=sum(not a and not b for a,b in zip(truth,predicted))
    fp=sum(not a and b for a,b in zip(truth,predicted))
    fn=sum(a and not b for a,b in zip(truth,predicted))
    return {"tp":tp,"tn":tn,"fp":fp,"fn":fn,
            "sensitivity":tp/(tp+fn) if tp+fn else None,
            "specificity":tn/(tn+fp) if tn+fp else None}


def episodes(flags, times):
    """Maximal occupied sampled intervals; boundary episodes are censored."""
    out=[]
    start=None
    for i,flag in enumerate(flags):
        if flag and start is None:
            start=i
        if start is not None and (not flag or i==len(flags)-1):
            end=i if not flag else i+1
            out.append({"first":start,"stop":end,"entry_ms":times[start],
                        "exit_ms":times[end] if end<len(times) else None,
                        "left_censored":start==0,"right_censored":end==len(times)})
            start=None
    return out


def episode_comparison(truth, predicted, times):
    t,p=episodes(truth,times),episodes(predicted,times)
    candidates=sorted((-max(0,min(a["stop"],b["stop"])-max(a["first"],b["first"])),i,j)
                      for i,a in enumerate(t) for j,b in enumerate(p))
    used_t,used_p=set(),set()
    matches=[]
    for neg,i,j in candidates:
        if neg>=0:
            break
        if i in used_t or j in used_p:
            continue
        used_t.add(i); used_p.add(j)
        a,b=t[i],p[j]
        matches.append({"truth":i,"prediction":j,
            "entry_offset_ms":b["entry_ms"]-a["entry_ms"] if not (a["left_censored"] or b["left_censored"]) else None,
            "exit_offset_ms":b["exit_ms"]-a["exit_ms"] if not (a["right_censored"] or b["right_censored"]) else None})
    return {"truth":t,"predicted":p,"matches":matches,
            "missed":[i for i in range(len(t)) if i not in used_t],
            "false":[j for j in range(len(p)) if j not in used_p]}


def associate(previous, points, gate, next_id):
    """Adjacent-frame greedy distance only; no truth identities or gap bridging."""
    candidates=sorted((math.dist(a,b),i,j) for i,a in previous.items()
                      for j,b in enumerate(points))
    used=set()
    current={}
    for distance,i,j in candidates:
        if distance>gate:
            break
        if i not in current and j not in used:
            current[i]=points[j]; used.add(j)
    for j,point in enumerate(points):
        if j not in used:
            current[next_id]=point; next_id+=1
    return current,next_id


def line_events(previous, current, zone, kind, start, stop):
    """Sample-bracketed center crossings; no interpolated exact timestamps."""
    axis=0 if kind=="vehicle" else 1
    other=1-axis
    line=(zone[axis]+zone[axis+2])/2
    out=[]
    for ident in sorted(previous.keys() & current.keys()):
        a,b=previous[ident],current[ident]
        if (a[axis]<line)==(b[axis]<line):
            continue
        fraction=(line-a[axis])/(b[axis]-a[axis])
        along=a[other]+fraction*(b[other]-a[other])
        if zone[other]<=along<zone[other+2]:
            out.append({"id":ident,"direction":"positive" if b[axis]>a[axis] else "negative",
                        "start_ms":start,"stop_ms":stop})
    return out


def compare_passages(truth,predicted):
    # Same direction and overlapping (start, stop] brackets only; no tuned tolerance.
    candidates=[]
    for i,a in enumerate(truth):
        for j,b in enumerate(predicted):
            overlap=min(a["stop_ms"],b["stop_ms"])-max(a["start_ms"],b["start_ms"])
            if a["direction"]==b["direction"] and overlap>0:
                candidates.append((-overlap,i,j))
    used_t,used_p=set(),set()
    matches=[]
    for _,i,j in sorted(candidates):
        if i not in used_t and j not in used_p:
            used_t.add(i); used_p.add(j); matches.append([i,j])
    return {"truth":truth,"predicted":predicted,"matches":matches,
            "missed":[i for i in range(len(truth)) if i not in used_t],
            "false":[j for j in range(len(predicted)) if j not in used_p],
            "signed_count_error":len(predicted)-len(truth),
            "absolute_count_error":abs(len(predicted)-len(truth))}


def evaluate_sequence(frames,zone,scale,speed_limits):
    times=[f["time_ms"] for f in frames]
    if len(times)<2 or any(b<=a for a,b in zip(times,times[1:])):
        raise ValueError("Non-monotonic or insufficient temporal sequence")
    if not math.isfinite(scale) or scale<=0:
        raise ValueError("Invalid scale")
    result={}
    for kind in KINDS:
        if not math.isfinite(speed_limits[kind]) or speed_limits[kind]<=0:
            raise ValueError("Invalid declared speed")
        truth_counts=[]; prediction_counts=[]; truth_events=[]; prediction_events=[]
        previous_truth={}; previous_prediction={}; next_id=0
        tracks=[]
        for i,frame in enumerate(frames):
            rows=[r for r in frame["truth"] if r["kind"]==kind]
            truth={str(r["agent_id"]):center(r) for r in rows}
            if len(truth)!=len(rows):
                raise ValueError("Duplicate truth identities")
            points=[center(r) for r in frame["predictions"] if r["kind"]==kind]
            # Lane/slot speed limit times elapsed plus raster rounding allowance.
            gate=scale*speed_limits[kind]*(times[i]-times[i-1])/1000+math.sqrt(2) if i else 0
            predicted,next_id=associate(previous_prediction,points,gate,next_id)
            truth_counts.append(sum(inside(a,zone) for a in truth.values()))
            prediction_counts.append(sum(inside(a,zone) for a in predicted.values()))
            if i:
                truth_events.extend(line_events(previous_truth,truth,zone,kind,times[i-1],times[i]))
                prediction_events.extend(line_events(previous_prediction,predicted,zone,kind,times[i-1],times[i]))
            tracks.append({"time_ms":times[i],"gate_px":gate,"prediction_tracks":predicted})
            previous_truth,previous_prediction=truth,predicted
        t,p=[x>0 for x in truth_counts],[x>0 for x in prediction_counts]
        error=sum(abs(a-b) for a,b in zip(truth_counts,prediction_counts))
        result[kind]={"truth_counts":truth_counts,"predicted_counts":prediction_counts,
            "zone_presence":presence(t,p),"episodes":episode_comparison(t,p,times),
            "passages":compare_passages(truth_events,prediction_events),"tracks":tracks,
            "occupancy_mae":error/len(frames),
            "occupancy_normalized_absolute_error":error/sum(truth_counts) if sum(truth_counts) else None}
    return result


def observation_gate(observation, expected, now_ms, deadline_ms, last_tick, connected):
    """Diagnostic decision admission only. Never grants movement or clearance."""
    reason="usable_for_offline_diagnostics"
    if not connected:
        reason="disconnected"
    elif observation is None:
        reason="missing"
    elif any(observation.get(k)!=v for k,v in expected.items()):
        reason="identity_mismatch"
    elif observation["tick"]<=last_tick:
        reason="duplicate_or_reordered"
    elif not (observation["capture_ms"]<=observation["completed_ms"]<=now_ms<=deadline_ms):
        reason="stale_or_future"
    return {"reason":reason,"usable":reason=="usable_for_offline_diagnostics",
            "physical_output_allowed":False,"movement_authorized":False,
            "clearance_shortening_allowed":False}


def fault_checks():
    identity={"epoch":"test","generation":1,"layout_id":"fixture","view_id":"simulation_camera"}
    row={**identity,"tick":8,"capture_ms":100,"completed_ms":150}
    tests=[("fresh",row,identity,150,200,7,True,True),
           ("missing",None,identity,150,200,7,True,False),
           ("late",row,identity,201,200,7,True,False),
           ("future",row,identity,149,200,7,True,False),
           ("duplicate",row,identity,150,200,8,True,False),
           ("reordered",row,identity,150,200,9,True,False),
           ("disconnected",row,identity,150,200,7,False,False)]
    for key in identity:
        tests.append(("wrong_"+key,{**row,key:"wrong"},identity,150,200,7,True,False))
    output={}
    for name,obs,exp,now,deadline,last,connected,wanted in tests:
        actual=observation_gate(obs,exp,now,deadline,last,connected)
        if actual["usable"]!=wanted or any(actual[k] for k in
            ("physical_output_allowed","movement_authorized","clearance_shortening_allowed")):
            raise AssertionError("Offline freshness/fault invariant failed: "+name)
        output[name]=actual
    return output
