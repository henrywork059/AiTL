"""Measure actual inference stages on the pinned development cohort; no holdout or live registration."""
import argparse
from contextlib import contextmanager, nullcontext
from collections import Counter
import json
import math
import os
from pathlib import Path
import platform
import resource
import shutil
import sys
from tempfile import TemporaryDirectory
from importlib.metadata import version
from time import perf_counter, process_time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2] / "AI_Traffic_Light"
sys.path.insert(0, str(ROOT / "scripts"))
from native_detector_batch import capture_input, file_sha256, latency_summary, summarize
from native_detector_tiled import tiled_predict, method_descriptor, METHOD
from app.services.native_detector_validation import score_footprints
from app.services.sumo_projection import VIEW_FLIPS

CHECKPOINT = "9c888355e3228db090c98969672a4418eb207e1c0ffa926746091485da84ecba"
STAGES = ("preprocess", "inference", "postprocess")
EXPORT_SETTINGS = {"format":"openvino","imgsz":640,"batch":8,"dynamic":True,"nms":False,"device":"cpu","quantize":None}
OV_PROPERTIES = ("EXECUTION_DEVICES","INFERENCE_NUM_THREADS","NUM_STREAMS","INFERENCE_PRECISION_HINT","PERFORMANCE_HINT")


def export_hashes(directory):
    files = sorted(p for p in directory.rglob("*") if p.is_file())
    if (not files or any(p.is_symlink() for p in files)
            or len(list(directory.glob("*.xml"))) != 1 or len(list(directory.glob("*.bin"))) != 1
            or not (directory/"metadata.yaml").is_file()):
        raise ValueError("Unexpected OpenVINO export files")
    return {p.relative_to(directory).as_posix():file_sha256(p) for p in files}


def read_export(root, *, shape_profile=None, parent=None):
    manifest = json.loads((root/"manifest.json").read_text(encoding="utf-8"))
    directory = root/"model_openvino_model"
    if (manifest["checkpoint_sha256"] != CHECKPOINT or manifest["settings"] != EXPORT_SETTINGS
            or manifest["openvino_version"] != version("openvino")
            or manifest["ultralytics_version"] != version("ultralytics")
            or manifest["files"] != export_hashes(directory)):
        raise ValueError("Export identity mismatch")
    if shape_profile is not None:
        from native_detector_openvino import validate_export, EXPORT_MANIFEST, FILES
        if shape_profile == "dynamic":
            validate_export(root)
            if parent is not None:
                raise ValueError("Unexpected parent for audited dynamic graph")
        elif shape_profile == "static-spatial":
            if parent is None:
                raise ValueError("Missing audited parent")
            validate_export(parent)
            if (manifest.get("specialization") != {"parent_manifest_sha256":EXPORT_MANIFEST,
                    "parent_files":FILES,"operation":"reshape_spatial_only",
                    "input_shape":[-1,3,640,640],"compress_to_fp16":False}
                    or file_sha256(directory/"metadata.yaml") != FILES["metadata.yaml"]):
                raise ValueError("Specialized graph parent identity mismatch")
        else:
            raise ValueError("Unknown graph shape profile")
        import openvino as ov
        graph = ov.Core().read_model(str(next(directory.glob("*.xml"))))
        inputs, outputs = graph_interface(graph)
        expected = "[?,3,640,640]" if shape_profile=="static-spatial" else "[?,3,?,?]"
        if inputs != [{"shape":expected,"type":"f32"}] or inputs != manifest["inputs"] or outputs != manifest["outputs"]:
            raise ValueError("Graph shape/interface mismatch")
        if len(outputs)!=1 or outputs[0]["type"]!="f32" or any(
                op.get_type_name() in ("NonMaxSuppression","MulticlassNms","MatrixNms") for op in graph.get_ops()):
            raise ValueError("Unexpected output interface or embedded suppression")
    return directory, manifest


def graph_interface(graph):
    return ([{"shape":str(x.partial_shape),"type":x.element_type.get_type_name()} for x in graph.inputs],
            [{"shape":str(x.partial_shape),"type":x.element_type.get_type_name()} for x in graph.outputs])


