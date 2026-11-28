"""Read-only supplementary review of the frozen Update 28C development evidence.

No inference, new detector settings, reserved capture access or controller authority.
"""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
from zipfile import ZipFile

from native_detector_temporal_metrics import (KINDS, inside, line_events, presence,
    episode_comparison, compare_passages, zone_from_scene, evaluate_sequence)

CAPTURE_SHA = "e9b9b079e13c3067351c34bf33df74d3e312904c3af7d7aa77922718be7dced3"
EVIDENCE_SHA = "4747d9bf0b5ba708d0167cf0824399c0e590cea9cdea1a4d5ed6da96cb78fe45"
PREFIX = "temporal-evidence/"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_json(z, name):
    return json.loads(z.read(name))


def native_centers(scene, kind):
    scale = scene["pixels_per_m"]
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("Invalid native scale")
    points = {}
    for agent in scene["agents"]:
        if agent["kind"] != kind:
            continue
        x,y = agent["x"],agent["y"]
        if kind == "vehicle":
            length = agent["length_m"]
            if not math.isfinite(length) or length<=0 or type(agent["eastbound"]) is not bool:
                raise ValueError("Invalid vehicle body geometry")
            x += (-1 if agent["eastbound"] else 1)*length*scale/2
        if agent["id"] in points or not all(math.isfinite(v) for v in (x,y)):
            raise ValueError("Invalid native identity or center")
        points[agent["id"]] = (x,y)
    return points


def availability(truth_counts, predicted_counts, usable):
    """Unavailable is unknown, never a negative detection or a correct empty sample."""
    if not (len(truth_counts)==len(predicted_counts)==len(usable)) or not usable:
        raise ValueError("Unaligned availability inputs")
    if any(type(v) is not bool for v in usable):
        raise ValueError("Invalid admission flag")
    out = {}
    for occupied,name in ((True,"occupied"),(False,"empty")):
        selected = [(p>0,g) for t,p,g in zip(truth_counts,predicted_counts,usable)
                    if (t>0)==occupied]
        correct = sum(g and p==occupied for p,g in selected)
        incorrect = sum(g and p!=occupied for p,g in selected)
        unknown = sum(not g for _,g in selected)
        out[name] = {"support":len(selected),"timely_correct":correct,
                     "timely_incorrect":incorrect,"unavailable":unknown,
                     "timely_correct_fraction_of_all":correct/len(selected) if selected else None,
                     "correct_fraction_given_timely":correct/(correct+incorrect) if correct+incorrect else None}
    return out


def review_sequence(frames, scenes, run):
    if len(frames)!=len(scenes) or len(frames)!=run["sample_count"]:
        raise ValueError("Incomplete sequence")
    zone,scale = run["zone"],run["scale"]
    times = [f["time_ms"] for f in frames]
    if len(times)<2 or any(b<=a for a,b in zip(times,times[1:])):
        raise ValueError("Invalid sample order")
    for f,s in zip(frames,scenes):
        if (s["tick"]*200!=f["time_ms"] or s["pixels_per_m"]!=scale
            or zone_from_scene(s)!=zone or s["seed"]!=run["seed"]):
            raise ValueError("Native scene identity mismatch")
        if any(f["gate"][k] is not False for k in
               ("physical_output_allowed","movement_authorized","clearance_shortening_allowed")):
            raise ValueError("Unexpected authority")
    # Reconstruct the original metric output; integer dictionary keys become
    # strings in JSON. The original records must not be replaced or retuned.
    original = json.loads(json.dumps(evaluate_sequence(frames,zone,scale,run["speed_limits_m_s"])))
    if original != run["metrics"]:
        raise ValueError("Frozen metrics do not reproduce")
    output = {}
    usable = [f["gate"]["usable"] for f in frames]
    if sum(usable)!=run["deadline_usable"]:
        raise ValueError("Admission totals disagree")
    for kind in KINDS:
        frozen = original[kind]
        old,events,counts = {},[],[]
        for i,scene in enumerate(scenes):
            current = native_centers(scene,kind)
            counts.append(sum(inside(p,zone) for p in current.values()))
            if i:
                events.extend(line_events(old,current,zone,kind,times[i-1],times[i]))
            old = current
        pred = frozen["predicted_counts"]
        t,p = [n>0 for n in counts],[n>0 for n in pred]
        err = sum(abs(a-b) for a,b in zip(counts,pred))
        output[kind] = {
            "raster_reference":{k:v for k,v in frozen.items() if k!="tracks"},
            "native_center_sensitivity":{
                "truth_counts":counts,"zone_presence":presence(t,p),
                "episodes":episode_comparison(t,p,times),
                "passages":compare_passages(events,frozen["passages"]["predicted"]),
                "occupancy_mae":err/len(frames),
                "occupancy_normalized_absolute_error":err/sum(counts) if sum(counts) else None},
            "availability_raster":availability(frozen["truth_counts"],pred,usable),
            "availability_native":availability(counts,pred,usable),
        }
    return output


