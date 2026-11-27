"""Executed finite native density/slow-demand and temporary capture evaluation."""
from pathlib import Path
import csv
import io
import json
import os
import sys
import tempfile
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "AI_Traffic_Light/apps/pc-studio/backend"))
from app.services.sumo_shadow_runtime import GeneratedSession
from app.services.sumo_shadow_fixture import DENSITY_COUNTS, SLOW_WALK_M_S, PhaseMap
from app.services.sumo_projection import NativeProjection, Projection, export_csv, PROVENANCE
from app.services.sumo_shadow_adapter import ShadowSnapshot
from app.services.sumo_projection_capture import evaluation_frames
from app.services.dataset_capture import DatasetCaptureService


def run(density):
    session = GeneratedSession(42, density=density)
    try:
        mapping = PhaseMap.load(session.network_path)
        projection = NativeProjection(Projection.load(session.network_path), 1)
        seen_v, seen_p = set(), set()
        prior = {}
        slow_speed = 0.0
        slow_crossing = slow_clear = 0
        samples = 0
        peak_agents = 0
        latest = None
        # Long pedestrian service deliberately allows the slow fixture to clear.
        cycle = ["vehicle_green"] * 100 + ["vehicle_yellow"] * 15 + ["all_red"] * 10 + ["pedestrian_green"] * 150 + ["pedestrian_flashing"] * 50 + ["all_red"] * 10
        start = time.perf_counter()
        for tick in range(2500):
            phase = cycle[tick % len(cycle)]
            session.set_phase(phase)
            session.advance()
            agents = session.agents()
            peak_agents = max(peak_agents, len(agents))
            grants = {i for i,ch in enumerate(session.last_permission) if ch == "G"}
            assert not (grants.intersection(mapping.vehicles) and grants.intersection(mapping.pedestrians))
            if any(a.kind == "pedestrian" and a.road_id in mapping.crossing_edges for a in prior.values()):
                assert not grants.intersection(mapping.vehicles)
            if phase not in ("vehicle_green","pedestrian_green"):
                assert not grants
            for agent in agents:
                if agent.kind == "vehicle":
                    seen_v.add(agent.engine_id)
                else:
                    seen_p.add(agent.engine_id)
                    old = prior.get(agent.id)
                    if agent.road_id in mapping.crossing_edges and old is not None and old.road_id not in mapping.crossing_edges:
                        assert phase == "pedestrian_green" and grants.intersection(mapping.pedestrians)
                    if agent.engine_id == "p0":
                        slow_speed = max(slow_speed, agent.speed_m_s)
                        if agent.road_id in mapping.crossing_edges:
                            slow_crossing += 1
                            if phase == "pedestrian_flashing":
                                slow_clear += 1
            prior = {a.id:a for a in agents}
            if tick % 100 == 99 and agents:
                meta, views = projection.render(ShadowSnapshot(42,tick+1,False,agents))
                assert len(list(csv.DictReader(io.StringIO(export_csv(meta))))) == len(agents)
                latest = meta, views
                samples += 1
        wall = time.perf_counter() - start
        n_v,n_p = DENSITY_COUNTS[density]
        assert seen_v == session.arrived == {f"v{i}" for i in range(n_v)}
        assert seen_p == session.person_arrived == {f"p{i}" for i in range(n_p)}
        assert 0 < slow_speed <= SLOW_WALK_M_S + .05 and slow_crossing > 0
        assert latest is not None
        meta, views = latest
        with tempfile.TemporaryDirectory(prefix="mesh-native-eval-") as tmp:
            with patch.dict(os.environ, {"AITL_DATASET_DIR": tmp}):
                capture = DatasetCaptureService()
                for frame in evaluation_frames(meta, views, received_at_ms=100):
                    rec = capture.capture_frame(frame, session_id="native_evaluation")
                    assert rec.origin == PROVENANCE and rec.source_frame_number == meta["tick"]
                    assert (Path(tmp)/rec.image_path).read_bytes() == frame.content
                    assert json.loads((Path(tmp)/rec.metadata_path).read_text())["origin"] == PROVENANCE
                assert capture.status()["frame_count"] == 4
        return {"density":density,"offered_vehicles":n_v,"offered_pedestrians":n_p,
                "arrived_vehicles":len(session.arrived),"arrived_pedestrians":len(session.person_arrived),
                "peak_agents":peak_agents,"slow_max_speed_m_s":slow_speed,
                "slow_crossing_samples":slow_crossing,"slow_clear_samples":slow_clear,
                "projection_samples":samples,"temporary_captures":4,"wall_s":wall}
    finally:
        session.close()
        assert not session.proc.is_alive()


if __name__ == "__main__":
    result = {"evidence":"executed isolated native finite demand and capture evaluation",
              "seed":42,"step_s":.2,"horizon_s":500,"runs":[run(d) for d in DENSITY_COUNTS],
              "replacement_parity":False,"default_migration_allowed":False,
              "limitations":"Finite demand differs from legacy recirculating slots; long WALK test schedule; no authoritative capture or matched replacement resource benchmark."}
    Path(sys.argv[1]).write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))
