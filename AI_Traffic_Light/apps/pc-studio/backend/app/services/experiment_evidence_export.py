"""Hash-manifested exports of a single already-stored experiment snapshot.

Do not infer unrecorded execution metadata, rerun experiments or mix metric contracts.
"""
from hashlib import sha256
from io import BytesIO
import json
from zipfile import ZIP_DEFLATED, ZipFile

from app.core.project_version import PROJECT_VERSION
from app.services.experiment_timeline_csv import serialize_experiment_timeline


def json_bytes(value) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def experiment_evidence_zip(result: dict, run_id: str) -> bytes:
    if result.get("run_id") != run_id or result.get("prototype_only") is not True:
        raise ValueError("Stored experiment identity or scope mismatch")
    scenario = result["scenario"]
    modes = ("fixed", "adaptive")
    if any(result[mode].get("mode") != mode for mode in modes):
        raise ValueError("Stored experiment mode mismatch")
    files = {"experiment.json": json_bytes(result),
             "samples.csv": serialize_experiment_timeline(result).encode("utf-8")}
    manifest = {
        "schema_version": 1, "kind": "stored_single_junction_experiment",
        "run_id": run_id, "created_at_ms": result.get("created_at_ms"),
        "exporter_version": PROJECT_VERSION, "execution_version": result.get("execution_version"),
        "provenance": "executed_synthetic_simulation", "prototype_only": True,
        "physical_output_allowed": False, "scenario": scenario,
        "sample_counts": {mode: len(result[mode]["timeline"]) for mode in modes},
        "sha256": {name: sha256(data).hexdigest() for name, data in files.items()},
        "not_recorded_by_this_export": ["execution_git_sha", "original_full_policy_and_zone_configuration",
            "execution_cpu_memory", "endurance_measurement", "field_validation", "emissions_measurement"],
        "limitations": "Stored result and existing CSV from one read; no rerun. Exporter version is not the execution version. Missing original execution metadata remains unknown. Synthetic simulation only.",
    }
    stream = BytesIO()
    with ZipFile(stream, "w", compression=ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
        archive.writestr("manifest.json", json_bytes(manifest))
    return stream.getvalue()
