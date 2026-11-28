"""Offline binding and fail-closed checks without loading a real model."""
from contextlib import nullcontext
import copy
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from native_detector_batch import evaluate
import native_detector_openvino as ov
from native_detector_holdout import load_holdout


class OpenVINOBindingTest(unittest.TestCase):
    def test_export_identity_and_snapshot(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)/"input"
            root.mkdir()
            directory=root/"model_openvino_model"
            directory.mkdir()
            files={}
            for name in ov.FILES:
                (directory/name).write_bytes(name.encode())
                files[name]=hashlib.sha256(name.encode()).hexdigest()
            manifest={"checkpoint_sha256":ov.CHECKPOINT,"files":files,"settings":{},
                      "inputs":[],"outputs":[]}
            path=root/"manifest.json"
            path.write_text(json.dumps(manifest),encoding="utf-8")
            base={"versions":{k:v for k,v in ov.VERSIONS.items() if k!="openvino"},"source_sha256":{}}
            with patch.object(ov,"FILES",files), patch.object(ov,"EXPORT_MANIFEST",ov.digest(path)),                  patch.object(ov,"base_descriptor",return_value=base), patch.object(ov,"version",return_value="2026.0.0"),                  patch.object(ov.sys,"platform","linux"), patch.dict(os.environ,{"OMP_NUM_THREADS":"4"}):
                method=ov.descriptor(root)
                snap=ov.snapshot_export(root,Path(tmp)/"snapshot",method)
                self.assertEqual(ov.descriptor(snap),method)
                self.assertEqual(method["runtime"]["compilation_policy"],ov.COMPILATION_POLICY)
                self.assertEqual(method["runtime"]["compiled_input"],ov.COMPILED_INPUT)
                (directory/"model.bin").write_bytes(b"changed")
                with self.assertRaises(ValueError):
                    ov.descriptor(root)
                self.assertEqual(ov.descriptor(snap),method)
                (snap/"model_openvino_model"/"unexpected").write_bytes(b"extra")
                with self.assertRaises(ValueError):
                    ov.descriptor(snap)

    def test_runtime_rejects_changes(self):
        wrapper=ov.BoundOpenVINO.__new__(ov.BoundOpenVINO)
        wrapper.torch=SimpleNamespace(get_num_threads=lambda:2,get_num_interop_threads=lambda:4)
        wrapper.model=SimpleNamespace(predict=lambda **kwargs:[object() for _ in kwargs["source"]])
        wrapper.calls=wrapper.evaluated=0
        wrapper.last_properties=None
        wrapper.last_input=None
        kwargs={"source":[object()],"imgsz":640,"conf":.1,"device":"cpu","verbose":False,"save":False}
        with patch.dict(os.environ,{"OMP_NUM_THREADS":"4"}), patch.object(ov,"explicit_fp32_cpu_compile",side_effect=nullcontext), patch.object(ov,"observed_input",return_value=ov.COMPILED_INPUT.copy()):
            with patch.object(ov,"observed_properties",return_value=ov.PROPERTIES.copy()):
                self.assertEqual(len(wrapper.predict(**kwargs)),1)
                for key in ov.COMPILED_INPUT:
                    with patch.object(ov,"observed_input",return_value={**ov.COMPILED_INPUT,key:"changed"}):
                        with self.assertRaises(ValueError):
                            wrapper.predict(**kwargs)
            for key in ov.PROPERTIES:
                with patch.object(ov,"observed_properties",return_value={**ov.PROPERTIES,key:"changed"}):
                    with self.assertRaises(ValueError):
                        wrapper.predict(**kwargs)
            wrapper.torch.get_num_threads=lambda:3
            with self.assertRaises(ValueError):
                wrapper.predict(**kwargs)
        self.assertEqual(wrapper.calls,1)
        self.assertEqual(wrapper.evaluated,1)

    def test_compile_policy_scope_without_optional_runtime(self):
        class Core:
            def compile_model(self, model, device_name=None, config=None, **kwargs):
                return model,device_name,config,kwargs
        runtime=SimpleNamespace(Core=Core,Type=SimpleNamespace(f32="f32"))
        original=Core.compile_model
        with patch.dict(ov.sys.modules,{"openvino":runtime}):
            with ov.explicit_fp32_cpu_compile():
                result=Core().compile_model("graph","CPU",{"INFERENCE_PRECISION_HINT":"bf16","unrelated":1})
                self.assertEqual(result,("graph","CPU",{"INFERENCE_PRECISION_HINT":"f32",
                    "INFERENCE_NUM_THREADS":2,"NUM_STREAMS":1,"PERFORMANCE_HINT":"LATENCY","unrelated":1},{}))
                with self.assertRaises(ValueError):
                    Core().compile_model("graph","GPU")
            self.assertIs(Core.compile_model,original)
            with self.assertRaises(RuntimeError):
                with ov.explicit_fp32_cpu_compile():
                    raise RuntimeError("fixture")
            self.assertIs(Core.compile_model,original)

    @unittest.skipUnless(os.getenv("MESH_OPENVINO_REAL_TEST")=="1","optional isolated real runtime")
    def test_real_compiled_runtime(self):
        import openvino as runtime
        param=runtime.opset13.parameter([-1,3,-1,-1],runtime.Type.f32)
        graph=runtime.Model([runtime.opset13.relu(param)],[param])
        original=runtime.Core.compile_model
        with ov.explicit_fp32_cpu_compile():
            compiled=runtime.Core().compile_model(graph,"CPU",{"INFERENCE_PRECISION_HINT":runtime.Type.bf16})
            model=SimpleNamespace(predictor=SimpleNamespace(model=SimpleNamespace(ov_compiled_model=compiled)))
            self.assertEqual(ov.observed_properties(model),ov.PROPERTIES)
            self.assertEqual(ov.observed_input(model),ov.COMPILED_INPUT)
        self.assertIs(runtime.Core.compile_model,original)

    def test_method_mismatch(self):
        method={"id":ov.METHOD,"runtime":{"compiled_properties":ov.PROPERTIES}}
        plan={"schema_version":2,"method":method,"model_sha256":ov.CHECKPOINT,
              "model_provenance":"fixture","training_separation":"fixture","holdout_selection":"fixture",
              "criteria_rationale":"fixture only","confidence":.1,"iou_threshold":.5,
              "captures":{"capture.zip":ov.CHECKPOINT},"known_training_canonical_pixel_sha256":[ov.CHECKPOINT],
              "criteria":{k:{"min_truth":1,"min_precision":.5,"min_recall":.5} for k in ("vehicle","pedestrian")}}
        self.assertEqual(load_holdout(json.dumps(plan).encode(),["capture.zip"],ov.CHECKPOINT,.1,.5,method=method),plan)
        wrong=copy.deepcopy(method)
        wrong["runtime"]["compiled_properties"]["NUM_STREAMS"]="2"
        with self.assertRaises(ValueError):
            load_holdout(json.dumps(plan).encode(),["capture.zip"],ov.CHECKPOINT,.1,.5,method=wrong)
        with self.assertRaises(ValueError):
            evaluate([None],object(),capture_root="unused",holdout=plan,method=method)


if __name__=="__main__":
    unittest.main()
