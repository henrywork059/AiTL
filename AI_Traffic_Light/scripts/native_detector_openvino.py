"""Explicit offline OpenVINO qualification for the audited original export only.

No live registration, model downloading, automatic backend selection or fallback.
"""
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import shutil
import sys

from native_detector_tiled import method_descriptor as base_descriptor

METHOD = "tiled-stream-reuse-openvino-v1"
CHECKPOINT = "9c888355e3228db090c98969672a4418eb207e1c0ffa926746091485da84ecba"
EXPORT_MANIFEST = "ddd22de4972ab3e2f335d02343ab0ba5cfe49ce4379ecf2ddab40beb06a87d1d"
FILES = {
    "metadata.yaml": "53d57be2e90a1275824b22759437a1b3b2ee4cbb4c013caeee95b727b4123de0",
    "model.bin": "6a2861a6b3b857151f0fdaab5c63471d0187119ac0869d8e5608966799775804",
    "model.xml": "2d01de4bce32b451756448fba1ba23883e4c7366cfc3010b52933e138ecb0881",
}
PROPERTIES = {"EXECUTION_DEVICES": "['CPU']", "INFERENCE_NUM_THREADS": "2",
              "NUM_STREAMS": "1", "INFERENCE_PRECISION_HINT": "<Type: 'float32'>",
              "PERFORMANCE_HINT": "LATENCY"}
VERSIONS = {"openvino": "2026.0.0", "ultralytics": "8.4.220",
            "torch": "2.11.0+cpu", "torchvision": "0.26.0+cpu",
            "numpy": "2.2.1", "opencv": "4.10.0"}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def validate_export(root):
    root = Path(root)
    directory = root/"model_openvino_model"
    manifest = root/"manifest.json"
    if (root.is_symlink() or directory.is_symlink() or manifest.is_symlink()
            or not directory.is_dir() or not manifest.is_file()
            or {p.name for p in root.iterdir()} != {"manifest.json","model_openvino_model"}
            or {p.name for p in directory.iterdir()} != set(FILES)):
        raise ValueError("Unexpected audited export layout")
    if digest(manifest) != EXPORT_MANIFEST:
        raise ValueError("Audited export manifest mismatch")
    data = json.loads(manifest.read_bytes())
    if data["checkpoint_sha256"] != CHECKPOINT or data["files"] != FILES:
        raise ValueError("Export checkpoint provenance mismatch")
    for name, expected in FILES.items():
        path = directory/name
        if path.is_symlink() or not path.is_file() or digest(path) != expected:
            raise ValueError("Audited export file mismatch: "+name)
    return data


def descriptor(root):
    manifest = validate_export(root)
    base = base_descriptor()
    versions = {**base["versions"],"openvino":version("openvino")}
    if (sys.platform != "linux" or os.getenv("OMP_NUM_THREADS") != "4"
            or versions != VERSIONS):
        raise ValueError("Unqualified OpenVINO dependency/platform/environment identity")
    source = Path(__file__).resolve()
    return {**base,"id":METHOD,"versions":versions,
            "source_sha256":{**base["source_sha256"],"scripts/native_detector_openvino.py":digest(source)},
            "runtime":{"backend":"openvino","source_checkpoint_sha256":CHECKPOINT,
                       "export_artifact_id":15253197259,"export_manifest_sha256":EXPORT_MANIFEST,
                       "export_files":FILES.copy(),"export_settings":manifest["settings"],
                       "graph_inputs":manifest["inputs"],"graph_outputs":manifest["outputs"],
                       "omp_num_threads":"4","torch_intraop":2,"torch_interop":4,
                       "compiled_properties":PROPERTIES.copy(),
                       "startup":"no_prequalification_capture_warmup; first admitted view includes initialization"}}


def snapshot_export(root, destination, expected):
    if descriptor(root) != expected:
        raise ValueError("OpenVINO method identity changed before snapshot")
    destination = Path(destination)
    destination.mkdir()
    directory = destination/"model_openvino_model"
    directory.mkdir()
    shutil.copyfile(Path(root)/"manifest.json", destination/"manifest.json")
    for name in FILES:
        shutil.copyfile(Path(root)/"model_openvino_model"/name,directory/name)
    if descriptor(destination) != expected:
        raise ValueError("OpenVINO export snapshot changed")
    return destination


def observed_properties(model):
    backend = getattr(getattr(model,"predictor",None),"model",None)
    compiled = getattr(backend,"ov_compiled_model",None)
    if compiled is None:
        compiled = getattr(getattr(backend,"backend",None),"ov_compiled_model",None)
    if compiled is None:
        raise ValueError("OpenVINO compiled model unavailable")
    return {key:str(compiled.get_property(key)) for key in PROPERTIES}


class BoundOpenVINO:
    """Check actual runtime before accepting every unique-tile model result."""
    qualification_method = METHOD

    def __init__(self, snapshot, expected):
        import torch
        from ultralytics import YOLO
        if descriptor(snapshot) != expected:
            raise ValueError("OpenVINO snapshot method mismatch")
        self.root = Path(snapshot)
        self.method = expected
        self.torch = torch
        self.model = YOLO(str(self.root/"model_openvino_model"),task="detect")
        torch.set_num_threads(2)
        if torch.get_num_interop_threads()!=4:
            torch.set_num_interop_threads(4)
        self.calls = 0
        self.evaluated = 0
        self.last_properties = None
        self.check_threads()

    def __getattr__(self,name):
        return getattr(self.model,name)

    def check_threads(self):
        if (self.torch.get_num_threads()!=2 or self.torch.get_num_interop_threads()!=4
                or os.getenv("OMP_NUM_THREADS")!="4"):
            raise ValueError("OpenVINO surrounding CPU runtime changed")

    def predict(self, *, source, **kwargs):
        self.check_threads()
        if not 1 <= len(source) <= 8 or kwargs != {
                "imgsz":640,"conf":.1,"device":"cpu","verbose":False,"save":False}:
            raise ValueError("Unexpected bound inference arguments")
        results = self.model.predict(source=source,**kwargs)
        self.check_threads()
        actual = observed_properties(self.model)
        if actual != PROPERTIES:
            raise ValueError("OpenVINO compiled CPU runtime mismatch: "+str(actual))
        if len(results)!=len(source):
            raise ValueError("OpenVINO result cardinality mismatch")
        self.last_properties = actual
        self.calls += 1
        self.evaluated += len(source)
        return results

    def runtime_evidence(self):
        self.check_threads()
        if self.calls<1 or self.last_properties!=PROPERTIES:
            raise ValueError("No verified OpenVINO calls")
        if descriptor(self.root)!=self.method:
            raise ValueError("OpenVINO snapshot identity changed")
        return {"backend":"openvino","compiled_properties":self.last_properties.copy(),
                "torch_intraop":self.torch.get_num_threads(),
                "torch_interop":self.torch.get_num_interop_threads(),
                "checked_calls":self.calls,"evaluated_tiles":self.evaluated,
                "all_calls_runtime_verified":True}
