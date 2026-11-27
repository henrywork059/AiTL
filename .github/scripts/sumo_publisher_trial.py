"""Matched read-workload comparison of legacy and isolated native-only publisher.

Not a full application replacement benchmark: no native authoritative camera
route, geometry equivalence, recirculating demand, frontend or GPU parity.
"""
from pathlib import Path
import csv
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

from sumo_migration_trial import processes
from app.services.camera_frames import CameraFrameService, SIMULATION_CAMERA_SOURCE_IDS
from app.services.signal_rules import SignalRulesService
from app.services.sumo_shadow_runtime import GeneratedSession
from app.services.sumo_shadow_adapter import ShadowSnapshot
from app.services.sumo_projection import NativeProjection, Projection, export_csv
from app.services.sumo_frame_publisher import NativeFramePublisher
from app.services.experiment_timeline_csv import serialize_experiment_timeline
from app.services.dataset_capture import DatasetCaptureService

SEED = 42
SAMPLES = 100
INTERVAL = .4


def arm(native):
    now = [0.0]
    with tempfile.TemporaryDirectory(prefix="mesh-publisher-") as tmp:
        folder = Path(tmp)
        with patch.dict(os.environ, {"AITL_DATASET_DIR": str(folder/"datasets"), "AITL_SIGNAL_RULES": str(folder/"signals.json")}):
            controller = SignalRulesService(config_path=folder/"signals.json",history_path=folder/"history.json")
            config = controller.defaults()
            config["mode"] = "fixed"
            controller.save_config(config)
            capture = DatasetCaptureService()
            publisher = NativeFramePublisher() if native else None
            legacy = None if native else CameraFrameService(simulation_seed=SEED,simulation_monotonic=lambda:now[0])
            session = None
            with patch("app.services.camera_frames.signal_rules_service",controller):
                try:
                    if native:
                        session = GeneratedSession(SEED,density="normal")
                        layout = NativeProjection(Projection.load(session.network_path),1)
                        publisher.begin(1)
                        controller.reset_runtime(0.0)
                    else:
                        legacy.set_simulation(True)
                    pids = [os.getpid()] + ([session.proc.pid] if native else [])
                    before = processes(pids)
                    start = time.perf_counter()
                    digest = hashlib.sha256()
                    timeline = []
                    native_rows = []
                    for i in range(1,SAMPLES+1):
                        now[0] = i*INTERVAL
                        if native:
                            for tick in (i*2-1,i*2):
                                phases = [controller.signal_state((tick-1)*.2+j*.05)["phase"] for j in range(4)]
                                phase = phases[0] if len(set(phases)) == 1 else "all_red"
                                session.set_phase(phase)
                                session.advance()
                            snap = ShadowSnapshot(SEED,i*2,False,session.agents())
                            meta,views = layout.render(snap)
                            publisher.publish(meta,views,received_at_ms=i*400)
                            requested = controller.signal_state(now[0])["phase"]
                            timeline.append({"t":round(now[0],1),"phase":requested})
                            native_rows.append({"t_seconds":round(now[0],1),"requested_phase":requested,
                                                "native_applied_permission":session.last_permission,
                                                "active_vehicles":sum(a.kind=="vehicle" for a in snap.agents),
                                                "active_pedestrians":sum(a.kind=="pedestrian" for a in snap.agents),
                                                "arrived_vehicle_trips":len(session.arrived),
                                                "arrived_pedestrian_trips":len(session.person_arrived)})
                        for sid in SIMULATION_CAMERA_SOURCE_IDS:
                            scene = publisher.scene_for(sid) if native else legacy.simulation_scene_for(sid)
                            frame = publisher.frame_for(sid) if native else legacy.simulation_frame_for(sid)
                            assert scene["frame_number"] == frame.frame_number
                            assert scene["source_id"] == frame.source_id and scene["received_at_ms"] == frame.received_at_ms
                            assert frame.width == 1280 and frame.height == 720
                            if native:
                                assert abs(scene["time_s"]-now[0]) < 1e-6
                            else:
                                assert -1e-6 <= now[0]-scene["simulation_time_seconds"] <= .5+1e-6
                                assert abs(legacy._simulation_clock_s-now[0]) < 1e-6
                                exact = legacy.exact_simulation_frame(**{k:scene["observation"][k] for k in
                                    ("epoch","generation","tick","layout_id","source_id")})
                                assert exact is frame
                            digest.update(frame.content)
                    wall = time.perf_counter()-start
                    after = processes(pids)
                    for sid in SIMULATION_CAMERA_SOURCE_IDS:
                        frame = publisher.frame_for(sid) if native else legacy.simulation_frame_for(sid)
                        record = capture.capture_frame(frame,session_id="publisher_evaluation")
                        assert (capture.dataset_root/record.image_path).read_bytes() == frame.content
                        assert json.loads((capture.dataset_root/record.metadata_path).read_text())["origin"] == frame.origin
                    assert capture.status()["frame_count"] == 4
                    result = {"arm":"isolated_native_only" if native else "legacy_only",
                              "scene_frame_pairs":SAMPLES*4,"simulation_s":SAMPLES*INTERVAL,
                              "captures":4,"digest":digest.hexdigest(),
                              "resources":{"wall_s":wall,"before":before,"after":after,
                                           "cpu_delta_s":sum(after[k]["cpu_s"]-before[k]["cpu_s"] for k in before),
                                           "end_combined_working_set_bytes":sum(v["working_set_bytes"] for v in after.values())}}
                    if native:
                        compatible = serialize_experiment_timeline({"fixed":{"timeline":timeline}})
                        rows = list(csv.DictReader(io.StringIO(compatible)))
                        assert len(rows)==SAMPLES and all(row["fixed_phase"] and not row["fixed_vehicle_queue"] and not row["adaptive_phase"] for row in rows)
                        result["partial_legacy_csv"] = compatible
                        result["native_timeline"] = native_rows
                        result["native_last_snapshot_csv"] = export_csv(meta)
                        result["unsupported_legacy_fields"] = ["vehicle_queue","pedestrian_queue","vehicle_passages","pedestrian_crossings","active_rules","adaptive_arm"]
                        publisher.invalidate()
                        assert all(publisher.frame_for(sid) is None for sid in SIMULATION_CAMERA_SOURCE_IDS)
                    return result
                finally:
                    if publisher: publisher.invalidate()
                    if legacy: legacy.set_simulation(False)
                    if session:
                        session.close()
                        assert not session.proc.is_alive()


