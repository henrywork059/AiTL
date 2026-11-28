"""Development-only tiled raster detector trial. No holdout access or live registration."""
import argparse
import csv
import json
from pathlib import Path
import shutil
from time import perf_counter

import cv2
import numpy as np

from native_detector_development_trial import (SETTINGS, MODEL_SHA, KINDS, WIDTH, HEIGHT,
    VIEW_FLIPS, materialize, inspect_capture, sha, write_json, file_sha256)
from native_detector_batch import summarize, latency_summary
from app.services.native_detector_validation import score_footprints
from app.services.camera_frames import CameraFrame
from app.services.inference import InferenceService

from native_detector_tiled import TILE, STRIDE, CONFIDENCE, IOU, starts, windows, clip_box, merge, predict_view
# Retain the same optimizer, six epochs and input resolution as full-frame trial.
# The development intervention is tiling plus pedestrian-containing tile sampling.
TILE_SETTINGS = {**SETTINGS, "batch": 8}


def make_dataset(captures, work, evidence):
    # Existing admission validates exact original archive/image identities and
    # rejects reserved/historical whole-view overlap before any crop is made.
    _, original=materialize(captures,work/"qualified-source")
    write_json(evidence/"source-dataset-manifest.json",original)
    tiles=work/"tiles"
    stats={s:{"images":0,"vehicle":0,"pedestrian":0,"skipped_exact_duplicate":0,
              "skipped_cross_split":0} for s in ("train","val")}
    seen={"train":{},"val":{}}
    manifest={}
    for split in ("train","val"):
        for folder in sorted((captures/split).rglob("capture.zip")):
            name=folder.relative_to(captures).as_posix()
            raw=folder.read_bytes()
            tick=int(folder.parent.name.rsplit("-",1)[1])
            ann,images,_=inspect_capture(raw,tick)
            for view in VIEW_FLIPS:
                image=cv2.imdecode(np.frombuffer(images[view],np.uint8),cv2.IMREAD_COLOR)
                candidates=[]
                for index,(x,y) in enumerate(windows()):
                    rows=[]
                    for row in ann["views"][view]:
                        box=clip_box(row["box_xyxy"],x,y)
                        if box is not None:
                            rows.append((row["kind"],box))
                    candidates.append((index,x,y,rows))
                # Include all pedestrian-containing tiles, plus one deterministic
                # vehicle-only tile and one empty tile where available. Never
                # select by model performance. Exhaustive evaluation uses all tiles.
                chosen=[r for r in candidates if any(k=="pedestrian" for k,b in r[3])]
                for predicate in (lambda r: bool(r[3]) and all(k=="vehicle" for k,b in r[3]),
                                  lambda r: not r[3]):
                    selected=next((r for r in candidates if predicate(r)),None)
                    if selected is not None:
                        chosen.append(selected)
                for index,x,y,rows in chosen:
                    crop=image[y:y+TILE,x:x+TILE]
                    pixel_sha=sha(crop.tobytes())
                    labels=[]
                    for kind,(a,b,c,d) in rows:
                        labels.append(f"{KINDS.index(kind)} {(a+c)/(2*TILE):.10f} {(b+d)/(2*TILE):.10f} {(c-a)/TILE:.10f} {(d-b)/TILE:.10f}")
                    label_bytes=("\n".join(sorted(labels))+("\n" if labels else "")).encode()
                    label_sha=sha(label_bytes)
                    if pixel_sha in seen[split]:
                        if seen[split][pixel_sha]!=label_sha:
                            raise ValueError("Identical crop has inconsistent labels")
                        stats[split]["skipped_exact_duplicate"]+=1
                        continue
                    if split=="val" and pixel_sha in seen["train"]:
                        if seen["train"][pixel_sha]!=label_sha:
                            raise ValueError("Cross-split identical crop has inconsistent labels")
                        stats[split]["skipped_cross_split"]+=1
                        continue
                    seen[split][pixel_sha]=label_sha
                    stem=f"{folder.parent.name}-{view}-{index}"
                    image_path=tiles/"images"/split/(stem+".png")
                    label_path=tiles/"labels"/split/(stem+".txt")
                    image_path.parent.mkdir(parents=True,exist_ok=True)
                    label_path.parent.mkdir(parents=True,exist_ok=True)
                    ok,encoded=cv2.imencode(".png",crop)
                    if not ok:
                        raise ValueError("Tile encode failed")
                    image_path.write_bytes(encoded.tobytes())
                    label_path.write_bytes(label_bytes)
                    stats[split]["images"]+=1
                    for kind,_ in rows:
                        stats[split][kind]+=1
                    manifest[image_path.relative_to(tiles).as_posix()]={"capture":name,"view":view,
                        "tile_index":index,"origin_xy":[x,y],"image_sha256":file_sha256(image_path),
                        "pixel_sha256":pixel_sha,"label_sha256":label_sha}
    if any(stats[s][k]==0 for s in stats for k in KINDS):
        raise ValueError("Both classes required in development tiles")
    yaml=tiles/"data.yaml"
    yaml.write_text("path: "+json.dumps(tiles.resolve().as_posix())+
                    "\ntrain: images/train\nval: images/val\nnames:\n  0: vehicle\n  1: pedestrian\n",
                    encoding="utf-8")
    write_json(evidence/"tile-manifest.json",{"tile_size":TILE,"stride":STRIDE,"images":manifest,
        "stats":stats,"formal_holdout_used":False})
    return yaml