def review(captures, evidence):
    # Read once and verify exact archive bytes before opening either ZIP.
    capture_bytes,evidence_bytes = captures.read_bytes(),evidence.read_bytes()
    if sha(capture_bytes)!=CAPTURE_SHA or sha(evidence_bytes)!=EVIDENCE_SHA:
        raise ValueError("Only the exact audited development archives are admitted")
    with ZipFile(io.BytesIO(capture_bytes)) as c, ZipFile(io.BytesIO(evidence_bytes)) as e:
        manifest_bytes = c.read("manifest.json")
        manifest = json.loads(manifest_bytes)
        admission = read_json(e,PREFIX+"admission.json")
        report = read_json(e,PREFIX+"report.json")
        plan = read_json(e,PREFIX+"plan.json")
        if (manifest["formal_holdout_used"] is not False or admission["formal_holdout_used"] is not False
            or report["formal_holdout_used"] is not False or report["absolute_qualification"] is not False
            or report["physical_output_allowed"] is not False or plan["absolute_criteria"] is not None
            or plan["capture_manifest_sha256"]!=sha(manifest_bytes)
            or admission["manifest_sha256"]!=sha(manifest_bytes) or admission["overlap_names"]
            or report["method"]!=plan["method"] or report["method"]!=plan["reference_method"]):
            raise ValueError("Unexpected scope or method identity")
        runs = []
        seen = set()
        for run in report["runs"]:
            seed = run["seed"]
            if run!=read_json(e,PREFIX+f"sequence-{seed}.json"):
                raise ValueError("Sequence report mismatch")
            frames = [json.loads(line) for line in e.read(PREFIX+f"frames-{seed}.jsonl").splitlines()]
            expected = [f"{seed}/{tick:04d}/capture.zip" for tick in manifest["ticks"]]
            if [f["capture"] for f in frames]!=expected or seen.intersection(expected):
                raise ValueError("Sequence order or identity mismatch")
            seen.update(expected)
            scenes = []
            for name,f in zip(expected,frames):
                record = manifest["records"][name]
                raw = c.read(name)
                if sha(raw)!=record["archive_sha256"] or f["archive_sha256"]!=record["archive_sha256"]:
                    raise ValueError("Capture digest mismatch")
                with ZipFile(io.BytesIO(raw)) as archive:
                    scene = read_json(archive,"scene.json")
                    ann = read_json(archive,"synthetic_footprints.json")
                    if (f["truth"]!=ann["views"][manifest["view"]]
                        or any(scene[k]!=v for k,v in record["identity"].items())
                        or scene["layout_id"]!=record["layout_id"] or scene["tick"]!=record["tick"]):
                        raise ValueError("Capture reference mismatch")
                    scenes.append(scene)
            runs.append({"seed":seed,"sample_count":len(frames),
                         "review":review_sequence(frames,scenes,run)})
        if seen!=set(manifest["records"]) or len(seen)!=admission["capture_count"]:
            raise ValueError("Incomplete capture coverage")
    return {"scope":"supplementary development-only review; original raster metrics retained",
            "capture_sha256":CAPTURE_SHA,"evidence_sha256":EVIDENCE_SHA,
            "formal_holdout_used":False,"absolute_qualification":False,
            "physical_output_allowed":False,"runs":runs,
            "limitations":"Native centers are a sensitivity reference, not continuous-time truth; frozen prediction tracks and strict sample brackets are unchanged. Availability is based on diagnostic serial replay, not actual live delivery."}


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--captures",type=Path,required=True)
    p.add_argument("--evidence",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    if args.output.resolve() in (args.captures.resolve(),args.evidence.resolve()):
        p.error("Output must not overwrite source artifacts")
    result=review(args.captures,args.evidence)
    with args.output.open("x",encoding="utf-8") as out:
        json.dump(result,out,indent=2,allow_nan=False)
    print("Supplementary review complete; no qualification verdict")
