"""Score one retained native capture offline, never a live inference service."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
from zipfile import ZipFile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"apps/pc-studio/backend"))
from app.services.native_detector_validation import footprint_annotations,palette_predictions,model_predictions,score_footprints
from app.services.sumo_projection import VIEW_FLIPS


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture",type=Path,required=True)
    parser.add_argument("--model",type=Path,help="Explicit trusted local .pt weights; no default model download")
    parser.add_argument("--confidence",type=float,default=.1)
    args=parser.parse_args()
    if not 0<args.confidence<=1: parser.error("confidence must be in (0,1]")
    model=None
    model_digest=None
    if args.model is not None:
        path=args.model.expanduser().resolve()
        if not path.is_file() or path.suffix.lower()!=".pt":
            parser.error("provide existing trusted local .pt weights")
        with path.open("rb") as f:
            digest=hashlib.sha256()
            for block in iter(lambda:f.read(1048576),b""): digest.update(block)
        model_digest=digest.hexdigest()
        from ultralytics import YOLO
        model=YOLO(str(path))
    with ZipFile(args.capture) as archive:
        scene=json.loads(archive.read("scene.json"))
        ann=footprint_annotations(scene)
        if "synthetic_footprints.json" in archive.namelist() and json.loads(archive.read("synthetic_footprints.json"))!=ann:
            raise ValueError("Retained annotation differs from scene reconstruction")
        views={}
        for sid in VIEW_FLIPS:
            image=archive.read(sid+".png")
            unmapped=[]
            if model is None:
                predictions=palette_predictions(image)
            else:
                predictions,unmapped=model_predictions(image,ann,sid,model,args.confidence)
            views[sid]={"score":score_footprints(ann["views"][sid],predictions),
                        "predictions":predictions,"unmapped_classes":unmapped}
    print(json.dumps({"method":"offline_local_yolo" if model is not None else "exact_palette_components_not_trained_model",
        "model_sha256":model_digest,"confidence":args.confidence if model is not None else None,
        "layout_id":ann["layout_id"],"generation":ann["generation"],"tick":ann["tick"],
        "production_detector_validated":False,"physical_output_allowed":False,
        "limitations":"One synthetic capture, four correlated mirrors, full raster footprints, greedy IoU matching; not field accuracy or mAP.",
        "views":views},indent=2))


if __name__=="__main__":
    main()
