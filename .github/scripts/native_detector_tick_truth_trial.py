"""Generate separate every-tick native development truth and fixed sampled images.

No detector inference, live source registration, training or reserved archive access.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[2]/"AI_Traffic_Light"
sys.path[:0]=[str(ROOT/"scripts"),str(ROOT/"apps/pc-studio/backend")]
from native_detector_tick_truth import analyze,STEP_MS,SAMPLE_TICKS,freeze_scene
from native_detector_temporal_metrics import zone_from_scene
from native_detector_temporal_trial import read_capture,VIEW,RESERVED,known_hashes
from native_detector_temporal_trial import ARMS as PREVIOUS_ARMS

ARMS=((1103,"light","midblock_compact","adaptive"),
      (1201,"normal","midblock","fixed"),
      (1301,"normal","midblock","adaptive"),
      (1409,"busy","midblock_wide","fixed"))
HORIZON=600


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path,data):
    path.write_text(json.dumps(data,indent=2,allow_nan=False),encoding="utf-8")


def generate(out):
    from app.services.native_evaluation import NativeEvaluationService
    out.mkdir(parents=True,exist_ok=False)
    if {a[0] for a in ARMS} & {a[0] for a in PREVIOUS_ARMS}:
        raise ValueError("Reused temporal development seed")
    manifest={"scope":"new native temporal development; no detector evaluation",
              "formal_holdout_used":False,"arms":ARMS,"horizon_tick":HORIZON,
              "step_ms":STEP_MS,"sample_ticks":SAMPLE_TICKS,"view":VIEW,"sequences":{}}
    for seed,density,geometry,mode in ARMS:
        service=NativeEvaluationService(enabled=True)
        folder=out/str(seed)
        folder.mkdir()
        scenes=[];footprints={};records={}
        trace=folder/"native-ticks.jsonl"
        try:
            start=service.start(epoch=service.epoch,generation=service.generation,
                seed=seed,density=density,geometry=geometry,mode=mode)
            identity={k:start[k] for k in ("epoch","generation")}
            with trace.open("x",encoding="utf-8",newline="\n") as stream:
                for tick in range(HORIZON+1):
                    if tick:
                        service.step(**identity,tick=tick-1,steps=1,_return_scene=False)
                    state=service.scene()
                    if state["physical_output_allowed"] is not False or state["evaluation_only"] is not True:
                        raise ValueError("Unexpected evaluation authority")
                    if state["mode"]!=mode:
                        raise ValueError("Unexpected protected policy mode")
                    scene=freeze_scene(state["snapshot"])
                    if scene["tick"]!=tick or any(scene[k]!=v for k,v in identity.items()):
                        raise ValueError("Every-tick identity mismatch")
                    scenes.append(scene)
                    stream.write(json.dumps(scene,allow_nan=False)+"\n")
                    if tick%SAMPLE_TICKS:
                        continue
                    raw=service.capture(**identity,tick=tick)
                    ann,_,hashes,captured=read_capture(raw,tick)
                    if captured!=scene:
                        raise ValueError("Sampled capture and native tick differ")
                    if set(hashes.values()) & RESERVED:
                        raise ValueError("Known historical/reserved pixel overlap; no capture persisted")
                    path=folder/f"{tick:04d}"/"capture.zip"
                    path.parent.mkdir()
                    path.write_bytes(raw)
                    footprints[tick]=ann["views"][VIEW]
                    records[path.relative_to(out).as_posix()]={"archive_sha256":sha(raw),"pixels":hashes,"tick":tick}
            report=analyze(scenes,footprints)
            write(folder/"truth-report.json",report)
            manifest["sequences"][str(seed)]={"trace_sha256":sha(trace.read_bytes()),
                "report_sha256":sha((folder/"truth-report.json").read_bytes()),"records":records}
            # Preserve complete earlier arms if later generation fails.
            write(out/"manifest.json",manifest)
        finally:
            service.close()
    print("Every-tick native development generation complete; no detector results")


def verify(captures,prior,old_temporal,output):
    manifest=json.loads((captures/"manifest.json").read_bytes())
    if (manifest["formal_holdout_used"] is not False or manifest["arms"]!=[list(x) for x in ARMS]
        or manifest["horizon_tick"]!=HORIZON or manifest["step_ms"]!=STEP_MS
        or manifest["sample_ticks"]!=SAMPLE_TICKS or manifest["view"]!=VIEW
        or set(manifest["sequences"])!={str(a[0]) for a in ARMS}):
        raise ValueError("Unexpected new cohort")
    previous=known_hashes(prior)
    prior_manifest=json.loads(prior.read_bytes())
    old=json.loads(old_temporal.read_bytes())
    if old["formal_holdout_used"] is not False or len(old["records"])!=452:
        raise ValueError("Unexpected old temporal manifest")
    if {a[0] for a in ARMS} & ({a[1] for a in prior_manifest["arms"]}|{a[0] for a in old["arms"]}):
        raise ValueError("Prior development scenario seed reused")
    old_pixels={h for rec in old["records"].values() for h in rec["pixels"].values()}
    all_names=set();all_pixels=set();results=[];prior_overlaps=[];repeated=[]
    for seed,density,geometry,mode in ARMS:
        folder=captures/str(seed)
        seq=manifest["sequences"][str(seed)]
        raw=(folder/"native-ticks.jsonl").read_bytes()
        if sha(raw)!=seq["trace_sha256"]:
            raise ValueError("Native tick trace digest mismatch")
        scenes=[json.loads(line) for line in raw.splitlines()]
        if len(scenes)!=HORIZON+1 or any(s["seed"]!=seed or s["density"]!=density or s["geometry"]!=geometry for s in scenes):
            raise ValueError("Incomplete/mislabeled native trace")
        expected={f"{seed}/{t:04d}/capture.zip" for t in range(0,HORIZON+1,SAMPLE_TICKS)}
        if set(seq["records"])!=expected:
            raise ValueError("Incomplete capture schedule")
        footprints={}
        for name in sorted(expected):
            rec=seq["records"][name]
            tick=int(name.split("/")[1])
            raw=(captures/name).read_bytes()
            if rec["tick"]!=tick or sha(raw)!=rec["archive_sha256"]:
                raise ValueError("Capture changed")
            ann,_,hashes,captured=read_capture(raw,tick)
            if hashes!=rec["pixels"] or captured!=scenes[tick]:
                raise ValueError("Capture/trace disagreement")
            pixels=set(hashes.values())
            if pixels & RESERVED:
                raise ValueError("Historical/reserved overlap")
            if pixels & (previous|old_pixels):
                prior_overlaps.append(name)
            if pixels & all_pixels:
                repeated.append(name)
            all_pixels.update(pixels)
            all_names.add(name)
            footprints[tick]=ann["views"][VIEW]
        actual=analyze(scenes,footprints)
        retained=(folder/"truth-report.json").read_bytes()
        if sha(retained)!=seq["report_sha256"] or actual!=json.loads(retained):
            raise ValueError("Ground-truth report did not reproduce")
        results.append({"seed":seed,"density":density,"geometry":geometry,"mode":mode,"truth":actual})
    if all_names!={p.relative_to(captures).as_posix() for p in captures.rglob("capture.zip")}:
        raise ValueError("Unexpected capture files")
    write(output,{"scope":"expanded development ground-truth review only",
        "capture_manifest_sha256":sha((captures/"manifest.json").read_bytes()),
        "capture_count":len(all_names),"distinct_orientation_hashes":len(all_pixels),
        "prior_development_pixel_overlap_names":prior_overlaps,"within_cohort_repeated_pixel_names":repeated,
        "historical_reserved_overlap_count":0,"detector_scoring_admitted":False,
        "formal_holdout_used":False,"absolute_qualification":False,"physical_output_allowed":False,
        "runs":results,"limitations":"Every 200ms native tick is sampled truth, not continuous time. Fixed 400ms detector images may share empty backgrounds; overlaps retained, no independent-image or detector scoring claim. No detector execution."})
    print("Expanded native ground-truth metrics reproduced")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("generate","verify"))
    p.add_argument("--captures",type=Path,required=True)
    for name in ("prior","old-temporal","output"):
        p.add_argument("--"+name,type=Path)
    a=p.parse_args()
    if a.action=="generate":
        generate(a.captures)
    else:
        if not all((a.prior,a.old_temporal,a.output)):
            p.error("Require pinned prior manifests and output")
        verify(a.captures,a.prior,a.old_temporal,a.output)
