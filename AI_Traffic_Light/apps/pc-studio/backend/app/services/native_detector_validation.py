"""Offline raster-footprint qualification; no production inference or signal authority."""
from __future__ import annotations

import math
import cv2
import numpy as np
from app.services.sumo_projection import WIDTH, HEIGHT, VIEW_FLIPS, RASTER_PALETTE
from app.services.observation_identity import EVALUATION_ORIGINS


def footprint_annotations(scene):
    """Expected raster footprint boxes, half-open XYXY like live detections.

    Reconstruct the actual renderer's integer geometry before mirroring.
    Boxes describe full clipped footprints, not visible-only segmentation;
    overlapping objects may merge or occlude in the raster.
    """
    if (scene.get("provenance") not in EVALUATION_ORIGINS or
        scene.get("coordinate_space")!="native_projection_v1" or
        (scene.get("width"),scene.get("height"))!=(WIDTH,HEIGHT)):
        raise ValueError("Unqualified synthetic scene")
    scale=scene["pixels_per_m"]
    if not math.isfinite(scale) or scale<=0:
        raise ValueError("Invalid projection scale")
    canonical=[]
    for a in scene["agents"]:
        x,y=a["x"],a["y"]
        if a["kind"] not in ("vehicle","pedestrian") or not all(math.isfinite(v) for v in (x,y)):
            raise ValueError("Invalid synthetic agent")
        if "length_m" in a:
            tail=x+(-1 if a["eastbound"] else 1)*a["length_m"]*scale
            half=a["width_m"]*scale/2
            l,r=sorted((round(x),round(tail)))
            t,b=round(y-half),round(y+half)
        else:
            radius=max(1,round(.25*scale)) if "slot_id" in a else (4 if a["kind"]=="vehicle" else 3)
            l,r=round(x)-radius,round(x)+radius
            t,b=round(y)-radius,round(y)+radius
        box=[max(0,l),max(0,t),min(WIDTH,r+1),min(HEIGHT,b+1)]
        if box[0]<box[2] and box[1]<box[3]:
            canonical.append({"agent_id":a["id"],"kind":a["kind"],"box_xyxy":box})
    if len({a["agent_id"] for a in canonical})!=len(canonical):
        raise ValueError("Duplicate synthetic footprint identity")
    views={}
    for sid,flip in VIEW_FLIPS.items():
        rows=[]
        for a in canonical:
            x1,y1,x2,y2=a["box_xyxy"]
            if flip in (1,-1): x1,x2=WIDTH-x2,WIDTH-x1
            if flip in (0,-1): y1,y2=HEIGHT-y2,HEIGHT-y1
            rows.append({**a,"box_xyxy":[x1,y1,x2,y2]})
        views[sid]=rows
    return {"schema_version":1,"epoch":scene.get("epoch"),"generation":scene["generation"],"tick":scene["tick"],
            "layout_id":scene["layout_id"],"coordinate_space":"native_projection_v1","provenance":scene["provenance"],
            "width":WIDTH,"height":HEIGHT,"box_contract":"clipped_full_raster_footprint_half_open_xyxy_v1",
            "authoritative":False,"detector_input_eligible":False,"views":views}


def palette_predictions(content):
    """Executed colour connected-component baseline, NOT a trained model."""
    image=cv2.imdecode(np.frombuffer(content,np.uint8),cv2.IMREAD_COLOR)
    if image is None or image.shape!=(HEIGHT,WIDTH,3):
        raise ValueError("Invalid evaluation image")
    rows=[]
    for kind,indices in (("vehicle",(4,5)),("pedestrian",(6,))):
        mask=np.zeros((HEIGHT,WIDTH),np.uint8)
        for i in indices:
            colour=RASTER_PALETTE[i]
            mask=cv2.bitwise_or(mask,cv2.inRange(image,colour,colour))
        count,_,stats,_=cv2.connectedComponentsWithStats(mask,connectivity=8)
        for x,y,w,h,area in stats[1:count]:
            rows.append({"kind":kind,"box_xyxy":[int(x),int(y),int(x+w),int(y+h)],"confidence":1.0})
    return rows


