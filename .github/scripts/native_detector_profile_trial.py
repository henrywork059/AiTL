"""Measure actual inference stages on the pinned development cohort; no holdout or live registration."""
import argparse
from collections import Counter
import json
import math
import os
from pathlib import Path
import platform
import resource
import sys
from time import perf_counter, process_time

ROOT = Path(__file__).resolve().parents[2] / "AI_Traffic_Light"
sys.path.insert(0, str(ROOT / "scripts"))
from native_detector_batch import capture_input, file_sha256, latency_summary, summarize
from native_detector_tiled import tiled_predict, method_descriptor, METHOD
from app.services.native_detector_validation import score_footprints
from app.services.sumo_projection import VIEW_FLIPS

CHECKPOINT = "9c888355e3228db090c98969672a4418eb207e1c0ffa926746091485da84ecba"
STAGES = ("preprocess", "inference", "postprocess")


class TimedModel:
    """Proxy only: return the original result objects without modification."""
    def __init__(self, model, torch_module=None):
        self.model = model
        self.torch = torch_module
        self.calls = []

    def __getattr__(self, name):
        return getattr(self.model, name)

    def predict(self, *, source, **kwargs):
        before_threads = self.torch.get_num_threads() if self.torch is not None else None
        start = perf_counter()
        cpu = process_time()
        results = self.model.predict(source=source, **kwargs)
        elapsed = (perf_counter()-start)*1000
        cpu_ms = (process_time()-cpu)*1000
        if len(results) != len(source):
            raise ValueError("Unexpected timed prediction cardinality")
        # Ultralytics Results.speed is reported per image in milliseconds.
        # Keep raw entries and sum across the returned unique images only.
        speeds = []
        for result in results:
            speed = getattr(result, "speed", None)
            if not isinstance(speed, dict):
                raise ValueError("Model did not expose stage timings")
            row = {stage: float(speed[stage]) for stage in STAGES}
            if any(not math.isfinite(v) or v < 0 for v in row.values()):
                raise ValueError("Invalid stage timing")
            speeds.append(row)
        self.calls.append({"unique_images": len(source), "wall_ms": elapsed,
                           "cpu_ms": cpu_ms, "per_image_reported_ms": speeds,
                           "threads_before": before_threads,
                           "threads_after": self.torch.get_num_threads() if self.torch is not None else None})
        return results


def stage_totals(calls, wall):
    model = sum(c["wall_ms"] for c in calls)
    stage = {s: sum(v[s] for c in calls for v in c["per_image_reported_ms"]) for s in STAGES}
    # Residuals are signed diagnostic differences, not separately timed stages.
    return {"frame_wall_ms": wall, "model_wall_ms": model,
            "model_cpu_ms": sum(c["cpu_ms"] for c in calls),
            **{s+"_reported_ms": v for s,v in stage.items()},
            "outside_model_wall_ms": wall-model,
            "model_unattributed_wall_ms": model-sum(stage.values())}


def self_test():
    from types import SimpleNamespace
    class Fake:
        def predict(self, *, source, **kwargs):
            return [SimpleNamespace(speed={"preprocess":1,"inference":2,"postprocess":3})
                    for _ in source]
    proxy = TimedModel(Fake())
    result = proxy.predict(source=[0,1])
    assert len(result)==2 and len(proxy.calls)==1
    totals = stage_totals(proxy.calls, proxy.calls[0]["wall_ms"]+5)
    assert totals["inference_reported_ms"]==4
    assert abs(totals["outside_model_wall_ms"]-5)<1e-9
    class Bad:
        def predict(self, **kwargs):
            return [SimpleNamespace(speed={"preprocess":1,"inference":float("nan"),"postprocess":3})]
    try:
        TimedModel(Bad()).predict(source=[0])
    except ValueError:
        pass
    else:
        raise AssertionError("Nonfinite timing admitted")
    class ThreadDouble:
        def get_num_threads(self):
            return 2
    threaded = TimedModel(Fake(), ThreadDouble())
    threaded.predict(source=[0])
    assert threaded.calls[0]["threads_before"] == threaded.calls[0]["threads_after"] == 2
    print("Timing proxy, stage aggregation, thread recording, and invalid timing rejection passed")


def boxes(rows):
    return Counter((r["class_name"],tuple(r["box_xyxy"])) for r in rows)


def write(path, data):
    path.write_text(json.dumps(data,indent=2,allow_nan=False),encoding="utf-8")