def evaluate_tiles(captures,model,digest):
    records=[]
    for path in sorted((captures/"val").rglob("capture.zip")):
        name=path.relative_to(captures).as_posix()
        raw=path.read_bytes()
        ann,images,_=inspect_capture(raw,int(path.parent.name.rsplit("-",1)[1]))
        views={}
        for view in VIEW_FLIPS:
            t=perf_counter()
            predictions,unmapped,tiles=predict_view(images[view],ann,view,model)
            elapsed=(perf_counter()-t)*1000
            views[view]={"predictions":predictions,"unmapped_classes":unmapped,
                         "tiles":tiles,"prediction_latency_ms":elapsed,
                         "score":score_footprints(ann["views"][view],predictions,IOU)}
        records.append({"capture_name":name,"archive_sha256":sha(raw),"views":views})
    return {"model_sha256":digest,"method":"offline_tiled_development_yolo",
            "confidence":CONFIDENCE,"iou_threshold":IOU,"tile_size":TILE,"stride":STRIDE,
            "capture_count":len(records),"formal_holdout_used":False,
            "production_detector_validated":False,"physical_output_allowed":False,
            "views":{v:{"micro":summarize(r["views"][v]["score"] for r in records),
                        "latency":latency_summary([r["views"][v]["prediction_latency_ms"] for r in records])} for v in VIEW_FLIPS},
            "records":records}


def trial(captures,work,weights,evidence):
    if file_sha256(weights)!=MODEL_SHA:
        raise ValueError("Unexpected initialization checkpoint")
    work.mkdir(parents=True,exist_ok=False)
    evidence.mkdir(parents=True,exist_ok=False)
    yaml=make_dataset(captures,work,evidence)
    write_json(evidence/"plan.json",{"settings":TILE_SETTINGS,"tile_size":TILE,"stride":STRIDE,
        "confidence":CONFIDENCE,"iou_threshold":IOU,"initial_sha256":MODEL_SHA,
        "selection":"final epoch only","evaluation":"all tiles, all development validation views",
        "formal_holdout_used":False})
    from ultralytics import YOLO
    model=YOLO(str(weights))
    model.train(data=str(yaml),project=str(work/"runs"),name="tiles",**TILE_SETTINGS)
    run=Path(model.trainer.save_dir)
    with (run/"results.csv").open(newline="",encoding="utf-8") as stream:
        epochs=list(csv.DictReader(stream))
    if len(epochs)!=TILE_SETTINGS["epochs"]:
        raise ValueError("Incomplete fixed training schedule")
    for name in ("results.csv","args.yaml"):
        shutil.copyfile(run/name,evidence/name)
    checkpoint=evidence/"tile-development-last.pt"
    shutil.copyfile(run/"weights"/"last.pt",checkpoint)
    digest=file_sha256(checkpoint)
    result=evaluate_tiles(captures,YOLO(str(checkpoint)),digest)
    write_json(evidence/"tiled-validation.json",result)
    write_json(evidence/"summary.json",{"model_sha256":digest,"completed_epochs":len(epochs),
        "views":result["views"],"formal_holdout_used":False,"migration_authorized":False,
        "limitations":"Development only; correlated crops and full footprints. Tiling and sampling both changed. No real-world accuracy or live pipeline claim."})


def self_test():
    coverage=np.zeros((HEIGHT,WIDTH),np.uint8)
    for x,y in windows():
        coverage[y:y+TILE,x:x+TILE]+=1
    assert coverage.min()>=1 and len(windows())==45
    assert clip_box([190,190,195,195],0,0)==[190,190,192,192]
    assert clip_box([190,190,195,195],192,192)==[0,0,3,3]
    assert clip_box([0,0,3,3],192,0) is None
    a={"kind":"pedestrian","box_xyxy":[190,190,195,195],"confidence":.9,"tile_index":0,"id":"a"}
    b={**a,"confidence":.8,"tile_index":1,"id":"b"}
    c={**a,"kind":"vehicle","id":"c"}
    assert merge([b,c,a])==[a,c]
    assert merge([a,{**b,"box_xyxy":[0,0,5,5]}])==[a,{**b,"box_xyxy":[0,0,5,5]}]
    print("Tile coverage, clipping and original-coordinate same-kind NMS checks passed")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=("self-test","train"))
    p.add_argument("--captures",type=Path)
    p.add_argument("--work",type=Path)
    p.add_argument("--weights",type=Path)
    p.add_argument("--evidence",type=Path)
    a=p.parse_args()
    if a.mode=="self-test":
        self_test()
    else:
        trial(a.captures,a.work,a.weights,a.evidence)
