"""Matched inference-only resolution profiles for Update 28C; never uses holdout."""
import argparse
from pathlib import Path

from native_detector_tile_trial import evaluate_tiles, self_test as tile_self_test
from native_detector_development_trial import file_sha256, write_json

MODEL_DIGEST = "9c888355e3228db090c98969672a4418eb207e1c0ffa926746091485da84ecba"
PROFILES = (640, 416, 320, 256)


class ResolutionModel:
    """Keep original converter and tiling path; change only inference imgsz."""
    def __init__(self, model, size):
        if size not in PROFILES:
            raise ValueError("Unplanned development resolution")
        self.model = model
        self.size = size

    def predict(self, **kwargs):
        return self.model.predict(**{**kwargs, "imgsz": self.size})

    def __getattr__(self, name):
        return getattr(self.model, name)


def self_test():
    tile_self_test()

    class Fake:
        names = {0: "vehicle", 1: "pedestrian"}

        def predict(self, **kwargs):
            return kwargs

    for size in PROFILES:
        adapter = ResolutionModel(Fake(), size)
        assert adapter.names == Fake.names
        assert adapter.predict(source="test", imgsz=640, conf=.1, device="cpu") == {
            "source": "test", "imgsz": size, "conf": .1, "device": "cpu"}
    try:
        ResolutionModel(Fake(), 999)
    except ValueError:
        pass
    else:
        raise AssertionError("Unplanned size admitted")
    print("Resolution adapter and original tile invariants passed")


def sweep(captures, weights, evidence):
    if file_sha256(weights) != MODEL_DIGEST:
        raise ValueError("Unexpected development checkpoint")
    evidence.mkdir(parents=True, exist_ok=False)
    write_json(evidence / "plan.json", {
        "model_sha256": MODEL_DIGEST, "profiles": list(PROFILES),
        "capture_artifact_id": 15245454146, "checkpoint_artifact_id": 15247571354,
        "tile_size": 192, "stride": 144, "confidence": .1, "iou_threshold": .5,
        "evaluation": "every tile in every development-validation view",
        "formal_holdout_used": False, "migration_authorized": False})
    from ultralytics import YOLO
    summaries = {}
    identities = None
    for size in PROFILES:
        model = ResolutionModel(YOLO(str(weights)), size)
        report = evaluate_tiles(captures, model, MODEL_DIGEST)
        report["inference_imgsz"] = size
        current = [(r["capture_name"], r["archive_sha256"], list(r["views"])) for r in report["records"]]
        if identities is None:
            identities = current
        elif current != identities:
            raise ValueError("Unmatched evaluation cohort")
        if report["capture_count"] != 16 or any(len(r["views"]) != 4 for r in report["records"]):
            raise ValueError("Incomplete development cohort")
        write_json(evidence / f"resolution-{size}.json", report)
        summaries[str(size)] = report["views"]
        del model
    write_json(evidence / "summary.json", {
        "model_sha256": MODEL_DIGEST, "profiles": summaries,
        "formal_holdout_used": False, "migration_authorized": False,
        "limitations": "Fixed-order isolated CPU development comparison; correlated views; no acceptance thresholds or automatic selection."})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("self-test", "sweep"))
    parser.add_argument("--captures", type=Path)
    parser.add_argument("--weights", type=Path)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    if args.mode == "self-test":
        self_test()
    else:
        if not all((args.captures, args.weights, args.evidence)):
            parser.error("sweep requires --captures, --weights and --evidence")
        sweep(args.captures, args.weights, args.evidence)