def specialize_spatial_graph(graph):
    before, _ = graph_interface(graph)
    if before != [{"shape":"[?,3,?,?]","type":"f32"}]:
        raise ValueError("Unexpected dynamic FP32 source graph")
    graph.reshape([-1,3,640,640])
    after, _ = graph_interface(graph)
    if after != [{"shape":"[?,3,640,640]","type":"f32"}]:
        raise ValueError("Spatial-only reshape failed")


def specialize_export(parent, root):
    from native_detector_openvino import validate_export, EXPORT_MANIFEST, FILES
    manifest = validate_export(parent)
    directory, verified = read_export(parent,shape_profile="dynamic")
    if manifest != verified:
        raise ValueError("Inconsistent parent export")
    import openvino as ov
    root.mkdir(parents=True,exist_ok=False)
    destination=root/"model_openvino_model"
    destination.mkdir()
    start=perf_counter()
    graph=ov.Core().read_model(str(directory/"model.xml"))
    specialize_spatial_graph(graph)
    # No quantization, no FP16 compression, no re-export from .pt.
    ov.save_model(graph,str(destination/"model.xml"),compress_to_fp16=False)
    shutil.copyfile(directory/"metadata.yaml",destination/"metadata.yaml")
    saved=ov.Core().read_model(str(destination/"model.xml"))
    inputs,outputs=graph_interface(saved)
    write(root/"manifest.json",{**manifest,"inputs":inputs,"outputs":outputs,
          "files":export_hashes(destination),
          "specialization":{"parent_manifest_sha256":EXPORT_MANIFEST,"parent_files":FILES,
                            "operation":"reshape_spatial_only","input_shape":[-1,3,640,640],
                            "compress_to_fp16":False},
          "specialization_wall_ms":(perf_counter()-start)*1000})
    read_export(root,shape_profile="static-spatial",parent=parent)
    validate_export(parent)


def export_openvino(weights, root):
    if file_sha256(weights) != CHECKPOINT:
        raise ValueError("Unexpected reference checkpoint")
    import openvino as ov
    from ultralytics import YOLO
    root.mkdir(parents=True, exist_ok=False)
    t = perf_counter()
    with TemporaryDirectory(prefix="mesh-ov-export-") as temp:
        snapshot = Path(temp)/"model.pt"
        shutil.copyfile(weights,snapshot)
        if file_sha256(snapshot) != CHECKPOINT:
            raise ValueError("Checkpoint changed during export")
        exported = Path(YOLO(str(snapshot),task="detect").export(**EXPORT_SETTINGS))
        directory = root/"model_openvino_model"
        shutil.copytree(exported,directory)
    graph = ov.Core().read_model(str(next(directory.glob("*.xml"))))
    inputs = [{"shape":str(x.partial_shape),"type":x.element_type.get_type_name()} for x in graph.inputs]
    outputs = [{"shape":str(x.partial_shape),"type":x.element_type.get_type_name()} for x in graph.outputs]
    if len(inputs)!=1 or inputs[0]["type"]!="f32" or any(x["type"]!="f32" for x in outputs):
        raise ValueError("Expected FP32 graph interface")
    write(root/"manifest.json",{"checkpoint_sha256":CHECKPOINT,"settings":EXPORT_SETTINGS,
          "openvino_version":version("openvino"),"ultralytics_version":version("ultralytics"),
          "files":export_hashes(directory),"inputs":inputs,"outputs":outputs,
          "export_wall_ms":(perf_counter()-t)*1000})


@contextmanager
def explicit_fp32_cpu_compile(inference_threads=2):
    """Only in isolated trials: prevent hardware-dependent auto BF16."""
    if inference_threads not in (2,4):
        raise ValueError("Unsupported experimental inference thread count")
    import openvino as ov
    original = ov.Core.compile_model

    def compile_cpu(core, model, device_name=None, config=None, **kwargs):
        if device_name not in (None, "CPU", "AUTO"):
            raise ValueError("Unexpected OpenVINO compilation device: "+str(device_name))
        settings = dict(config or {})
        settings.update({"INFERENCE_PRECISION_HINT":ov.Type.f32,
                         "INFERENCE_NUM_THREADS":inference_threads,"NUM_STREAMS":1,
                         "PERFORMANCE_HINT":"LATENCY"})
        return original(core, model, device_name="CPU", config=settings, **kwargs)

    with patch.object(ov.Core,"compile_model",compile_cpu):
        yield


