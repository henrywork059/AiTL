"""Read-only audit of S04 retained synthetic evidence, independent of simulator code."""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from statistics import mean
from zipfile import ZipFile

VIEWS = ("simulation_camera", "simulation_camera_b", "simulation_camera_c", "simulation_camera_d")
COUNTS = ("vehicle_queue", "pedestrian_queue", "vehicle_passages", "pedestrian_crossings")
FLAGS = ("detector_input_eligible", "detector_observation", "authoritative", "physical_output_allowed")


def check(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(read, name):
    return json.loads(read(name))


def verify_metric_rows(rows, run, step, horizon):
    """Use Decimal-like rounded sample times and integer queue counts, not wait claims."""
    check(rows and len(rows) == round(horizon / step), "Metric sample count")
    for i, row in enumerate(rows, 1):
        check(row["tick"] == i and math.isclose(row["t_seconds"], i * step, abs_tol=1e-8), "Metric clock")
        check(all(type(row[key]) is int and row[key] >= 0 for key in COUNTS), "Metric negative/fractional count")
        if i > 1:
            check(all(row[key] >= rows[i-2][key] for key in COUNTS[2:]), "Metric passage count reversed")
    summary = run["summary"]
    check(summary["samples"] == len(rows), "Metric summary sample count")
    for kind, passage in (("vehicle", "vehicle_passages"), ("pedestrian", "pedestrian_crossings")):
        queue = kind + "_queue"
        check(summary[passage] == rows[-1][passage], "Metric passage total")
        check(summary["peak_" + queue] == max(row[queue] for row in rows), "Metric peak queue")
        check(math.isclose(summary[kind + "_wait_agent_s"], sum(row[queue] for row in rows) * step, abs_tol=1e-8), "Metric queue integral")
    check(digest(json.dumps(rows, sort_keys=True).encode()) == run["digest"], "Metric raw timeline digest")
    return len(rows)


def csv_rows(read, name):
    return [{k: float(v) if k == "t_seconds" else v if k == "requested_phase" else int(v)
             for k, v in row.items()} for row in csv.DictReader(io.StringIO(read(name).decode("utf-8")))]


def audit_metrics(read):
    total = 0
    pairs = {}
    for group, engines in (("mesh-sumo-gate-metrics", ("legacy", "native")),
                           ("mesh-sumo-finite-fixture", ("native", "finite_reference"))):
        result = load(read, group + "/result.json")
        check(result["replacement_parity"] is False and result["default_migration_allowed"] is False, "Metric migration authority")
        check(len(result["runs"]) == 4, "Metric repeat count")
        for engine in engines:
            runs = [r for r in result["runs"] if r["engine"] == engine]
            check(len(runs) == 2, "Metric engine repeat count")
            for repeat, run in enumerate(runs):
                rows = csv_rows(read, f"{group}/{engine}-{repeat}.csv")
                total += verify_metric_rows(rows, run, result["step_s"], result["horizon_s"])
                if group.endswith("finite-fixture"):
                    check(load(read, f"{group}/{engine}-{repeat}-summary.json") == run, "Finite summary differs")
                    check(run["completion_ok"] and not run["route_mismatches"] and not run["unsupported_routes"] and not run["unknown_roads"], "Finite route qualification")
                else:
                    index = engines.index(engine)
                    raw = load(read, f"{group}/arm-{index}-{repeat}.json")
                    check(raw["timeline"] == rows and all(raw[k] == run[k] for k in run), "Metric raw JSON differs")
            check(runs[0]["digest"] == runs[1]["digest"], "Metric deterministic repeat differs")
            pairs[group + "/" + engine] = runs[0]["summary"]
    return total, pairs


def percentile95(values):
    ordered = sorted(values)
    position = .95 * (len(ordered) - 1)
    low = math.floor(position)
    return ordered[low] + (ordered[math.ceil(position)] - ordered[low]) * (position - low)


def audit_resources(read):
    root = "mesh-sumo-midblock/"
    encoding = load(read, root + "indexed-rgb-comparison.json")
    transport = load(read, root + "worker-memory-comparison.json")
    check(encoding["pixel_equivalent"] is True and transport["pixel_equivalent"] is True and encoding["indexed"] == transport["lean"], "Resource arm identity")
    groups = (("indexed_lean", encoding["indexed"], ("42-normal-fixed", "42-normal-fixed-repeat"), True, "lean_stdio"),
              ("rgb_lean", encoding["rgb"], ("42-normal-fixed-rgb-0", "42-normal-fixed-rgb-1"), False, "lean_stdio"),
              ("indexed_spawn", transport["spawn"], ("42-normal-fixed-spawn-0", "42-normal-fixed-spawn-1"), True, "spawn"))
    output, pixels = {}, set()
    for key, records, paths, indexed, worker in groups:
        check(len(records) == len(paths), "Resource repeat count")
        pooled = []
        for record, path in zip(records, paths):
            check(record["indexed_frames"] is indexed and record["worker_transport"] == worker and record["simulated_seconds"] == 40, "Resource arm settings")
            samples = load(read, root + path + "/latency-samples.json")
            for channel, count_key in (("scene_ms", "scene_reads"), ("frame_ms", "frame_reads")):
                values = samples[channel]
                stats = record["latency_ms"][channel]
                check(len(values) == record[count_key] == stats["count"] == 400 and all(math.isfinite(x) and x >= 0 for x in values), "Resource sample count")
                check(math.isclose(mean(values), stats["mean"], abs_tol=1e-8) and math.isclose(percentile95(values), stats["p95"], abs_tol=1e-8), "Resource latency statistic")
            pooled += samples["frame_ms"]
            before, after = record["before"], record["after"]
            check(set(before) == set(after) == {record["parent_pid"], record["child_pid"]}, "Resource process identity")
            check(sum(v["working_set_bytes"] for v in after.values()) == record["end_combined_working_set_bytes"], "Resource working-set sum")
            check(math.isclose(sum(after[k]["cpu_s"] - before[k]["cpu_s"] for k in before), record["cpu_delta_s"], abs_tol=1e-8), "Resource CPU delta")
            pixels.add(record["decoded_pixel_digest"])
        output[key] = {"frame_samples": len(pooled), "mean_ms": mean(pooled), "p95_ms_linear": percentile95(pooled),
                       "mean_final_combined_working_set_bytes": mean(r["end_combined_working_set_bytes"] for r in records)}
    check(len(pixels) == 1, "Resource decoded-pixel digest differs")
    return output


def audit_captures(read):
    report = load(read, "mesh-native-detector-batch.json")
    check(report["method"] == "exact_palette_components_not_trained_model" and report["model_sha256"] is None
          and report["production_detector_validated"] is False and report["physical_output_allowed"] is False, "Detector evidence authority")
    identities, views = set(), 0
    check(report["capture_count"] == len(report["records"]) > 0, "Detector capture count")
    for record in report["records"]:
        name = record["capture_name"]
        check(not Path(name).is_absolute() and ".." not in Path(name).parts and "\\" not in name, "Unsafe capture path")
        content = read("mesh-sumo-midblock/" + name)
        check(digest(content) == record["archive_sha256"], "Capture archive digest")
        with ZipFile(io.BytesIO(content)) as archive:
            check(len(archive.namelist()) == len(set(archive.namelist())), "Duplicate capture member")
            scene = load(archive.read, "scene.json")
            coordinate = load(archive.read, "coordinate_contract.json")
            detector = load(archive.read, "detector_contract.json")
            observations = load(archive.read, "observations.json")
            identity = tuple(scene[k] for k in ("epoch", "generation", "tick", "layout_id"))
            check(list(identity) == record["identity"] and identity not in identities, "Capture identity")
            identities.add(identity)
            check(all(coordinate[k] == scene[k] for k in ("epoch", "generation", "tick", "layout_id", "coordinate_space", "width", "height", "provenance"))
                  and coordinate["coordinate_space"] == "native_projection_v1" and coordinate["legacy_editor_compatible"] is False, "Capture coordinate provenance")
            check(detector["observations"] == observations and all(detector[k] is False for k in FLAGS), "Capture detector authority")
            hashes = load(archive.read, "capture_integrity.json")["sha256"]
            check(set(hashes) == {"scene.json", *(sid + ".png" for sid in VIEWS)} and hashes == record["integrity"]["sha256"], "Capture member manifest")
            check(all(digest(archive.read(member)) == expected for member, expected in hashes.items()), "Capture member digest")
            truth = load(archive.read, "synthetic_footprints.json")["views"]
            check(set(truth) == set(record["views"]) == set(VIEWS), "Capture view coverage")
            base = {a["agent_id"]: a for a in truth[VIEWS[0]]}
            for index, sid in enumerate(VIEWS):
                obs = observations[index]
                meta = load(archive.read, sid + ".json")
                check(obs["view_id"] == sid and all(obs[k] is False for k in FLAGS) and meta["detector_input_eligible"] is False, "Capture view authority")
                check(all(obs[k] == scene[k] for k in ("epoch", "generation", "tick", "layout_id", "coordinate_space", "width", "height", "provenance"))
                      and meta["source_id"] == obs["source_id"] and meta["source_frame_number"] == scene["tick"], "Capture view identity")
                check(meta.get("content_sha256", hashes[sid + ".png"]) == hashes[sid + ".png"], "Capture content digest")
                check(len(truth[sid]) == len(base) and {a["agent_id"] for a in truth[sid]} == set(base), "Capture mirrored truth IDs")
                for item in truth[sid]:
                    x1, y1, x2, y2 = base[item["agent_id"]]["box_xyxy"]
                    w, h = scene["width"], scene["height"]
                    if index in (2, 3): x1, x2 = w-x2, w-x1
                    if index in (1, 3): y1, y2 = h-y2, h-y1
                    check(item["box_xyxy"] == [x1, y1, x2, y2], "Capture mirrored half-open coordinates")
                views += 1
    return len(identities), views


def audit(read):
    samples, metrics = audit_metrics(read)
    captures, views = audit_captures(read)
    return {"normalized_samples": samples, "metrics": metrics, "resource_arms": audit_resources(read),
            "capture_count": captures, "coordinate_views": views, "migration_allowed": False,
            "limitations": "Synthetic evidence consistency only; no calibrated production coordinates, trained holdout, owner resource budget or migration acceptance."}


def tamper_checks(read):
    cases = ((audit_metrics, "mesh-sumo-gate-metrics/result.json", lambda d: d["runs"][0]["summary"].__setitem__("vehicle_wait_agent_s", -1), "Metric queue integral"),
             (audit_resources, "mesh-sumo-midblock/indexed-rgb-comparison.json", lambda d: d["rgb"][0]["latency_ms"]["frame_ms"].__setitem__("mean", -1), "Resource latency statistic"),
             (audit_captures, "mesh-native-detector-batch.json", lambda d: d["records"][0].__setitem__("archive_sha256", "0" * 64), "Capture archive digest"))
    for function, name, alter, expected in cases:
        changed = load(read, name)
        alter(changed)
        def modified(member):
            return json.dumps(changed).encode() if member == name else read(member)
        try:
            function(modified)
        except ValueError as exc:
            check(expected in str(exc), "Unexpected tamper rejection: " + str(exc))
        else:
            raise ValueError("Tampered evidence accepted: " + name)
    return len(cases)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Retained evidence directory or ZIP")
    parser.add_argument("--sha256", help="Independently retained expected archive SHA-256")
    parser.add_argument("--tamper-check", action="store_true", help="Run non-mutating negative controls on retained evidence")
    args = parser.parse_args()
    if args.input.is_dir():
        check(not args.sha256, "Archive digest requires ZIP input")
        read = lambda name: (args.input / name).read_bytes()
        result = audit(read)
        if args.tamper_check:
            result["tamper_rejections"] = tamper_checks(read)
    else:
        if args.sha256:
            check(digest(args.input.read_bytes()) == args.sha256, "Outer archive digest")
        with ZipFile(args.input) as archive:
            check(len(archive.namelist()) == len(set(archive.namelist())), "Duplicate evidence member")
            result = audit(archive.read)
            if args.tamper_check:
                result["tamper_rejections"] = tamper_checks(archive.read)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