def score_footprints(truth,predictions,threshold=.5):
    """Deterministic one-to-one same-kind greedy IoU matching, no mAP claim."""
    if not 0<threshold<=1:
        raise ValueError("Invalid IoU threshold")
    def checked(row):
        box=row["box_xyxy"]
        if (row["kind"] not in ("vehicle","pedestrian") or len(box)!=4 or
            not all(type(v) in (int,float) and math.isfinite(v) for v in box) or
            not (0<=box[0]<box[2]<=WIDTH and 0<=box[1]<box[3]<=HEIGHT)):
            raise ValueError("Invalid evaluation box")
        return box
    tb=[checked(x) for x in truth]
    pb=[checked(x) for x in predictions]
    def iou(a,b):
        overlap=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
        union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-overlap
        return overlap/union
    candidates=sorted((-iou(a,b),i,j) for i,a in enumerate(tb) for j,b in enumerate(pb)
                      if truth[i]["kind"]==predictions[j]["kind"])
    used_t,used_p=set(),set()
    matches=[]
    for negative,i,j in candidates:
        if -negative<threshold: break
        if i not in used_t and j not in used_p:
            used_t.add(i);used_p.add(j)
            matches.append({"agent_id":truth[i]["agent_id"],"prediction_index":j,"iou":round(-negative,6)})
    return {"iou_threshold":threshold,"truth_count":len(tb),"prediction_count":len(pb),
            "matched":len(matches),"unmatched_truth":len(tb)-len(matches),
            "unmatched_predictions":len(pb)-len(matches),"matches":matches,
            "production_detector_validated":False}


def model_predictions(content,annotations,view_id,model,confidence_threshold=.1):
    """Run an explicitly supplied offline model using the production box converter.

    Never load/register a live model or publish detections into camera, tracking,
    regions or control. Unmapped classes are reported separately.
    """
    from app.services.camera_frames import CameraFrame
    from app.services.inference import InferenceService
    from app.services.observation_identity import evaluation_source_id
    if (view_id not in VIEW_FLIPS or not 0<confidence_threshold<=1 or
        annotations.get("coordinate_space")!="native_projection_v1" or annotations.get("provenance") not in EVALUATION_ORIGINS or
        annotations.get("detector_input_eligible") is not False or annotations.get("authoritative") is not False):
        raise ValueError("Invalid offline detector evaluation identity")
    image=cv2.imdecode(np.frombuffer(content,np.uint8),cv2.IMREAD_COLOR)
    if image is None or image.shape!=(HEIGHT,WIDTH,3):
        raise ValueError("Invalid offline detector image")
    generation=annotations["generation"]
    origin=annotations["provenance"]
    frame=CameraFrame(content=content,content_type="image/png",
        source_id=evaluation_source_id(origin,generation,view_id),
        width=WIDTH,height=HEIGHT,received_at_ms=0,frame_number=annotations["tick"],
        origin=origin,mode_generation=generation,
        coordinate_space="native_projection_v1",layout_id=annotations["layout_id"],
        observation_epoch=annotations.get("epoch"))
    results=model.predict(source=image,conf=confidence_threshold,verbose=False,device="cpu",save=False)
    converted=InferenceService._convert_results(frame,results,model)
    mapped=[]
    unmapped=[]
    for row in converted["detections"]:
        name=row["class_name"].strip().lower()
        kind=("pedestrian" if name in {"person","pedestrian"} else
              "vehicle" if name in {"vehicle","car","suv","van","bus","truck","motorcycle","motorbike"} else None)
        if kind is None:
            unmapped.append(row)
        else:
            mapped.append({**row,"kind":kind})
    return mapped,unmapped