def shape_runtime_verified(properties, shape_profile, inference_threads=2):
    from native_detector_openvino import PROPERTIES
    expected_shape = "[?,3,640,640]" if shape_profile=="static-spatial" else "[?,3,?,?]"
    expected = {**PROPERTIES,"INFERENCE_NUM_THREADS":str(inference_threads)}
    return (inference_threads in (2,4) and cpu_backend_observed(properties)
            and all(properties.get(k)==v for k,v in expected.items())
            and properties.get("compiled_input_shape")==expected_shape
            and properties.get("compiled_input_type")=="f32")


def openvino_properties(model):
    # Record actual library-managed CPU configuration, not assumed defaults.
    backend = getattr(getattr(model,"predictor",None),"model",None)
    compiled = getattr(backend,"ov_compiled_model",None)
    if compiled is None:
        compiled = getattr(getattr(backend,"backend",None),"ov_compiled_model",None)
    if compiled is None:
        return {"available":False}
    result = {"available":True}
    try:
        result["compiled_input_shape"] = str(compiled.input(0).partial_shape)
        result["compiled_input_type"] = compiled.input(0).element_type.get_type_name()
    except (AttributeError,RuntimeError,TypeError,ValueError):
        result["compiled_input_shape"] = None
        result["compiled_input_type"] = None
    for key in OV_PROPERTIES:
        try:
            result[key] = str(compiled.get_property(key))
        except (RuntimeError,TypeError,ValueError):
            result[key] = None
    return result


def cpu_backend_observed(properties):
    return properties.get("available") is True and all(properties.get(k) is not None for k in OV_PROPERTIES) and "CPU" in properties["EXECUTION_DEVICES"] and not any(x in properties["EXECUTION_DEVICES"] for x in ("GPU","NPU"))


class TimedModel:
    """Proxy only: return the original result objects without modification."""
    def __init__(self, model, torch_module=None, backend="pytorch"):
        self.model = model
        self.torch = torch_module
        self.backend = backend
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
                           "threads_after": self.torch.get_num_threads() if self.torch is not None else None,
                           **({"openvino_properties":openvino_properties(self.model)} if self.backend=="openvino" else {})})
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
    class CompiledDouble:
        def get_property(self, key):
            return ["CPU"] if key=="EXECUTION_DEVICES" else "fixture"
    backend = SimpleNamespace(predictor=SimpleNamespace(model=SimpleNamespace(ov_compiled_model=CompiledDouble())))
    assert cpu_backend_observed(openvino_properties(backend))
    assert not cpu_backend_observed(openvino_properties(SimpleNamespace()))
    assert not cpu_backend_observed({**openvino_properties(backend),"EXECUTION_DEVICES":"GPU"})
    with TemporaryDirectory() as temp:
        d = Path(temp)
        for n in ("model.xml","model.bin","metadata.yaml"):
            (d/n).write_bytes(n.encode())
        original = export_hashes(d)
        (d/"model.bin").write_bytes(b"changed")
        assert export_hashes(d)!=original
    # Exercise the actual runtime reshape API without a trained model.
    import openvino as ov
    parameter=ov.opset13.parameter([-1,3,-1,-1],ov.Type.f32)
    graph=ov.Model([ov.opset13.relu(parameter)],[parameter])
    original_compile = ov.Core.compile_model
    from native_detector_openvino import PROPERTIES
    with explicit_fp32_cpu_compile():
        core = ov.Core()
        dynamic = core.compile_model(graph,"CPU",{"INFERENCE_PRECISION_HINT":ov.Type.bf16})
        actual = {"available":True,"compiled_input_shape":str(dynamic.input(0).partial_shape),
                  "compiled_input_type":dynamic.input(0).element_type.get_type_name(),
                  **{k:str(dynamic.get_property(k)) for k in PROPERTIES}}
        assert shape_runtime_verified(actual,"dynamic")
        assert not shape_runtime_verified(actual,"dynamic",4)
        assert shape_runtime_verified({**actual,"INFERENCE_NUM_THREADS":"4"},"dynamic",4)
        assert not shape_runtime_verified({**actual,"INFERENCE_NUM_THREADS":"4"},"dynamic",2)
        assert not shape_runtime_verified({**actual,"INFERENCE_PRECISION_HINT":"<Type: 'bfloat16'>"},"dynamic")
        assert not shape_runtime_verified(actual,"static-spatial")
        try:
            core.compile_model(graph,"GPU")
        except ValueError:
            pass
        else:
            raise AssertionError("Unexpected accelerator admitted")
        specialize_spatial_graph(graph)
        static = core.compile_model(graph,"CPU")
        actual = {"available":True,"compiled_input_shape":str(static.input(0).partial_shape),
                  "compiled_input_type":static.input(0).element_type.get_type_name(),
                  **{k:str(static.get_property(k)) for k in PROPERTIES}}
        assert shape_runtime_verified(actual,"static-spatial")
    assert ov.Core.compile_model is original_compile
    try:
        with explicit_fp32_cpu_compile(3):
            pass
    except ValueError:
        pass
    else:
        raise AssertionError("Unsupported thread count admitted")
    assert graph_interface(graph)[0] == [{"shape":"[?,3,640,640]","type":"f32"}]
    try:
        specialize_spatial_graph(graph)
    except ValueError:
        pass
    else:
        raise AssertionError("Non-dynamic source admitted")
    print("Timing proxy, stage aggregation, thread recording, backend identity, spatial reshape and invalid timing rejection passed")


