"""Verify isolated seeded-network evidence without importing simulator services.

A matching archive digest establishes identity against an independently retained
trusted digest, not field validity or authenticity of a self-generated manifest.
No files are extracted, executed or modified.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
from statistics import mean
from zipfile import ZipFile

MODES = ("fixed", "adaptive", "cooperative")
FAIRNESS_MODES = (*MODES, "pedestrian_aware_cooperative")
METRICS = ("total_vehicle_wait_seconds", "total_pedestrian_wait_seconds",
           "total_vehicle_queue_average", "total_pedestrian_queue_average",
           "corridor_completed", "max_observed_pedestrian_wait_seconds")
PAIRS = (("adaptive", "fixed"), ("cooperative", "fixed"), ("cooperative", "adaptive"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def local_metrics(arm, node):
    m = arm["intersections"][node]["metrics"]
    p = m["waiting"]["pedestrian"]
    t = m["throughput"]
    signal = m["signal"]["phase_time_seconds"]
    net = arm["network_metrics"]
    return {"pedestrian_arrivals": t["external_pedestrian_arrivals"],
            "pedestrians_served": t["pedestrians_served"],
            "pedestrian_wait_count": p["count"], "pedestrian_wait_person_seconds": p["total_seconds"],
            "pedestrian_max_wait_seconds": p["max_seconds"], "pedestrian_p95_wait_seconds": p["p95_seconds"],
            "vehicle_wait_vehicle_seconds": m["waiting"]["vehicle"]["total_seconds"],
            "vehicle_green_seconds": signal.get("vehicle_green", 0),
            "pedestrian_green_seconds": signal.get("pedestrian_green", 0),
            "network_coordination_seconds_added": net["coordination"]["timing_seconds_added"],
            "network_pedestrian_awareness_applied": net["pedestrian_awareness"]["applied"]}


def verify_members(names, read):
    require(len(names) == len(set(names)), "Duplicate member names")
    require(all(Path(n).name == n and n not in (".", "..") and "\\" not in n for n in names), "Unexpected member path")
    def load(name):
        return json.loads(read(name))
    manifest = load("manifest.json")
    require(manifest["schema_version"] == 1 and manifest["evidence_class"] == "actually_executed_synthetic_queue_model"
            and manifest["physical_output_allowed"] is False, "Unqualified evidence classification")
    hashes = manifest["sha256"]
    require(set(names) == set(hashes) | {"manifest.json"} and "manifest.json" not in hashes, "Manifest member set differs")
    for name, digest in hashes.items():
        require(hashlib.sha256(read(name)).hexdigest() == digest, "Member digest mismatch: " + name)
    settings = manifest["settings"]
    densities, seeds = settings["densities"], settings["seeds"]
    cases = {(d, s) for d in densities for s in seeds}
    require(cases and len(cases) == len(densities) * len(seeds), "Duplicate or empty planned case")
    records = manifest["records"]
    require(len(records) == len(cases) and {(r["density"], r["seed"]) for r in records} == cases, "Case coverage differs")
    require(tuple(manifest["fairness_modes"]) == FAIRNESS_MODES, "Fairness modes differ")
    expected_primary, expected_fairness, originals = {}, {}, {}
    expected_files = {"paired-metrics.csv", "intersection-fairness.csv", "repeat.json"}
    nodes = {n["id"] for n in settings["network"]["intersections"]}
    for record in records:
        density, seed = record["density"], record["seed"]
        case = f"{density}-{seed}"
        expected_files.update((case + ".json", case + "-timeline.csv", case + "-decisions.csv"))
        raw = originals[density, seed] = load(case + ".json")
        scenario = raw["scenario"]
        require(raw["prototype_only"] is True and raw["run_id"] == record["run_id"] and scenario["density"] == density and scenario["seed"] == seed, "Run identity differs: " + case)
        for key in ("duration_seconds", "sample_interval_seconds", "transfer_share_percent"):
            require(scenario[key] == settings[key], "Setting differs: " + case + "/" + key)
        demand = scenario["arrival_plan"]["fingerprint_sha256"]
        require(demand == record["demand_sha256"], "Demand identity differs: " + case)
        for mode in FAIRNESS_MODES:
            arm = raw[mode]
            require(set(arm["intersections"]) == nodes, "Intersection coverage differs: " + case)
            metrics = {k: arm["network_metrics"][k] for k in METRICS}
            if mode in MODES:
                require(metrics == record["metrics"][mode], "Primary metrics differ: " + case)
                expected_primary[density, str(seed), demand, mode] = metrics
            else:
                require(metrics == record["pedestrian_aware_metrics"], "Secondary metrics differ: " + case)
                require({k: round(metrics[k] - record["metrics"]["cooperative"][k], 6) for k in METRICS} == record["pedestrian_aware_minus_cooperative"], "Secondary delta differs: " + case)
            for node in nodes:
                expected_fairness[density, str(seed), demand, mode, node] = local_metrics(arm, node)
        for candidate, baseline in PAIRS:
            delta = {k: round(record["metrics"][candidate][k] - record["metrics"][baseline][k], 6) for k in METRICS}
            require(delta == record["paired_deltas"][candidate + "_minus_" + baseline], "Paired delta differs: " + case)
    def verify_csv(name, identity, expected):
        table = csv.DictReader(io.StringIO(read(name).decode("utf-8")))
        require(set(table.fieldnames or ()) == set(identity) | set(next(iter(expected.values()))) and len(table.fieldnames or ()) == len(set(table.fieldnames or ())), "CSV columns differ: " + name)
        seen = set()
        for row in table:
            key = tuple(row[k] for k in identity)
            require(key in expected and key not in seen and None not in row, "Unknown or duplicate CSV identity: " + name)
            seen.add(key)
            for field, value in expected[key].items():
                require(float(row[field]) == value, "CSV metric differs: " + name + "/" + field)
        require(seen == set(expected), "CSV row coverage differs: " + name)
    common = ("density", "seed", "demand_sha256", "mode")
    verify_csv("paired-metrics.csv", common, expected_primary)
    verify_csv("intersection-fairness.csv", (*common, "intersection_id"), expected_fairness)
    def verify_repeat(name, original):
        repeat = load(name)
        require(repeat["prototype_only"] is True and repeat["scenario"] == original["scenario"], "Repeat scenario differs: " + name)
        for mode in FAIRNESS_MODES:
            require(repeat[mode]["network_metrics"] == original[mode]["network_metrics"], "Repeat network differs: " + name + "/" + mode)
            require({n: v["metrics"] for n, v in repeat[mode]["intersections"].items()} == {n: v["metrics"] for n, v in original[mode]["intersections"].items()}, "Repeat local metrics differ: " + name + "/" + mode)
    first = records[0]
    verify_repeat("repeat.json", originals[first["density"], first["seed"]])
    require(manifest["repeat_primary_metrics_and_demand_equal"] is True and manifest["repeat_intersection_fairness_equal"] is True, "First repeat flag differs")
    expected_busy = {s for d, s in cases if d == "busy"}
    repeats = manifest["busy_repeats"]
    require(len(repeats) == len(expected_busy) and {r["seed"] for r in repeats} == expected_busy, "Busy repeat coverage differs")
    for repeat in repeats:
        name = f"busy-{repeat['seed']}-repeat.json"
        require(repeat["file"] == name and repeat["primary_fairness_and_demand_equal"] is True, "Busy repeat declaration differs")
        expected_files.add(name)
        verify_repeat(name, originals["busy", repeat["seed"]])
    require(set(hashes) == expected_files, "Unexpected or missing evidence file")
    signs, summary = {}, {}
    for density in densities:
        group = [r for r in records if r["density"] == density]
        summary[density] = {}
        for candidate, baseline in PAIRS:
            pair = candidate + "_minus_" + baseline
            summary[density][pair] = {}
            for metric in METRICS:
                values = [r["paired_deltas"][pair][metric] for r in group]
                summary[density][pair][metric] = {"mean": mean(values), "min": min(values), "max": max(values), "n": len(values)}
        values = [r["paired_deltas"]["cooperative_minus_adaptive"]["total_pedestrian_wait_seconds"] for r in group]
        signs[density] = {"higher": sum(x > 0 for x in values), "lower": sum(x < 0 for x in values), "equal": sum(x == 0 for x in values)}
    require(summary == manifest["paired_summary_by_density"] and signs == manifest["cooperative_vs_adaptive_pedestrian_wait_signs"], "Paired aggregate differs")
    return {"verified_members": len(hashes), "matched_cases": len(cases), "primary_rows": len(expected_primary),
            "fairness_rows": len(expected_fairness), "busy_repeats": len(expected_busy),
            "pedestrian_wait_signs": signs, "evidence_class": manifest["evidence_class"],
            "scope": "Content consistency only; no field efficacy or migration acceptance."}


def verify(path, expected_sha256=None):
    if path.is_dir():
        require(expected_sha256 is None, "Archive digest requires a ZIP file")
        entries = list(path.iterdir())
        require(all(p.is_file() and not p.is_symlink() for p in entries), "Unexpected directory entry")
        return verify_members([p.name for p in entries], lambda n: (path / n).read_bytes())
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    require(expected_sha256 is None or digest == expected_sha256.lower(), "Archive digest mismatch")
    with ZipFile(path) as archive:
        result = verify_members(archive.namelist(), archive.read)
    return {**result, "archive_sha256": digest, "external_digest_checked": expected_sha256 is not None}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--sha256", help="Trusted independently retained ZIP digest")
    args = parser.parse_args()
    print(json.dumps(verify(args.evidence, args.sha256), indent=2, sort_keys=True))
