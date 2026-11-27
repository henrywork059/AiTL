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
from app.services.simulation_experiments import _ModeSimulation
from app.services.simulation_finite_fixture import Segment, Trip, FiniteReference, RouteGateAdapter
from app.services.simulation_gate_metrics import GateMetrics
import hashlib


def replay_reference(arm):
    """Same declared route geometry/offers and requested phases; not legacy PC Studio."""
    def segment(row):
        return Segment(row["road_id"],row["kind"],tuple(tuple(pt) for pt in row["points"]))
    trips=tuple(Trip(t["ident"],t["kind"],t["depart_s"],t["desired_speed"],
                     tuple(segment(s) for s in t["path"]),
                     tuple(tuple(segment(s) for s in path) for path in t["alternatives"]))
                for t in arm["demand_manifest"])
    digest=hashlib.sha256(json.dumps(arm["demand_manifest"],sort_keys=True,separators=(",",":")).encode()).hexdigest()
    assert digest==arm["demand_digest"]
    model=FiniteReference(trips)
    adapter=RouteGateAdapter(trips)
    metrics=GateMetrics()
    timeline=[]
    for row in arm["timeline"]:
        agents=model.advance(row["phase"])
        timeline.append({**metrics.sample(row["tick"],adapter.observations(agents)),"requested_phase":row["phase"]})
    return {"engine":"finite_reference","demand_digest":digest,"layout_id":arm["layout_id"],
            "summary":metrics.summary(),"waiting_episodes":metrics.waiting_episodes(),
            "timeline":timeline,"arrived":sorted(model.arrived),
            "active":sorted(model.active),"pending":sorted(t.ident for t in model.pending),
            "production_experiment_parity":False}


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
                            # Execute the existing production benchmark, not a new substitute.
                            if geometry=="standard":
                                legacy_root=root/f"{seed}-{density}-{mode}-historical"
                                legacy_root.mkdir()
                                legacy=_ModeSimulation(mode=mode,density=density,seed=seed,duration_seconds=120,
                                    sample_interval_seconds=1,policy_config=json.loads(z.read("policy.json")),
                                    zones=[],temp_root=legacy_root,normalized_gate_evidence=True).run()
                                common=legacy["normalized_gate_evidence"]
                                assert len(common["timeline"])==600
                                for kind,waits in common["waiting_episodes"].items():
                                    assert waits["observed_agent_seconds"]==common["summary"][kind+"_wait_agent_s"]
                                (out/f"{seed}-{density}-{mode}-production-legacy.json").write_text(json.dumps(legacy,indent=2),encoding="utf-8")
                                if seed==42:
                                    live_root=root/f"{seed}-{density}-{mode}-live"
                                    live_root.mkdir()
                                    live=_ModeSimulation(mode=mode,density=density,seed=seed,duration_seconds=120,
                                        sample_interval_seconds=1,policy_config=json.loads(z.read("policy.json")),
                                        zones=[],temp_root=live_root,normalized_gate_evidence=True,live_slot_demand=True).run()
                                    live_common=live["normalized_gate_evidence"]
                                    assert live_common["demand_model"]=="production_live_slots"
                                    assert live_common["movement_step_seconds"]==.05 and len(live_common["timeline"])==600
                                    for kind,waits in live_common["waiting_episodes"].items():
                                        assert waits["observed_agent_seconds"]==live_common["summary"][kind+"_wait_agent_s"]
                                    (out/f"{seed}-{density}-{mode}-live-slot-legacy.json").write_text(json.dumps(live,indent=2),encoding="utf-8")
                            reference=replay_reference(arm)
                            assert len(reference["timeline"])==len(arm["timeline"])
                            (out/f"{seed}-{density}-{geometry}-{mode}-reference.json").write_text(json.dumps(reference,indent=2),encoding="utf-8")
                        rows.append({"archive":name,"seed":seed,"density":density,"geometry":geometry,"layout_id":manifest["layout_id"],
                            "wall_s":elapsed,"demand_digest":manifest["demand_digest"],
                            "summaries":summaries,"deltas":deltas})
            assert len({row["layout_id"] for row in rows}) == 3
            assert policy.config_path.read_bytes() == original
        finally:
            service.close()
    result = {"evidence":"executed synthetic native policy matrix",
              "duration_seconds":120,"step_seconds":.2,"pairs":rows,
              "reference_replays":16,"production_legacy_arms":12,"live_slot_legacy_arms":6,"production_experiment_parity":False,"physical_output_allowed":False}
    (out/"matrix.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
