"""Shared offline tiled predictor; never registers a live model or observations."""
import hashlib
from importlib.metadata import version
from pathlib import Path
import platform
import sys

import cv2
import numpy as np
from app.services.sumo_projection import WIDTH, HEIGHT, VIEW_FLIPS
from app.services.camera_frames import CameraFrame
from app.services.inference import InferenceService

TILE = 192
STRIDE = 144
CONFIDENCE = .1
IOU = .5
INPUT_SIZE = 640
BATCH_SIZE = 8
METHOD = "tiled-stream-reuse-v1"


def starts(length):
    if length < TILE:
        raise ValueError("Tile larger than source")
    return sorted(set(range(0, length - TILE + 1, STRIDE)) | {length - TILE})


def windows():
    return [(x,y) for y in starts(HEIGHT) for x in starts(WIDTH)]


def clip_box(box, x, y):
    a,b,c,d = box
    clipped = [max(0,a-x), max(0,b-y), min(TILE,c-x), min(TILE,d-y)]
    return clipped if clipped[0]<clipped[2] and clipped[1]<clipped[3] else None


def intersection_over_union(a,b):
    overlap=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    return overlap / ((a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-overlap)


def merge(rows):
    # Deterministic confidence-ordered, same-kind NMS in source coordinates.
    # Retain raw tile predictions in the evidence alongside merged predictions.
    kept=[]
    for row in sorted(rows,key=lambda r:(-r["confidence"],r["tile_index"],r["id"])):
        if not any(row["kind"]==other["kind"] and intersection_over_union(row["box_xyxy"],other["box_xyxy"])>IOU for other in kept):
            kept.append(row)
    return kept


def predict_view(content, ann, view, model, *, batch_size=8):
    image=cv2.imdecode(np.frombuffer(content,np.uint8),cv2.IMREAD_COLOR)
    windows_xy=windows()
    crops=[image[y:y+TILE,x:x+TILE].copy() for x,y in windows_xy]
    raw_tiles=[]
    mapped=[]
    unmapped=[]
    # Bounded batches. Never publish crops or outputs to live inference.
    if not isinstance(batch_size, int) or not 1 <= batch_size <= len(crops):
        raise ValueError("Invalid offline tile batch size")
    for offset in range(0,len(crops),batch_size):
        batch=crops[offset:offset+batch_size]
        results=model.predict(source=batch,imgsz=INPUT_SIZE,conf=CONFIDENCE,
                              device="cpu",verbose=False,save=False)
        if len(results)!=len(batch):
            raise ValueError("Tile prediction cardinality mismatch")
        for j,result in enumerate(results):
            index=offset+j
            x,y=windows_xy[index]
            frame=CameraFrame(content=b"",content_type="image/png",
                source_id=f"offline_tile_{view}_{index}",width=TILE,height=TILE,
                received_at_ms=0,frame_number=ann["tick"],origin=ann["provenance"],
                coordinate_space="native_projection_v1",layout_id=ann["layout_id"])
            converted=InferenceService._convert_results(frame,[result],model)["detections"]
            raw_tiles.append({"tile_index":index,"origin_xy":[x,y],"local_predictions":converted})
            for row in converted:
                a,b,c,d=row["box_xyxy"]
                name=row["class_name"].strip().lower()
                kind=("pedestrian" if name in ("person","pedestrian") else
                      "vehicle" if name in ("vehicle","car","suv","van","bus","truck","motorcycle","motorbike") else None)
                full={**row,"tile_index":index,"box_xyxy":[a+x,b+y,c+x,d+y]}
                if kind is None:
                    unmapped.append(full)
                else:
                    mapped.append({**full,"kind":kind})
    return merge(mapped),unmapped,raw_tiles


class FrameDedupModel:
    """One frame only; exact byte equality, not similarity or stale tracking."""
    def __init__(self, model):
        self.model = model
        self.results = {}
        self.requested = self.evaluated = self.model_calls = 0

    def __getattr__(self, name):
        return getattr(self.model, name)

    def predict(self, *, source, **kwargs):
        keys = [(crop.shape, crop.dtype.str, crop.tobytes()) for crop in source]
        missing = {}
        for key, crop in zip(keys, source):
            if key not in self.results:
                missing.setdefault(key, crop)
        self.requested += len(keys)
        if missing:
            results = self.model.predict(source=list(missing.values()), **kwargs)
            if len(results) != len(missing):
                raise ValueError("Unique-tile prediction cardinality mismatch")
            self.results.update(zip(missing, results))
            self.evaluated += len(missing)
            self.model_calls += 1
        return [self.results[key] for key in keys]


def tiled_predict(content, ann, view, model):
    if (view not in VIEW_FLIPS or ann.get("coordinate_space") != "native_projection_v1"
            or ann.get("authoritative") is not False or ann.get("detector_input_eligible") is not False):
        raise ValueError("Invalid offline tiled evaluation identity")
    from app.services.observation_identity import EVALUATION_ORIGINS
    if ann.get("provenance") not in EVALUATION_ORIGINS:
        raise ValueError("Invalid offline tiled provenance")
    fresh = FrameDedupModel(model)
    predictions, unmapped, tiles = predict_view(content, ann, view, fresh, batch_size=BATCH_SIZE)
    expected = len(windows())
    if len(tiles) != expected or fresh.requested != expected or not 0 < fresh.evaluated <= expected:
        raise ValueError("Incomplete tiled evaluation coverage")
    return predictions, unmapped, {"tiles": tiles, "work": {
        "requested": fresh.requested, "evaluated": fresh.evaluated, "model_calls": fresh.model_calls}}


def method_descriptor():
    """Freeze actual implementation bytes and inference dependency versions."""
    root = Path(__file__).resolve().parents[1]
    files = ("scripts/native_detector_tiled.py", "scripts/native_detector_batch.py",
             "scripts/native_detector_holdout.py",
             "apps/pc-studio/backend/app/services/native_detector_validation.py",
             "apps/pc-studio/backend/app/services/inference.py",
             "apps/pc-studio/backend/app/services/camera_frames.py",
             "apps/pc-studio/backend/app/services/observation_identity.py",
             "apps/pc-studio/backend/app/services/sumo_projection.py")
    return {
        "id": METHOD, "tile_size": TILE, "stride": STRIDE, "input_size": INPUT_SIZE,
        "batch_size": BATCH_SIZE, "confidence": CONFIDENCE, "merge_iou": IOU,
        "score_iou": IOU, "device": "cpu", "cache_scope": "exact_shape_dtype_bytes_single_view",
        "coordinate_space": "native_projection_v1", "coverage": "end_aligned_full_frame",
        "class_mapping": "existing_offline_vehicle_pedestrian_v1",
        "python": platform.python_version(), "platform": sys.platform,
        "versions": {"ultralytics": version("ultralytics"), "torch": version("torch"),
                     "torchvision": version("torchvision"), "numpy": np.__version__, "opencv": cv2.__version__},
        "source_sha256": {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in files},
    }
