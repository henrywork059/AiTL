"""Isolated reproducible paired network-policy experiments; no live data or outputs."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
from statistics import mean
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/pc-studio/backend"))
from app.services.network_simulation_experiments import NetworkSimulationExperimentService
from app.services.signal_rules import SignalRulesService

MODES = ("fixed", "adaptive", "cooperative")
METRICS = ("total_vehicle_wait_seconds", "total_pedestrian_wait_seconds",
           "total_vehicle_queue_average", "total_pedestrian_queue_average",
           "corridor_completed", "max_observed_pedestrian_wait_seconds")
DENSITIES = ("light", "normal", "busy")


def fixture():
    nodes = [{"id": key, "label": "Synthetic " + key, "enabled": True,
              "source_ids": ["cam_" + key], "zone_ids": ["queue_" + key, "ped_" + key],
              "signal_profile": "Normal"} for key in ("A", "B")]
    network = {"schema_version": 1, "active_intersection_id": "A", "intersections": nodes,
               "links": [{"id": "A_to_B", "enabled": True, "source_intersection_id": "A",
                          "destination_intersection_id": "B", "source_approach": "eastbound_out",
                          "destination_approach": "westbound_in", "travel_time_seconds": 7.5}]}
    zones = [{"id": prefix + key, "type": kind} for key in ("A", "B")
             for prefix, kind in (("queue_", "vehicle_queue"), ("ped_", "pedestrian_waiting"))]
    return network, zones


def primary(result):
    return {mode: {metric: result[mode]["network_metrics"][metric] for metric in METRICS} for mode in MODES}


def deltas(metrics):
    return {candidate + "_minus_" + baseline:
            {key: round(metrics[candidate][key] - metrics[baseline][key], 6) for key in METRICS}
            for candidate, baseline in (("adaptive", "fixed"), ("cooperative", "fixed"), ("cooperative", "adaptive"))}


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")


def execute(output, seeds=(42, 43), densities=DENSITIES, duration=120):
    if os.environ.get("AITL_SIGNAL_RULES"):
        raise ValueError("Unset AITL_SIGNAL_RULES before isolated experiment")
    if not seeds or len(set(seeds)) != len(seeds) or not densities or len(set(densities)) != len(densities) or set(densities) - set(DENSITIES):
        raise ValueError("Require unique seeds and supported densities")
    output.mkdir(parents=True, exist_ok=False)
    network, zones = fixture()
    records = []
    with TemporaryDirectory(prefix="mesh_seeded_batch_") as temporary:
        root = Path(temporary)
        policy = SignalRulesService(config_path=root / "rules.json", history_path=root / "history.json",
                                    respect_environment=False).defaults()
        service = NetworkSimulationExperimentService(storage_root=root / "runs",
                    config_provider=lambda: policy, network_provider=lambda: network, zones_provider=lambda: zones)
        def run(seed, density):
            return service.run(duration_seconds=duration, density=density, seed=seed,
                               sample_interval_seconds=2, profile="Normal", link_id="A_to_B",
                               transfer_share_percent=70, emergency_event_enabled=False)
        for density in densities:
            for seed in seeds:
                result = run(seed, density)
                if result.get("prototype_only") is not True:
                    raise ValueError("Expected isolated prototype run")
                case = f"{density}-{seed}"
                metrics = primary(result)
                plan = result["scenario"]["arrival_plan"]["fingerprint_sha256"]
                write_json(output / (case + ".json"), result)
                (output / (case + "-timeline.csv")).write_text(service.export_csv(result["run_id"]), encoding="utf-8")
                (output / (case + "-decisions.csv")).write_text(service.export_evidence_csv(result["run_id"]), encoding="utf-8")
                records.append({"density": density, "seed": seed, "demand_sha256": plan,
                                "run_id": result["run_id"], "metrics": metrics, "paired_deltas": deltas(metrics)})
        first = records[0]
        repeat = run(first["seed"], first["density"])
        repeat_ok = primary(repeat) == first["metrics"] and repeat["scenario"]["arrival_plan"]["fingerprint_sha256"] == first["demand_sha256"]
        write_json(output / "repeat.json", repeat)
        if not repeat_ok:
            raise ValueError("Repeat demand or primary metrics differ")
    groups = {density: [r for r in records if r["density"] == density] for density in densities}
    summary = {density: {pair: {metric: {"mean": mean(values), "min": min(values), "max": max(values),
                "n": len(values)} for metric in METRICS
                for values in [[r["paired_deltas"][pair][metric] for r in group]]}
                for pair in group[0]["paired_deltas"]} for density, group in groups.items()}
    with (output / "paired-metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["density", "seed", "demand_sha256", "mode", *METRICS])
        for r in records:
            for mode in MODES:
                writer.writerow([r["density"], r["seed"], r["demand_sha256"], mode, *[r["metrics"][mode][k] for k in METRICS]])
    manifest = {"schema_version": 1, "evidence_class": "actually_executed_synthetic_queue_model",
                "physical_output_allowed": False, "settings": {"duration_seconds": duration,
                "sample_interval_seconds": 2, "seeds": list(seeds), "densities": list(densities),
                "profile": "Normal", "transfer_share_percent": 70, "emergency_event_enabled": False,
                "network": network, "zones": zones, "signal_policy": policy},
                "units": {"total_vehicle_wait_seconds": "vehicle-seconds (includes waits truncated at horizon)",
                          "total_pedestrian_wait_seconds": "person-seconds (includes waits truncated at horizon)",
                          "total_vehicle_queue_average": "vehicles (sampled)", "total_pedestrian_queue_average": "persons (sampled)",
                          "corridor_completed": "vehicles", "max_observed_pedestrian_wait_seconds": "seconds"},
                "records": records, "paired_summary_by_density": summary,
                "repeat_primary_metrics_and_demand_equal": repeat_ok,
                "limitations": "Restricted synthetic queue model; same exogenous arrivals across three primary policies; policy-dependent transfers. Other existing service arms retained in raw exports. Small seed sample, range not confidence interval; no native/legacy or field superiority claim.",
                "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir()) if p.is_file()}}
    write_json(output / "manifest.json", manifest)
    print(json.dumps({"cases": len(records), "repeat_equal": repeat_ok, "paired_summary_by_density": summary}))
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration", type=int, default=120, choices=(30, 60, 120, 240))
    args = parser.parse_args()
    execute(args.output, duration=args.duration)
