"""Development-only scoring of the independently audited every-tick cohort.

Retain all scheduled observations, including declared development-only overlaps.
Never register a live model, alter a detector setting or access reserved archives.
"""
import argparse
from collections import Counter
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from time import perf_counter
from zipfile import ZipFile

from native_detector_tick_truth_trial import ARMS,HORIZON,STEP_MS,SAMPLE_TICKS,VIEW,RESERVED,sha,write,verify
from native_detector_temporal_trial import read_capture,known_hashes
from native_detector_temporal_metrics import KINDS,evaluate_sequence,observation_gate,fault_checks,compare_passages,presence
from native_detector_temporal_review import review_sequence,availability
from native_detector_batch import latency_summary
from app.services.sumo_midblock_fixture import slots_for

MANIFEST_SHA="be29a8517d2c3cc1b6420af669a9404611380c440fe8d92c92316b030feea4ef"
PRIOR_OVERLAP=frozenset(["1103/0000/capture.zip","1103/0002/capture.zip"]+
    [f"1409/{t:04d}/capture.zip" for t in (0,2,4,6,8,12)])
REPEATED=frozenset(f"1301/{t:04d}/capture.zip" for t in range(0,20,2))


def admit_pixels(name,pixels,excluded,old,seen):
    if pixels & excluded:
        raise ValueError("Known training/validation/historical/reserved pixel overlap")
    flags={"prior_temporal_overlap":bool(pixels&old),"within_cohort_repeat":bool(pixels&seen)}
    if flags!={"prior_temporal_overlap":name in PRIOR_OVERLAP,"within_cohort_repeat":name in REPEATED}:
        raise ValueError("Unexpected development overlap identity")
    seen.update(pixels)
    return flags


def self_test():
    seen=set()
    assert admit_pixels("1103/0000/capture.zip",{"old"},{"blocked"},{"old"},seen)=={
        "prior_temporal_overlap":True,"within_cohort_repeat":False}
    assert admit_pixels("1201/0000/capture.zip",{"new"},{"blocked"},{"old"},seen)=={
        "prior_temporal_overlap":False,"within_cohort_repeat":False}
    assert admit_pixels("1301/0000/capture.zip",{"new"},{"blocked"},{"old"},seen)=={
        "prior_temporal_overlap":False,"within_cohort_repeat":True}
    for name,pixels in (("1409/0000/capture.zip",{"blocked"}),("1201/0002/capture.zip",{"old"}),
                        ("1301/0002/capture.zip",{"unexpected"})):
        try:
            admit_pixels(name,pixels,{"blocked"},{"old"},seen)
        except ValueError:
            pass
        else:
            raise AssertionError("Unexpected overlap admission")
    print("Expanded temporal overlap guards passed")


