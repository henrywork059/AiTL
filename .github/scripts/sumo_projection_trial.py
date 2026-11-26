"""Actual native PNG/CSV projection evidence; isolated from normal camera APIs."""
import csv
import hashlib
import io
import json
from pathlib import Path
import sys

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "AI_Traffic_Light/apps/pc-studio/backend"))
from app.services.sumo_projection import VIEW_FLIPS, export_csv
from app.services.sumo_projection_session import NativeProjectionSession


def run(output):
    output.mkdir(parents=True, exist_ok=True)
    runner = NativeProjectionSession()
    digest = hashlib.sha256()
    sampled = 0
    max_agents = 0
    snapshot = None
    try:
        initial, _ = runner.reset(42)
        proc = runner._session.proc
        cycle = ["vehicle_green"] * 60 + ["vehicle_yellow"] * 15 + ["all_red"] * 10 + ["pedestrian_green"] * 60 + ["pedestrian_flashing"] * 15 + ["all_red"] * 10
        for i in range(220):
            meta, views = runner.step(cycle[i % len(cycle)])
            assert meta["tick"] == i + 1
            max_agents = max(max_agents, len(meta["agents"]))
            if (i + 1) % 20 == 0:
                canonical = cv2.imdecode(np.frombuffer(views["simulation_camera"], np.uint8), cv2.IMREAD_COLOR)
                assert canonical.shape == (720, 1280, 3)
                for sid, flip in VIEW_FLIPS.items():
                    decoded = cv2.imdecode(np.frombuffer(views[sid], np.uint8), cv2.IMREAD_COLOR)
                    assert np.array_equal(decoded, canonical if flip is None else cv2.flip(canonical, flip))
                assert len({a["id"] for a in meta["agents"]}) == len(meta["agents"])
                rows = list(csv.DictReader(io.StringIO(export_csv(meta))))
                assert len(rows) == len(meta["agents"])
                for agent, row in zip(meta["agents"], rows):
                    assert row["id"] == agent["id"] and float(row["x"]) == agent["x"] and float(row["y"]) == agent["y"]
                    for sid in VIEW_FLIPS:
                        layout = runner._projection.layout
                        xy = layout.world(*layout.pixel(agent["x_m"], agent["y_m"], sid), sid)
                        assert abs(xy[0] - agent["x_m"]) < 1e-8 and abs(xy[1] - agent["y_m"]) < 1e-8
                digest.update(json.dumps(meta, sort_keys=True).encode())
                digest.update(views["simulation_camera"])
                sampled += 1
                if snapshot is None or len(meta["agents"]) > len(snapshot[0]["agents"]):
                    snapshot = (meta, views)
        assert snapshot is not None and max_agents > 0
        runner.pause(True)
        assert runner.step("all_red")[0]["tick"] == 220
        runner.pause(False)
        assert runner.step("all_red")[0]["tick"] == 221
        reset, _ = runner.reset(42)
        assert reset["generation"] == initial["generation"] + 1 and reset["tick"] == 0
        assert not proc.is_alive()
        proc = runner._session.proc
        runner.close()
        assert runner.read() is None and not proc.is_alive()
        meta, views = snapshot
        for sid, data in views.items():
            (output / (sid + ".png")).write_bytes(data)
        (output / "snapshot.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        (output / "agents.csv").write_text(export_csv(meta), encoding="utf-8")
        result = {"evidence": "executed isolated native geometry projection", "sampled_four_view_sets": sampled,
                  "seed": 42, "simulation_s": 44, "max_agents": max_agents,
                  "snapshot_tick": meta["tick"], "snapshot_agents": len(meta["agents"]),
                  "digest": digest.hexdigest(), "coordinate_round_trip": True,
                  "csv_snapshot_parity": True, "pause_reset_reap": True,
                  "replacement_parity": False, "default_migration_allowed": False}
        (output / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
    finally:
        runner.close()


if __name__ == "__main__":
    run(Path(sys.argv[1]))
