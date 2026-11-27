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



def verify_trace_exports(case, raw, read):
    """Reconcile selected raw timeline and every normalized decision row, not just hashes."""
    timeline_name = case + "-timeline.csv"
    table = csv.DictReader(io.StringIO(read(timeline_name).decode("utf-8")))
    rows = list(table)
    modes = ("fixed", "adaptive", "cooperative", "pedestrian_aware_cooperative")
    require(len(rows) == len(raw["fixed"]["timeline"]), "Timeline sample count differs: " + case)
    for mode in modes:
        require(len(raw[mode]["timeline"]) == len(rows), "Mode timeline count differs: " + case + "/" + mode)
    for index, row in enumerate(rows):
        for mode in modes:
            sample = raw[mode]["timeline"][index]
            require(float(row["t_seconds"]) == sample["t"], "Timeline timestamp differs: " + case + "/" + mode)
            for location in ("source", "destination"):
                location_sample = sample[location]
                prefix = mode + "_" + location + "_"
                require(row[prefix + "phase"] == location_sample["phase"], "Timeline phase differs: " + case + "/" + mode)
                for metric in ("vehicle_queue", "pedestrian_queue", "vehicles_served"):
                    require(float(row[prefix + metric]) == location_sample[metric], "Timeline queue/throughput differs: " + case + "/" + mode + "/" + metric)
            for metric in ("pipeline_count", "transfers_departed", "transfers_arrived", "corridor_completed"):
                require(float(row[mode + "_" + metric]) == sample[metric], "Timeline transfer differs: " + case + "/" + mode + "/" + metric)
    decision_name = case + "-decisions.csv"
    decisions = list(csv.DictReader(io.StringIO(read(decision_name).decode("utf-8"))))
    evidence = raw["decision_evidence"]
    require(evidence["prototype_only"] is True and len(decisions) == evidence["record_count"] == len(evidence["records"]), "Decision count differs: " + case)
    require(len({item["evidence_id"] for item in evidence["records"]}) == len(decisions), "Duplicate decision evidence IDs: " + case)
    for row, item in zip(decisions, evidence["records"]):
        for field in ("evidence_id", "mode", "trigger_category", "trigger_id", "intersection_id", "source_intersection_id", "destination_intersection_id", "link_id", "decision", "action", "phase_before", "phase_key_before", "provenance", "reason", "explanation", "source_ref"):
            require(row[field] == str(item.get(field) or ""), "Decision identity/value differs: " + case + "/" + field)
        require(float(row["t_seconds"]) == item["t_seconds"] and row["applied"] == str(item["applied"]), "Decision time/applied differs: " + case)
        for column, key in (("timing_delta_seconds", "delta_seconds"), ("previous_duration_seconds", "previous_duration_seconds"), ("effective_duration_seconds", "effective_duration_seconds")):
            value = item.get("timing", {}).get(key)
            require(row[column] == ("" if value is None else str(value)), "Decision timing differs: " + case + "/" + column)
    return len(rows), len(decisions)


def verify_conservation(case, raw):
    """Check raw run identities independently of copied summary/CSV values."""
    duration = raw["scenario"]["duration_seconds"]
    checked = 0
    for mode in FAIRNESS_MODES:
        arm = raw[mode]
        timeline = arm["timeline"]
        require(timeline and timeline[-1]["t"] == duration, "Conservation horizon differs: " + case)
        final = timeline[-1]
        network = arm["network_metrics"]
        previous = None
        for sample in timeline:
            for role in ("source", "destination"):
                for key in ("vehicle_queue", "pedestrian_queue", "vehicles_served"):
                    value = sample[role][key]
                    require(type(value) is int and value >= 0, "Conservation negative or fractional count: " + case)
            require(sample["transfers_departed"] - sample["transfers_arrived"] == sample["pipeline_count"]
                    and sample["transfers_departed"] >= sample["transfers_arrived"] >= sample["corridor_completed"] >= 0,
                    "Conservation transfer pipeline differs: " + case + "/" + mode)
            if previous is not None:
                require(sample["t"] > previous["t"] and all(sample[k] >= previous[k]
                        for k in ("transfers_departed", "transfers_arrived", "corridor_completed")),
                        "Conservation cumulative count or clock moved backward: " + case)
            previous = sample
        for role in ("source", "destination"):
            sample = final[role]
            metrics = arm["intersections"][sample["intersection_id"]]["metrics"]
            t = metrics["throughput"]
            require(t["external_vehicle_arrivals"] + t["transfer_vehicle_arrivals"] - t["vehicles_served"] == sample["vehicle_queue"]
                    and t["vehicles_served"] == sample["vehicles_served"], "Conservation vehicle balance differs: " + case + "/" + mode)
            require(t["external_pedestrian_arrivals"] - t["pedestrians_served"] == sample["pedestrian_queue"],
                    "Conservation pedestrian balance differs: " + case + "/" + mode)
            require(metrics["waiting"]["vehicle"]["count"] == t["vehicles_served"] + sample["vehicle_queue"]
                    and metrics["waiting"]["pedestrian"]["count"] == t["pedestrians_served"] + sample["pedestrian_queue"],
                    "Conservation waiting-episode counts differ: " + case + "/" + mode)
            require(abs(sum(metrics["signal"]["phase_time_seconds"].values()) - duration) <= .03,
                    "Conservation phase duration differs: " + case + "/" + mode)
        require(all(final[k] == network[k] for k in ("transfers_departed", "transfers_arrived", "corridor_completed")),
                "Conservation final transfer totals differ: " + case + "/" + mode)
        for kind in ("vehicle", "pedestrian"):
            total = sum(node["metrics"]["waiting"][kind]["total_seconds"] for node in arm["intersections"].values())
            require(abs(total - network["total_" + kind + "_wait_seconds"]) <= .021,
                    "Conservation local/network waiting sums differ: " + case + "/" + mode)
        checked += 1
    return checked

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
    timeline_samples = decision_records = conservation_runs = 0
    expected_files = {"paired-metrics.csv", "intersection-fairness.csv", "repeat.json"}
    nodes = {n["id"] for n in settings["network"]["intersections"]}
    for record in records:
        density, seed = record["density"], record["seed"]
        case = f"{density}-{seed}"
        expected_files.update((case + ".json", case + "-timeline.csv", case + "-decisions.csv"))
        raw = originals[density, seed] = load(case + ".json")
        conservation_runs += verify_conservation(case, raw)
        samples, decisions = verify_trace_exports(case, raw, read)
        timeline_samples += samples
        decision_records += decisions
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
            "timeline_samples": timeline_samples, "decision_records": decision_records,
            "conservation_runs": conservation_runs,
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
