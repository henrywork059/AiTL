"""Execute bounded native policy pairs across seed and demand; retain all raw data."""
from pathlib import Path
import io
import json
import sys
import tempfile
import time
from unittest.mock import patch
from zipfile import ZipFile

# Existing native trial establishes the backend and test import paths.
from sumo_migration_trial import processes
from app.services.native_evaluation import NativeEvaluationService
from app.services.signal_rules import SignalRulesService


def main(out):
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    with tempfile.TemporaryDirectory(prefix="mesh-policy-matrix-") as tmp:
        root = Path(tmp)
        policy = SignalRulesService(config_path=root/"policy.json",
            history_path=root/"history.jsonl", respect_environment=False)
        policy.save_config(policy.defaults())
        original = policy.config_path.read_bytes()
        service = NativeEvaluationService(enabled=True)
        try:
            with patch("app.services.native_evaluation.signal_rules_service", policy):
                cases=[(seed,density,"standard") for seed in (42,73) for density in ("light","normal","busy")]
                cases += [(42,"normal",geometry) for geometry in ("compact","elongated")]
                for seed,density,geometry in cases:
                    start = time.perf_counter()
                    archive = service.compare(epoch=service.epoch,
                        generation=service.generation, seed=seed,
                        density=density, duration_seconds=120, geometry=geometry)
                    elapsed = time.perf_counter()-start
                    name = f"{seed}-{density}-{geometry}.zip"
                    (out/name).write_bytes(archive)
                    with ZipFile(io.BytesIO(archive)) as z:
                        manifest = json.loads(z.read("manifest.json"))
                        deltas = json.loads(z.read("deltas.json"))
                        summaries = {}
                        for mode in ("fixed", "adaptive"):
                            arm = json.loads(z.read(mode+".json"))
                            assert len(arm["timeline"]) == 600
                            assert arm["seed"] == seed and arm["density"] == density and arm["geometry"] == geometry
                            for kind, waits in arm["waiting_episodes"].items():
                                assert waits["observed_agent_seconds"] == arm["summary"][kind+"_wait_agent_s"]
                            summaries[mode] = arm["summary"]
                        rows.append({"archive":name,"seed":seed,"density":density,"geometry":geometry,"layout_id":manifest["layout_id"],
                            "wall_s":elapsed,"demand_digest":manifest["demand_digest"],
                            "summaries":summaries,"deltas":deltas})
            assert len({row["layout_id"] for row in rows}) == 3
            assert policy.config_path.read_bytes() == original
        finally:
            service.close()
    result = {"evidence":"executed synthetic native policy matrix",
              "duration_seconds":120,"step_seconds":.2,"pairs":rows,
              "production_experiment_parity":False,"physical_output_allowed":False}
    (out/"matrix.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
