"""Shared existing experiment timeline CSV contract; no metric inference."""
import csv
from io import StringIO


def serialize_experiment_timeline(result: dict) -> str:
    fixed_timeline = result.get("fixed", {}).get("timeline", [])
    adaptive_timeline = result.get("adaptive", {}).get("timeline", [])
    rows = max(len(fixed_timeline), len(adaptive_timeline))
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow([
        "t_seconds",
        "fixed_phase", "fixed_vehicle_queue", "fixed_pedestrian_queue", "fixed_vehicle_passages", "fixed_pedestrian_crossings", "fixed_active_rules",
        "adaptive_phase", "adaptive_vehicle_queue", "adaptive_pedestrian_queue", "adaptive_vehicle_passages", "adaptive_pedestrian_crossings", "adaptive_active_rules",
    ])
    for index in range(rows):
        fixed = fixed_timeline[index] if index < len(fixed_timeline) else {}
        adaptive = adaptive_timeline[index] if index < len(adaptive_timeline) else {}
        writer.writerow([
            fixed.get("t", adaptive.get("t", "")),
            fixed.get("phase", ""), fixed.get("vehicle_queue", ""), fixed.get("pedestrian_queue", ""), fixed.get("vehicle_passages", ""), fixed.get("pedestrian_crossings", ""), "|".join(fixed.get("active_rules", [])),
            adaptive.get("phase", ""), adaptive.get("vehicle_queue", ""), adaptive.get("pedestrian_queue", ""), adaptive.get("vehicle_passages", ""), adaptive.get("pedestrian_crossings", ""), "|".join(adaptive.get("active_rules", [])),
        ])
    return output.getvalue()