def qualified_capture(archive):
    """Qualify a retained capture before offline inference; never authenticate it.

    Existing captures without a hash manifest are supported if all provenance,
    observation, annotation and pixel-mirror checks succeed.
    """
    import hashlib
    import json
    from app.services.observation_identity import evaluation_source_id
    names=archive.namelist()
    if len(names)!=len(set(names)):
        raise ValueError("Duplicate capture member")
    def read(name):
        info=archive.getinfo(name)
        if info.file_size>8*1024*1024:
            raise ValueError("Capture member too large")
        return archive.read(info)
    scene_bytes=read("scene.json")
    scene=json.loads(scene_bytes)
    annotations=footprint_annotations(scene)
    if "synthetic_footprints.json" in names and json.loads(read("synthetic_footprints.json"))!=annotations:
        raise ValueError("Retained annotation differs from scene reconstruction")
    coordinate=json.loads(read("coordinate_contract.json"))
    identity={k:scene[k] for k in ("epoch","generation","tick","layout_id","coordinate_space","provenance","width","height","engine")}
    if any(coordinate.get(k)!=v for k,v in identity.items()) or coordinate.get("views")!=list(VIEW_FLIPS) or coordinate.get("legacy_editor_compatible") is not False:
        raise ValueError("Capture coordinate identity mismatch")
    observations=json.loads(read("observations.json"))
    detector=json.loads(read("detector_contract.json"))
    flags=("detector_input_eligible","detector_observation","authoritative","physical_output_allowed")
    if (detector.get("observations")!=observations or detector.get("layout_id")!=identity["layout_id"] or
        detector.get("coordinate_space")!=identity["coordinate_space"] or any(detector.get(k) is not False for k in flags)):
        raise ValueError("Capture detector contract mismatch")
    by_view={row["view_id"]:row for row in observations}
    if len(observations)!=len(VIEW_FLIPS) or set(by_view)!=set(VIEW_FLIPS):
        raise ValueError("Capture view identity mismatch")
    images={}
    hashes={"scene.json":hashlib.sha256(scene_bytes).hexdigest()}
    canonical=None
    for sid,flip in VIEW_FLIPS.items():
        obs=by_view[sid]
        if (any(obs.get(k)!=identity[k] for k in identity if k!="engine") or
            any(obs.get(k) is not False for k in flags) or obs.get("frame_number")!=identity["tick"] or
            obs.get("received_at_ms")!=scene["received_at_ms"] or
            obs.get("source_id")!=evaluation_source_id(identity["provenance"],identity["generation"],sid)):
            raise ValueError("Capture observation mismatch")
        metadata=json.loads(read(sid+".json"))
        expected={"observation_epoch":identity["epoch"],"layout_id":identity["layout_id"],
                  "coordinate_space":identity["coordinate_space"],"source_frame_number":identity["tick"],
                  "source_id":obs["source_id"],"source_received_at_ms":obs["received_at_ms"],
                  "origin":identity["provenance"],"width":WIDTH,"height":HEIGHT,
                  "content_type":"image/png","detector_input_eligible":False}
        content=read(sid+".png")
        expected["size_bytes"]=len(content)
        if any(metadata.get(k)!=v for k,v in expected.items()):
            raise ValueError("Capture frame metadata mismatch")
        image=cv2.imdecode(np.frombuffer(content,np.uint8),cv2.IMREAD_COLOR)
        if not content.startswith(b"\x89PNG\r\n\x1a\n") or image is None or image.shape!=(HEIGHT,WIDTH,3):
            raise ValueError("Capture PNG mismatch")
        if flip is None: canonical=image
        elif not np.array_equal(image,cv2.flip(canonical,flip)):
            raise ValueError("Capture view is not an exact mirror")
        images[sid]=content
        hashes[sid+".png"]=hashlib.sha256(content).hexdigest()
    manifest_present="capture_integrity.json" in names
    if manifest_present and json.loads(read("capture_integrity.json"))!={"schema_version":1,"sha256":hashes}:
        raise ValueError("Capture integrity hash mismatch")
    return annotations,images,{"hash_manifest_verified":manifest_present,"sha256":hashes,
                              "capture_authenticated":False}
