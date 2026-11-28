"""Separate native temporal development sequences and actual offline bound detector."""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from time import perf_counter
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[2]/"AI_Traffic_Light"
sys.path[:0]=[str(ROOT/"scripts"),str(ROOT/"apps/pc-studio/backend")]
from native_detector_development_trial import inspect_capture, RESERVED
from native_detector_batch import file_sha256, latency_summary
from native_detector_temporal_metrics import zone_from_scene,evaluate_sequence,observation_gate,fault_checks
from app.services.sumo_projection import VIEW_FLIPS
from app.services.sumo_midblock_fixture import slots_for

ARMS=((907,"light","midblock_compact","fixed"),(1009,"busy","midblock_wide","adaptive"))
TICKS=tuple(range(0,451,2))
STEP_MS=200
VIEW=next(iter(VIEW_FLIPS))
REFERENCE_ARTIFACT=15254202779


def write(path,data):
    path.write_text(json.dumps(data,indent=2,allow_nan=False),encoding="utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def known_hashes(path):
    manifest=json.loads(path.read_text(encoding="utf-8"))
    if manifest["formal_holdout_used"] is not False or len(manifest["records"])!=40:
        raise ValueError("Unexpected prior development manifest")
    return set(RESERVED)|{h for r in manifest["records"].values() for h in r["pixels"].values()}


def read_capture(raw,tick):
    ann,images,hashes=inspect_capture(raw,tick)
    with ZipFile(io.BytesIO(raw)) as z:
        scene=json.loads(z.read("scene.json"))
    if scene["engine"]!="native" or scene["tick"]!=tick or not math.isclose(scene["time_s"]*1000,tick*STEP_MS,abs_tol=.01):
        raise ValueError("Temporal native clock/identity mismatch")
    signal=scene["signal"]
    if signal is not None and (signal["vehicle_go"] and signal["pedestrian_walk"] or
        signal["applied_vehicle_go"] and signal["applied_pedestrian_walk"]):
        raise ValueError("Native conflicting phase")
    return ann,images,hashes,scene


def generate(out):
    from app.services.native_evaluation import NativeEvaluationService,MAX_BATCH
    out.mkdir(parents=True,exist_ok=False)
    records={}
    for seed,density,geometry,mode in ARMS:
        service=NativeEvaluationService(enabled=True)
        try:
            start=service.start(epoch=service.epoch,generation=service.generation,
                seed=seed,density=density,geometry=geometry,mode=mode)
            identity={k:start[k] for k in ("epoch","generation")}
            tick=0
            limits={kind:max([11 if kind=="vehicle" else 1.5]+[s.speed for s in slots_for(seed,density) if s.kind==kind])
                    for kind in ("vehicle","pedestrian")}
            for target in TICKS:
                while tick<target:
                    step=min(MAX_BATCH,target-tick)
                    service.step(**identity,tick=tick,steps=step,_return_scene=False)
                    tick+=step
                raw=service.capture(**identity,tick=tick)
                ann,_,hashes,scene=read_capture(raw,tick)
                name=f"{seed}/{tick:04d}/capture.zip"
                path=out/name
                path.parent.mkdir(parents=True)
                path.write_bytes(raw)
                records[name]={"archive_sha256":sha(raw),"pixels":hashes,"identity":identity,
                    "layout_id":ann["layout_id"],"zone":zone_from_scene(scene),
                    "scale":scene["pixels_per_m"],"speed_limits_m_s":limits,"tick":tick}
        finally:
            service.close()
    write(out/"manifest.json",{"scope":"temporal development only","formal_holdout_used":False,
        "arms":ARMS,"ticks":TICKS,"step_ms":STEP_MS,"view":VIEW,"records":records})


def evaluate(captures,prior,export,reference,evidence):
    from native_detector_openvino import BoundOpenVINO, descriptor, snapshot_export
    from native_detector_tiled import tiled_predict
    from app.services.native_detector_validation import score_footprints
    evidence.mkdir(parents=True,exist_ok=False)
    raw_manifest=(captures/"manifest.json").read_bytes()
    manifest=json.loads(raw_manifest)
    expected={f"{seed}/{tick:04d}/capture.zip" for seed,*_ in ARMS for tick in TICKS}
    if (manifest["formal_holdout_used"] is not False or manifest["arms"]!=[list(x) for x in ARMS]
        or manifest["ticks"]!=list(TICKS) or manifest["view"]!=VIEW or manifest["step_ms"]!=STEP_MS
        or set(manifest["records"])!=expected or expected!={p.relative_to(captures).as_posix() for p in captures.rglob("capture.zip")}):
        raise ValueError("Unexpected temporal cohort")
    known=known_hashes(prior)
    # Admit every frame before loading the model. Repeated temporal pixels are
    # legitimate observations; never select favorable frames or cache across time.
    overlaps=[]
    for name,record in manifest["records"].items():
        raw=(captures/name).read_bytes()
        if sha(raw)!=record["archive_sha256"]:
            raise ValueError("Temporal archive digest mismatch")
        ann,_,hashes,scene=read_capture(raw,record["tick"])
        if (hashes!=record["pixels"] or ann["layout_id"]!=record["layout_id"]
            or any(ann[k]!=v for k,v in record["identity"].items())
            or zone_from_scene(scene)!=record["zone"] or scene["pixels_per_m"]!=record["scale"]):
            raise ValueError("Temporal manifest identity mismatch")
        if set(hashes.values()) & known:
            overlaps.append(name)
    write(evidence/"admission.json",{"manifest_sha256":sha(raw_manifest),"capture_count":len(expected),
         "known_prior_pixel_count":len(known),"overlap_names":overlaps,"formal_holdout_used":False})
    if overlaps:
        raise ValueError("Exact prior/reserved pixel overlap; retain admission evidence")
    method=descriptor(export)
    frozen=json.loads(reference.read_text(encoding="utf-8"))
    # Python patch version is recorded; every algorithm/runtime field must
    # match the earlier development-qualified method, not a replacement graph.
    if {k:v for k,v in method.items() if k!="python"}!={k:v for k,v in frozen.items() if k!="python"}:
        raise ValueError("Qualified method changed")
    write(evidence/"plan.json",{"method":method,"reference_method":frozen,
        "reference_artifact":REFERENCE_ARTIFACT,"capture_manifest_sha256":sha(raw_manifest),
        "formal_holdout_used":False,"absolute_criteria":None,"scope":"development temporal diagnostics only",
        "sampling_ms":(TICKS[1]-TICKS[0])*STEP_MS,"view":VIEW,
        "zone_rule":"crossing lane centerline envelope expanded by half lane width; footprint centers; half-open",
        "passage_rule":"adjacent sampled center crosses axis line within transverse zone; truth IDs vs independent greedy distance tracks",
        "deadline_rule":"next sample time, diagnostic serial replay only, not safety requirement"})
    write(evidence/"faults.json",fault_checks())
    runs=[]
    with TemporaryDirectory(prefix="mesh-temporal-bound-") as temp:
        model=BoundOpenVINO(snapshot_export(export,Path(temp)/"export",method),method)
        for seed,density,geometry,mode in ARMS:
            frames=[]
            available=0.
            last=-1
            expected_identity=None
            zone=None
            scale=None
            limits=None
            for tick in TICKS:
                name=f"{seed}/{tick:04d}/capture.zip"
                record=manifest["records"][name]
                raw=(captures/name).read_bytes()
                if sha(raw)!=record["archive_sha256"]:
                    raise ValueError("Temporal capture changed after admission")
                ann,images,_,scene=read_capture(raw,tick)
                identity={**record["identity"],"layout_id":record["layout_id"],"view_id":VIEW}
                if expected_identity is None:
                    expected_identity,zone,scale,limits=identity,record["zone"],record["scale"],record["speed_limits_m_s"]
                if (identity,record["zone"],record["scale"],record["speed_limits_m_s"])!=(expected_identity,zone,scale,limits):
                    raise ValueError("Temporal sequence layout/identity changed")
                start=perf_counter()
                pred,unmapped,details=tiled_predict(images[VIEW],ann,VIEW,model)
                elapsed=(perf_counter()-start)*1000
                time_ms=tick*STEP_MS
                available=max(available,time_ms)+elapsed
                obs={**identity,"tick":tick,"capture_ms":time_ms,"completed_ms":available}
                gate=observation_gate(obs,expected_identity,available,time_ms+(TICKS[1]-TICKS[0])*STEP_MS,last,True)
                if gate["usable"]:
                    last=tick
                frame={"capture":name,"archive_sha256":record["archive_sha256"],"time_ms":time_ms,
                    "truth":ann["views"][VIEW],"predictions":pred,"unmapped":unmapped,**details,
                    "score":score_footprints(ann["views"][VIEW],pred,.5),"inference_ms":elapsed,
                    "serial_completion_ms":available,"serial_age_ms":available-time_ms,"gate":gate}
                frames.append(frame)
                # Keep partial raw evidence on error, not just successful summaries.
                with (evidence/f"frames-{seed}.jsonl").open("a",encoding="utf-8") as stream:
                    stream.write(json.dumps(frame,allow_nan=False)+"\n")
            report=evaluate_sequence(frames,zone,scale,limits)
            runs.append({"seed":seed,"density":density,"geometry":geometry,"mode":mode,"zone":zone,
                "scale":scale,"speed_limits_m_s":limits,"sample_count":len(frames),"metrics":report,
                "latency":latency_summary([f["inference_ms"] for f in frames]),
                "serial_age":latency_summary([f["serial_age_ms"] for f in frames]),
                "deadline_usable":sum(f["gate"]["usable"] for f in frames)})
            write(evidence/f"sequence-{seed}.json",runs[-1])
        runtime=model.runtime_evidence()
        write(evidence/"report.json",{"runs":runs,"runtime":runtime,"method":method,
            "formal_holdout_used":False,"absolute_qualification":False,"physical_output_allowed":False,
            "limitations":"Correlated native synthetic snapshots, canonical view only; adjacent-frame heuristic tracks, sample-bracketed events, serial replay not live latency; no field or safety validation."})
    print("Completed offline temporal development diagnostics; no acceptance verdict")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("generate","evaluate"))
    p.add_argument("--captures",type=Path,required=True)
    for name in ("prior","export","reference","evidence"):
        p.add_argument("--"+name,type=Path)
    a=p.parse_args()
    if a.action=="generate":
        generate(a.captures)
    else:
        if not all((a.prior,a.export,a.reference,a.evidence)):
            p.error("Explicit pinned inputs required")
        evaluate(a.captures,a.prior,a.export,a.reference,a.evidence)