def evaluate(captures,prior,old_temporal,retained_review,export,reference,evidence):
    from native_detector_openvino import BoundOpenVINO,descriptor,snapshot_export
    from native_detector_tiled import tiled_predict
    from app.services.native_detector_validation import score_footprints
    evidence.mkdir(parents=True,exist_ok=False)
    manifest_bytes=(captures/"manifest.json").read_bytes()
    if sha(manifest_bytes)!=MANIFEST_SHA:
        raise ValueError("Expanded cohort manifest changed")
    manifest=json.loads(manifest_bytes)
    # Reproduce the prior ground-truth review before any model is constructed.
    verified_path=evidence/"ground-truth-review.json"
    verify(captures,prior,old_temporal,verified_path)
    ground=json.loads(verified_path.read_bytes())
    if ground!=json.loads(retained_review.read_bytes()):
        raise ValueError("Frozen every-tick review changed")
    excluded=known_hashes(prior)
    old=json.loads(old_temporal.read_bytes())
    old_pixels={h for row in old["records"].values() for h in row["pixels"].values()}
    seen=set()
    flags={}
    for seed,*_ in ARMS:
        for name,rec in sorted(manifest["sequences"][str(seed)]["records"].items()):
            # verify() checked decoded bytes and archive digest; later inference
            # independently rechecks the archived bytes against the same manifest.
            flags[name]=admit_pixels(name,set(rec["pixels"].values()),excluded,old_pixels,seen)
    if len(flags)!=1204 or len(seen)!=4776 or sum(v["prior_temporal_overlap"] for v in flags.values())!=8 or sum(v["within_cohort_repeat"] for v in flags.values())!=10:
        raise ValueError("Expanded cohort admission totals changed")
    write(evidence/"admission.json",{"manifest_sha256":MANIFEST_SHA,"capture_count":len(flags),
        "distinct_orientation_hashes":len(seen),"capture_flags":flags,
        "historical_reserved_training_validation_overlap_count":0,"formal_holdout_used":False,
        "scope":"complete correlated development sequences only; not independent holdout"})
    method=descriptor(export)
    frozen=json.loads(reference.read_bytes())
    if {k:v for k,v in method.items() if k!="python"}!={k:v for k,v in frozen.items() if k!="python"}:
        raise ValueError("Qualified detector method changed")
    write(evidence/"plan.json",{"method":method,"reference_method":frozen,"capture_manifest_sha256":MANIFEST_SHA,
        "formal_holdout_used":False,"absolute_criteria":None,"sampling_ms":STEP_MS*SAMPLE_TICKS,
        "view":VIEW,"scope":"expanded development only","order":ARMS,
        "deadline_rule":"unchanged diagnostic serial next-sample deadline; reset virtual queue per scenario",
        "passage_rule":"unchanged strict same-direction bracket overlap; native ambiguity retained separately",
        "overlap_rule":"retain all frames, fresh inference each; report flagged sample support separately; no pooled independent reliability claim"})
    write(evidence/"faults.json",fault_checks())
    runs=[]
    with TemporaryDirectory(prefix="mesh-expanded-bound-") as temp:
        model=BoundOpenVINO(snapshot_export(export,Path(temp)/"export",method),method)
        for seed,density,geometry,mode in ARMS:
            arm=next(r["truth"] for r in ground["runs"] if r["seed"]==seed)
            seq=manifest["sequences"][str(seed)]
            trace_bytes=(captures/str(seed)/"native-ticks.jsonl").read_bytes()
            if sha(trace_bytes)!=seq["trace_sha256"]:
                raise ValueError("Native trace changed")
            trace=[json.loads(line) for line in trace_bytes.splitlines()]
            zone,scale=arm["zone"],arm["scale"]
            limits={kind:max([11 if kind=="vehicle" else 1.5]+[s.speed for s in slots_for(seed,density) if s.kind==kind]) for kind in KINDS}
            expected_identity={k:arm["identity"][k] for k in ("epoch","generation","layout_id")}
            expected_identity["view_id"]=VIEW
            frames=[];scenes=[];available=0.;last=-1
            with (evidence/f"frames-{seed}.jsonl").open("x",encoding="utf-8") as stream:
                for tick in range(0,HORIZON+1,SAMPLE_TICKS):
                    name=f"{seed}/{tick:04d}/capture.zip"
                    rec=seq["records"][name]
                    raw=(captures/name).read_bytes()
                    if sha(raw)!=rec["archive_sha256"]:
                        raise ValueError("Expanded capture changed after admission")
                    ann,images,hashes,scene=read_capture(raw,tick)
                    if hashes!=rec["pixels"] or scene!=trace[tick]:
                        raise ValueError("Expanded capture identity changed")
                    identity={k:ann[k] for k in ("epoch","generation","layout_id")}
                    identity["view_id"]=VIEW
                    if identity!=expected_identity:
                        raise ValueError("Unexpected source identity")
                    start=perf_counter()
                    pred,unmapped,details=tiled_predict(images[VIEW],ann,VIEW,model)
                    elapsed=(perf_counter()-start)*1000
                    time_ms=tick*STEP_MS
                    available=max(available,time_ms)+elapsed
                    obs={**identity,"tick":tick,"capture_ms":time_ms,"completed_ms":available}
                    gate=observation_gate(obs,expected_identity,available,time_ms+STEP_MS*SAMPLE_TICKS,last,True)
                    if gate["usable"]:
                        last=tick
                    frame={"capture":name,"archive_sha256":rec["archive_sha256"],"time_ms":time_ms,
                        "truth":ann["views"][VIEW],"predictions":pred,"unmapped":unmapped,**details,
                        "score":score_footprints(ann["views"][VIEW],pred,.5),"inference_ms":elapsed,
                        "serial_completion_ms":available,"serial_age_ms":available-time_ms,"gate":gate,
                        "development_overlap":flags[name]}
                    frames.append(frame);scenes.append(scene)
                    stream.write(json.dumps(frame,allow_nan=False)+"\n")
                    stream.flush()
            run={"seed":seed,"density":density,"geometry":geometry,"mode":mode,"zone":zone,"scale":scale,
                "speed_limits_m_s":limits,"sample_count":len(frames),
                "metrics":json.loads(json.dumps(evaluate_sequence(frames,zone,scale,limits))),
                "latency":latency_summary([f["inference_ms"] for f in frames]),
                "serial_age":latency_summary([f["serial_age_ms"] for f in frames]),
                "deadline_usable":sum(f["gate"]["usable"] for f in frames)}
            supplementary=review_sequence(frames,scenes,run)
            for kind in KINDS:
                truth=arm["classes"][kind]
                raw=run["metrics"][kind]
                sup=supplementary[kind]
                # Native reference must reconcile with frozen independent truth.
                if sup["native_center_sensitivity"]["truth_counts"]!=truth["sampled_native"]["counts"] or raw["truth_counts"]!=truth["sampled_raster"]["counts"]:
                    raise ValueError("Reference count mismatch")
                if sup["native_center_sensitivity"]["passages"]["truth"]!=truth["sampled_native"]["passages"] or raw["passages"]["truth"]!=truth["sampled_raster"]["passages"]:
                    raise ValueError("Reference event mismatch")
                sup["every_tick_native_passages"]=compare_passages(truth["every_tick_native"]["passages"],raw["passages"]["predicted"])
                sup["reference_ambiguity"]={k:v for k,v in truth.items() if k not in ("every_tick_native","sampled_native","sampled_raster")}
                # Sample-only metrics by overlap flags; never cut the temporal
                # track or pretend excluded observations were absent.
                strata={}
                for label,indices in (
                    ("flagged",[i for i,f in enumerate(frames) if any(f["development_overlap"].values())]),
                    ("unflagged",[i for i,f in enumerate(frames) if not any(f["development_overlap"].values())])):
                    if not indices:
                        strata[label]={"sample_count":0}
                        continue
                    p=[raw["predicted_counts"][i] for i in indices]
                    g=[frames[i]["gate"]["usable"] for i in indices]
                    strata[label]={"sample_count":len(indices)}
                    for key,counts in (("raster",raw["truth_counts"]),("native",truth["sampled_native"]["counts"])):
                        t=[counts[i] for i in indices]
                        strata[label][key]={"presence":presence([n>0 for n in t],[n>0 for n in p]),
                            "availability":availability(t,p,g)}
                sup["overlap_sample_strata"]=strata
            run["supplementary"]=supplementary
            runs.append(run)
            write(evidence/f"sequence-{seed}.json",run)
        write(evidence/"report.json",{"runs":runs,"runtime":model.runtime_evidence(),"method":method,
            "formal_holdout_used":False,"absolute_qualification":False,"physical_output_allowed":False,
            "limitations":"Four correlated native synthetic scenarios; exact overlap flags; strict sample brackets, no continuous-time truth; serial replay not live latency. No training, holdout, production or safety validation."})
    print("Expanded development evaluation complete; no acceptance verdict")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("self-test","evaluate"))
    for name in ("captures","prior","old-temporal","retained-review","export","reference","evidence"):
        p.add_argument("--"+name,type=Path)
    a=p.parse_args()
    if a.action=="self-test":
        self_test()
    else:
        args=(a.captures,a.prior,a.old_temporal,a.retained_review,a.export,a.reference,a.evidence)
        if not all(args):
            p.error("Explicit pinned inputs required")
        evaluate(*args)