def run(captures, weights, reference, evidence, *, thread_profile=None, run_label=None):
    if platform.system() != "Linux" or file_sha256(weights) != CHECKPOINT:
        raise ValueError("Expected isolated Linux and frozen checkpoint")
    ref = json.loads(reference.read_text(encoding="utf-8"))
    if (ref["model_sha256"] != CHECKPOINT or ref["method"] != METHOD or ref["capture_count"] != 16
            or ref["production_detector_validated"] is not False
            or "DEVELOPMENT REGRESSION ONLY" not in ref["holdout"]["plan"]["holdout_selection"]):
        raise ValueError("Unexpected development reference")
    expected = {r["capture_name"]:r for r in ref["records"]}
    names = sorted(p.relative_to(captures).as_posix() for p in captures.rglob("capture.zip"))
    if len(names) != 16 or set(names) != set(expected):
        raise ValueError("Unexpected capture cohort")
    for name in names:
        if file_sha256(captures/name) != expected[name]["archive_sha256"]:
            raise ValueError("Unexpected capture digest")
    evidence.mkdir(parents=True,exist_ok=False)
    descriptor = method_descriptor()
    write(evidence/"plan.json", {"method":descriptor,"model_sha256":CHECKPOINT,
        "reference_artifact":15249412930,"capture_artifact":15245454146,
        "formal_holdout_used":False,"migration_authorized":False,
        "thread_profile":thread_profile,"run_label":run_label,
        "timing_scope":"Single frame wall includes decode, crop, reuse, conversion and merge; excludes scoring and capture admission. Model call wall includes preprocessing/inference/postprocessing and startup. Results.speed is library-reported, not independently instrumented kernels."})
    import torch
    from ultralytics import YOLO
    model = YOLO(str(weights))
    # Warm up once on a fixed, already-evaluated development view. Explicit
    # intra-op settings are applied before and re-applied after lazy model
    # initialization, since the library may change the process thread count.
    # Keep cold work separate; do not hide it or include it in warm summaries.
    warmup = None
    requested = int(thread_profile) if thread_profile not in (None, "default") else None
    if thread_profile is not None:
        ann, images, integrity, digest = capture_input(captures/names[0],captures,None,set())
        if digest != expected[names[0]]["archive_sha256"] or not integrity["hash_manifest_verified"]:
            raise ValueError("Unqualified warmup archive")
        initial_threads = torch.get_num_threads()
        if requested is not None:
            torch.set_num_threads(requested)
        first_view = next(iter(VIEW_FLIPS))
        proxy = TimedModel(model, torch)
        t = perf_counter()
        cpu = process_time()
        predictions, unmapped, details = tiled_predict(images[first_view],ann,first_view,proxy)
        warm_wall = (perf_counter()-t)*1000
        warm_cpu = (process_time()-cpu)*1000
        after_initialization = torch.get_num_threads()
        if requested is not None:
            torch.set_num_threads(requested)
        warmup = {"capture_name":names[0],"view":first_view,"frame_wall_ms":warm_wall,
                  "frame_cpu_ms":warm_cpu,"initial_threads":initial_threads,
                  "threads_after_initialization":after_initialization,
                  "threads_after_configuration":torch.get_num_threads(),
                  "work":details["work"],"calls":proxy.calls,
                  "geometry_equal":boxes(predictions)==boxes(expected[names[0]]["views"][first_view]["predictions"]),
                  "unmapped_equal":boxes(unmapped)==boxes(expected[names[0]]["views"][first_view]["unmapped_classes"])}
        write(evidence/"warmup.json",warmup)
    expected_threads = torch.get_num_threads()
    records = []
    for name in names:
        ann, images, integrity, digest = capture_input(captures/name,captures,None,set())
        if digest != expected[name]["archive_sha256"] or not integrity["hash_manifest_verified"]:
            raise ValueError("Unqualified development archive")
        views = {}
        for view in VIEW_FLIPS:
            proxy = TimedModel(model, torch)
            t = perf_counter()
            cpu = process_time()
            predictions, unmapped, details = tiled_predict(images[view],ann,view,proxy)
            wall = (perf_counter()-t)*1000
            frame_cpu = (process_time()-cpu)*1000
            score = score_footprints(ann["views"][view],predictions,.5)
            old = expected[name]["views"][view]
            parity = {"merged":boxes(predictions)==boxes(old["predictions"]),
                      "raw":len(details["tiles"])==len(old["tiles"])==45 and all(
                        a["origin_xy"]==b["origin_xy"] and a["tile_index"]==b["tile_index"] and
                        boxes(a["local_predictions"])==boxes(b["local_predictions"]) for a,b in zip(details["tiles"],old["tiles"])),
                      "scores":score["by_kind"]==old["score"]["by_kind"],
                      "unmapped":boxes(unmapped)==boxes(old["unmapped_classes"]),
                      "work":details["work"]==old["work"]}
            if len(proxy.calls)!=details["work"]["model_calls"] or sum(c["unique_images"] for c in proxy.calls)!=details["work"]["evaluated"]:
                raise ValueError("Timing counters disagree with work")
            views[view] = {"predictions":predictions,"unmapped_classes":unmapped,**details,
                           "score":score,"prediction_latency_ms":wall,"frame_cpu_ms":frame_cpu,
                           "timing":stage_totals(proxy.calls,wall),"calls":proxy.calls,"parity":parity,
                           "exact_predictions_equal":predictions==old["predictions"],
                           "torch_num_threads":torch.get_num_threads(),"torch_num_interop_threads":torch.get_num_interop_threads()}
        records.append({"capture_name":name,"archive_sha256":digest,"views":views})
    rows=[v for r in records for v in r["views"].values()]
    if len(rows)!=64:
        raise ValueError("Incomplete profile")
    # latency_summary requires nonnegative samples; residuals may be signed.
    summaries={}
    for k in rows[0]["timing"]:
        values=[v["timing"][k] for v in rows]
        summaries[k]={"mean_ms":sum(values)/len(values),"p95_ms":sorted(values)[math.ceil(.95*len(values))-1],"raw_ms":values}
    usage=resource.getrusage(resource.RUSAGE_SELF)
    thread_consistent = all(v["torch_num_threads"] == expected_threads and all(
        c["threads_before"] == c["threads_after"] == expected_threads for c in v["calls"]) for v in rows)
    if requested is not None:
        thread_consistent = thread_consistent and expected_threads == requested
    report={"model_sha256":CHECKPOINT,"method":descriptor,"reference_artifact":15249412930,
            "formal_holdout_used":False,"migration_authorized":False,"physical_output_allowed":False,
            "production_detector_validated":False,"view_count":len(rows),"stage_summaries":summaries,
            "thread_profile":thread_profile,"run_label":run_label,"warmup":warmup,
            "expected_intraop_threads":expected_threads,"thread_configuration_consistent":thread_consistent,
            "exact_prediction_view_count":sum(v["exact_predictions_equal"] for v in rows),
            "frame_cpu":latency_summary([v["frame_cpu_ms"] for v in rows]),
            "resources":{"peak_rss_kib":usage.ru_maxrss,"process_user_cpu_s":usage.ru_utime,
                         "process_system_cpu_s":usage.ru_stime,"affinity_count":len(os.sched_getaffinity(0)),
                         "omp_num_threads":os.getenv("OMP_NUM_THREADS"),"platform":platform.platform()},
            "parity_counts":{k:sum(v["parity"][k] for v in rows) for k in rows[0]["parity"]},
            "views":{view:{"micro":summarize(r["views"][view]["score"] for r in records),
                           "latency":latency_summary([r["views"][view]["prediction_latency_ms"] for r in records])} for view in VIEW_FLIPS},
            "limitations":"Measured instrumented development workload only; library speed sums are estimates of internal stages, residuals can be signed, profiling overhead included; thread profiles exclude one separately retained cold warmup; ordinary profile includes first call. Runtime thread configuration is diagnostic, not a frozen schema-2 method identity or live setting. No Windows or multi-camera resource claim."}
    write(evidence/"summary.json",report)
    write(evidence/"profile.json",{**report,"records":records})
    if not all(v==64 for v in report["parity_counts"].values()):
        raise SystemExit("Profile did not preserve detection parity; retain negative evidence")
    if thread_profile is not None and not thread_consistent:
        raise SystemExit("Runtime thread configuration changed; retain negative evidence")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=("self-test","run"))
    p.add_argument("--thread-profile",choices=("default","1","2","4"))
    p.add_argument("--run-label")
    for name in ("captures","weights","reference","evidence"):
        p.add_argument("--"+name,type=Path)
    a=p.parse_args()
    if a.mode=="self-test":
        self_test()
    else:
        if not all((a.captures,a.weights,a.reference,a.evidence)):
            p.error("run requires all inputs")
        run(a.captures,a.weights,a.reference,a.evidence,thread_profile=a.thread_profile,run_label=a.run_label)
