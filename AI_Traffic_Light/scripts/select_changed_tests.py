"""Select focused regressions for changed Git paths; unknown code uses full suite."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

P = "AI_Traffic_Light/"
BACKEND = P + "apps/pc-studio/backend/"
FRONTEND = P + "apps/pc-studio/frontend/"
SCRIPTS = P + "scripts/"

GROUPS = {
    "camera": ("camera", "remote_camera", "v0310", "v037"),
    "dataset": ("dataset",),
    "inference": ("inference", "model_registry"),
    "model": ("model_registry", "inference", "training"),
    "training": ("training", "model_registry", "dataset"),
    "network": ("network", "junction", "intersection", "decision", "emergency", "pedestrian", "vehicle_class"),
    "signal": ("signal", "decision", "emergency", "pedestrian", "vehicle_class"),
    "simulation": ("simulation", "signal_scenarios", "emergency", "pedestrian", "vehicle_class"),
    "traffic": ("traffic", "object_tracking", "zone", "decision"),
    "zone": ("zone", "camera_frame", "dataset"),
    "settings": ("runtime_settings", "atomic_json"),
    "logs": ("runtime_settings",),
}


def backend_group(path: str) -> str | None:
    """Map a changed backend service/route to related regression families."""
    part = path.removeprefix(BACKEND + "app/")
    if not part.startswith(("services/", "routes/")):
        return None
    stem = Path(part).stem
    if stem.startswith(("camera", "remote_camera")):
        return "camera"
    if stem.startswith("dataset"):
        return "dataset"
    if stem.startswith("inference") or stem == "yolo_placeholder":
        return "inference"
    if stem.startswith("model"):
        return "model"
    if stem.startswith("training"):
        return "training"
    if stem.startswith(("network", "junction_network", "intersection_network", "decision")):
        return "network"
    if stem.startswith("signal"):
        return "signal"
    if stem.startswith(("simulation", "experiments")):
        return "simulation"
    if stem.startswith(("traffic", "object_tracking")):
        return "traffic"
    if stem.startswith("zone"):
        return "zone"
    if stem.startswith("runtime_settings") or stem == "settings":
        return "settings"
    if stem == "logs":
        return "logs"
    return None


def select(paths: list[str], available_tests: list[str]) -> dict[str, object]:
    """Scope tests conservatively; shared/unknown changes fall back to all."""
    chosen: set[str] = set()
    frontend = False
    all_tests = not paths
    for raw in paths:
        path = raw.replace("\\", "/")
        if path == FRONTEND + "src/constants/projectVersion.ts":
            continue  # version/structure guard verifies this mirrored label
        if path.startswith(FRONTEND):
            frontend = True
            if path.endswith(("package.json", "package-lock.json")):
                all_tests = True
            if "junction" in path.lower():
                chosen.add("test_junction_network_frontend_structure.py")
            if "useSerialPolling" in path or "/pages/" in path or path.endswith("App.tsx"):
                chosen.add("test_frontend_polling_structure.py")
        elif path.startswith(BACKEND):
            if path.endswith(("requirements.txt", "requirements-training.txt")):
                all_tests = True
                continue
            group = backend_group(path)
            if group is None:
                all_tests = True
            else:
                chosen.update(t for t in available_tests if any(x in t for x in GROUPS[group]))
        elif path.startswith(SCRIPTS):
            name = Path(path).name
            if name.startswith("test_") and name.endswith(".py"):
                chosen.add(name)
            elif name == "select_changed_tests.py":
                chosen.add("test_select_changed_tests.py")
            elif name == "update_test_run.ps1":
                chosen.add("test_update_test_run_script.py")
            elif name != "check_structure.py":
                all_tests = True
        elif path.startswith(P + "apps/device-camera/"):
            chosen.update(t for t in available_tests if any(x in t for x in GROUPS["camera"]))
        elif path.startswith(P + "docs/") or path in {
            P + "VERSION", P + "CHANGELOG.md", P + "README.md", P + "AGENTS.md", "README.md",
        }:
            continue
        else:
            all_tests = True

    return {
        "all": all_tests,
        "tests": sorted(chosen.intersection(available_tests)),
        "frontend": frontend,
        "python_files": sorted(p for p in paths if p.startswith(P) and p.endswith(".py")),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args()
    available = [p.name for p in Path(__file__).parent.glob("test_*.py")]
    print(json.dumps(select(args.paths, available), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