def boxes(rows):
    return Counter((r["class_name"],tuple(r["box_xyxy"])) for r in rows)


def write(path, data):
    path.write_text(json.dumps(data,indent=2,allow_nan=False),encoding="utf-8")


def run(captures, weights, reference, evidence, *, thread_profile=None, run_label=None, backend="pytorch", export_dir=None, shape_profile=None, parent_export=None, ov_inference_threads=2):
    if platform.system() != "Linux" or file_sha256(weights) != CHECKPOINT:
        raise ValueError("Expected isolated Linux and frozen checkpoint")
    ref = json.loads(reference.read_text(encoding="utf-8"))
    reference_artifact = 15254202779 if shape_profile is not None else 15249412930
    reference_method = "tiled-stream-reuse-openvino-v1" if shape_profile is not None else METHOD
    if (ref["model_sha256"] != CHECKPOINT or ref["method"] != reference_method or ref["capture_count"] != 16
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
    if ov_inference_threads not in (2,4) or (ov_inference_threads!=2 and shape_profile!="dynamic"):
        raise ValueError("Experimental thread change requires audited dynamic graph")
    if shape_profile is not None and (backend!="openvino" or thread_profile!="2"):
        raise ValueError("Shape trial requires OpenVINO with two surrounding threads")
    descriptor = method_descriptor()
    export = None
    model_path = weights
    if backend == "openvino":
        if export_dir is None or thread_profile != "2":
            raise ValueError("OpenVINO trial requires local export and fixed PyTorch surrounding threads")
        model_path, export = read_export(export_dir,shape_profile=shape_profile,parent=parent_export)
    elif export_dir is not None:
        raise ValueError("Unexpected export for native backend")
    runtime = {"backend":backend,"requested_torch_intraop":thread_profile,"omp_num_threads":os.getenv("OMP_NUM_THREADS"),
               "profile_source_sha256":file_sha256(Path(__file__)), "export":export,
               "shape_profile":shape_profile,
               "compilation_policy":f"explicit-fp32-cpu-{ov_inference_threads}-threads-1-stream-latency" if shape_profile is not None else "library-default",
               "requested_ov_inference_threads":ov_inference_threads if shape_profile is not None else None,
               "qualification_scope":"development-only; not a formal schema-2 method"}
    write(evidence/"plan.json", {"method":descriptor,"model_sha256":CHECKPOINT,
        "reference_artifact":reference_artifact,"capture_artifact":15245454146,
        "formal_holdout_used":False,"migration_authorized":False,
        "thread_profile":thread_profile,"run_label":run_label,"runtime":runtime,
        "timing_scope":"Single frame wall includes decode, crop, reuse, conversion and merge; excludes scoring and capture admission. Model call wall includes preprocessing/inference/postprocessing and startup. Results.speed is library-reported, not independently instrumented kernels."})
    import torch
    from ultralytics import YOLO
    if shape_profile is not None and torch.get_num_interop_threads()!=4:
        torch.set_num_interop_threads(4)
    model = YOLO(str(model_path), task="detect")
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
        proxy = TimedModel(model, torch, backend)
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
            proxy = TimedModel(model, torch, backend)
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
    observed = [c["openvino_properties"] for v in rows for c in v["calls"]] if backend=="openvino" else []
    backend_observed = backend=="pytorch" or (bool(observed) and all(cpu_backend_observed(p) for p in observed))
    if shape_profile is not None:
        warmup_observed = [c["openvino_properties"] for c in warmup["calls"]]
        backend_observed = (backend_observed and bool(warmup_observed)
                            and all(shape_runtime_verified(p,shape_profile,ov_inference_threads)
                                    for p in observed+warmup_observed))
        runtime["warmup_openvino_properties_verified"] = bool(warmup_observed) and all(
            shape_runtime_verified(p,shape_profile,ov_inference_threads) for p in warmup_observed)
        thread_consistent = thread_consistent and all(v["torch_num_interop_threads"]==4 for v in rows)
    runtime["actual_torch_intraop"] = expected_threads
    runtime["actual_torch_interop"] = sorted({v["torch_num_interop_threads"] for v in rows})
    runtime["observed_openvino_properties"] = list({json.dumps(p,sort_keys=True):p for p in observed}.values())
    runtime["cpu_backend_identity_verified"] = backend_observed
    if backend == "openvino":
        _, after = read_export(export_dir,shape_profile=shape_profile,parent=parent_export)
        if after != export:
            raise ValueError("Export changed during evaluation")
    report={"model_sha256":CHECKPOINT,"method":descriptor,"reference_artifact":reference_artifact,"runtime":runtime,
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
    if not backend_observed:
        raise SystemExit("OpenVINO CPU runtime properties not verified; retain negative evidence")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=("self-test","run","export","specialize"))
    p.add_argument("--shape-profile",choices=("dynamic","static-spatial"))
    p.add_argument("--parent-export",type=Path)
    p.add_argument("--ov-inference-threads",type=int,choices=(2,4),default=2)
    p.add_argument("--backend",choices=("pytorch","openvino"),default="pytorch")
    p.add_argument("--export-dir",type=Path)
    p.add_argument("--thread-profile",choices=("default","1","2","4"))
    p.add_argument("--run-label")
    for name in ("captures","weights","reference","evidence"):
        p.add_argument("--"+name,type=Path)
    a=p.parse_args()
    if a.mode=="self-test":
        self_test()
    elif a.mode=="export":
        if not all((a.weights,a.export_dir)):
            p.error("export requires weights and export-dir")
        export_openvino(a.weights,a.export_dir)
    elif a.mode=="specialize":
        if not all((a.parent_export,a.export_dir)):
            p.error("specialize requires parent-export and export-dir")
        specialize_export(a.parent_export,a.export_dir)
    else:
        if not all((a.captures,a.weights,a.reference,a.evidence)):
            p.error("run requires all inputs")
        with explicit_fp32_cpu_compile(a.ov_inference_threads) if a.shape_profile is not None else nullcontext():
            run(a.captures,a.weights,a.reference,a.evidence,thread_profile=a.thread_profile,run_label=a.run_label,backend=a.backend,export_dir=a.export_dir,shape_profile=a.shape_profile,parent_export=a.parent_export,ov_inference_threads=a.ov_inference_threads)