def main(output):
    with tempfile.TemporaryDirectory() as tmp:
        runs = []
        for native in (False,True):
            target=Path(tmp)/f"arm-{int(native)}.json"
            subprocess.run([sys.executable,__file__,"--arm",str(int(native)),str(target)],check=True,timeout=180)
            runs.append(json.loads(target.read_text(encoding="utf-8")))
    result={"evidence":"executed matched read workload, isolated native-only vs legacy-only",
            "seed":SEED,"density":"normal","runs":runs,"replacement_parity":False,
            "default_migration_allowed":False,
            "limitations":"Equal duration and scene/frame read counts; finite native offered demand differs from legacy recirculation. Native arm validates/decodes four PNGs per publication; legacy uses cached frame service. No HTTP, GPU, editor, adaptive experiment or owner hardware parity; unsupported CSV fields remain blank."}
    Path(output).write_text(json.dumps(result,indent=2),encoding="utf-8")
    for run in runs:
        print(json.dumps({k:v for k,v in run.items() if k not in ("partial_legacy_csv","native_timeline","native_last_snapshot_csv")},indent=2))
    print("[PASS] matched read count, native frame identity, four captures, invalidation and partial experiment CSV schema; replacement parity remains false")


if __name__=="__main__":
    if sys.argv[1]=="--arm":
        Path(sys.argv[3]).write_text(json.dumps(arm(sys.argv[2]=="1")),encoding="utf-8")
    else:
        main(sys.argv[1])
