"""Deterministic scheduler plus actual legacy world integration."""
from __future__ import annotations

import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/pc-studio/backend"))
from app.services.simulation_adapter import LegacySimulationAdapter


class AdapterTests(unittest.TestCase):
    def test_partition_and_snapshot(self):
        def run(times):
            trace = []
            adapter = LegacySimulationAdapter(lambda dt: trace.append((adapter.time_s, dt)))
            adapter.reset(seed=42, now=0)
            for now in times:
                adapter.sync(now)
                self.assertEqual(adapter.snapshot(), adapter.snapshot())
            return trace, adapter.snapshot()

        a = run([i / 100 for i in range(1, 101)])
        b = run([0.031, 0.179, 0.263, 0.999, 1.0])
        self.assertEqual(a, b)
        self.assertEqual(len(a[0]), 20)
        self.assertEqual(a[1].time_s, 1.0)
        self.assertEqual(a[1].seed, 42)

    def test_pause_and_cap(self):
        trace = []
        adapter = LegacySimulationAdapter(trace.append)
        adapter.reset(seed=7, now=10)
        self.assertEqual(adapter.sync(10.03), 0)
        adapter.set_paused(True, 10.03)
        self.assertEqual(adapter.sync(99), 0)
        adapter.set_paused(False, 100)
        self.assertEqual(adapter.sync(100.02), 1)
        self.assertEqual(adapter.sync(109), 40)
        self.assertEqual(adapter.sync(108), 0)
        self.assertEqual(adapter.sync(109.05), 1)
        self.assertEqual(adapter.time_s, 2.1)
        self.assertEqual(len(trace), 42)
        adapter.reset(seed=9, now=110, paused=True)
        self.assertEqual(adapter.step(1), 0)
        self.assertEqual(adapter.time_s, 0)
        adapter.stop()
        self.assertEqual(adapter.sync(111), 0)

    def test_invalid_duration(self):
        adapter = LegacySimulationAdapter(lambda dt: None)
        for value in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                adapter.step(value)

    def test_published_scene_matches_cached_camera_frame(self):
        from app.services.camera_frames import CameraFrameService
        from app.services.observation_identity import simulation_view_point
        now=[0.]
        service=CameraFrameService(simulation_seed=42,simulation_monotonic=lambda:now[0])
        phase={"phase":"vehicle_green","vehicle_go":True,"pedestrian_walk":False,
               "seconds_remaining":12,"base_cycle_seconds":34,"mode":"fixed",
               "active_profile":"fixture","active_rules":[]}
        with patch.object(service,"_simulation_signal_state_locked",return_value=phase):
            service.set_simulation(True)
            first=service.simulation_scene_for("simulation_camera")
            frame=service.latest_frame()
            now[0]=.2
            later=service.simulation_scene_for("simulation_camera")
            self.assertEqual(later,first)
            self.assertIs(frame,service.latest_frame())
            self.assertEqual(service._simulation_clock_s,.2)
            mirror=service.simulation_scene_for("simulation_camera_d")
            self.assertEqual(mirror["vehicles"],first["vehicles"])
            self.assertEqual(mirror["observation"]["frame_number"],frame.frame_number)
            for a,b in zip(first["view_agents"],mirror["view_agents"]):
                self.assertEqual((b["x"],b["y"]),simulation_view_point(a["x"],a["y"],1280,720,"simulation_camera_d"))
            first["vehicles"].clear()
            self.assertTrue(service.simulation_scene_for("simulation_camera")["vehicles"])
            identity=later["observation"]
            exact={k:identity[k] for k in ("epoch","generation","tick","layout_id","source_id")}
            self.assertIs(frame,service.exact_simulation_frame(**exact))
            self.assertEqual(service._simulation_clock_s,.2)
            # A batch acquires the clock once, even when encoding multiple views.
            times=iter([.5,1.,1.5,2.])
            service._simulation_monotonic=lambda:next(times)
            batch=service.simulation_frames_for(("simulation_camera","simulation_camera_b","simulation_camera_d"))
            self.assertEqual(len({(f.frame_number,f.received_at_ms) for f in batch}),1)
            self.assertEqual(service._simulation_clock_s,.5)
            from app.core.exceptions import AppError
            with self.assertRaises(AppError):
                service.exact_simulation_frame(**exact)
            service._simulation_monotonic=lambda:now[0]
            now[0]=.5
            current=service.simulation_scene_for("simulation_camera")
            self.assertGreater(current["frame_number"],frame.frame_number)
            self.assertEqual(current["simulation_time_seconds"],.5)
            token=service.observation_mode_token
            service.configure_simulation(density="busy")
            self.assertNotEqual(service.observation_mode_token,token)
            reset=service.simulation_scene_for("simulation_camera")
            self.assertEqual(reset["observation"]["generation"],service.observation_mode_token[1])
            self.assertEqual(len(reset["vehicles"]),12)

    def test_protected_camera_engine_switch_rollback_and_fault(self):
        from app.services.camera_frames import CameraFrameService, SIMULATION_CAMERA_SOURCE_IDS
        from app.services.traffic_observations import selected_observation_is_current
        from app.services.dataset_capture import DatasetCaptureService
        from app.core.exceptions import AppError
        from tempfile import TemporaryDirectory
        import cv2
        import numpy as np
        import json
        now=[0.]
        service=CameraFrameService(simulation_seed=42,simulation_monotonic=lambda:now[0])
        phase={"phase":"vehicle_green","vehicle_go":True,"pedestrian_walk":False,
               "seconds_remaining":12,"base_cycle_seconds":34,"mode":"fixed",
               "active_profile":"fixture","active_rules":[]}
        def signal():
            return dict(phase)
        with patch.object(service,"_simulation_signal_state_locked",side_effect=signal), \
             patch("app.services.camera_frames.camera_frame_service",service):
            service.set_simulation(True)
            original=service.latest_frame()
            self.assertTrue(selected_observation_is_current(original.observation))
            old=service.simulation_scene_for("simulation_camera")["observation"]
            identity={k:old[k] for k in ("epoch","generation","tick","layout_id","source_id")}
            with self.assertRaises(AppError):
                service.configure_simulation(engine="protected")
            self.assertIs(service.latest_frame(),original)
            service.configure_simulation(paused=True)
            status=service.configure_simulation(engine="protected")
            self.assertEqual(status["simulation_engine"],"protected")
            self.assertTrue(status["simulation_paused"])
            self.assertEqual(service._simulation_clock_s,0.)
            self.assertFalse(selected_observation_is_current(original.observation))
            with self.assertRaises(AppError):
                service.exact_simulation_frame(**identity,engine="legacy")
            self.assertEqual(service._protected_world.occupancy(),(False,False))
            first=service.simulation_scene_for("simulation_camera",engine="protected")
            self.assertEqual(first["observation"]["layout_id"],old["layout_id"])
            self.assertTrue(first["observation"]["detector_input_eligible"])
            batch=service.simulation_frames_for(SIMULATION_CAMERA_SOURCE_IDS)
            self.assertEqual(len(batch),4)
            self.assertEqual(len({(f.frame_number,f.received_at_ms,f.mode_generation) for f in batch}),1)
            self.assertTrue(all(f.origin=="simulation" and f.simulation_engine=="protected" for f in batch))
            self.assertTrue(selected_observation_is_current(batch[0].observation))
            canonical=cv2.imdecode(np.frombuffer(batch[0].content,np.uint8),cv2.IMREAD_COLOR)
            from app.services.observation_identity import SIMULATION_VIEW_FLIPS
            for frame in batch[1:]:
                self.assertTrue(np.array_equal(cv2.flip(canonical,SIMULATION_VIEW_FLIPS[frame.source_id]),
                    cv2.imdecode(np.frombuffer(frame.content,np.uint8),cv2.IMREAD_COLOR)))
            with TemporaryDirectory() as tmp:
                writer=DatasetCaptureService(dataset_root=Path(tmp),respect_environment=False)
                record=writer.capture_frame(batch[0],session_id="protected_trial")
                self.assertEqual(record.simulation_engine,"protected")
                self.assertEqual(json.loads((Path(tmp)/record.metadata_path).read_text())["simulation_engine"],"protected")
            service.configure_simulation(paused=False)
            for tick in range(1,1201):
                phase["phase"]=("vehicle_green","pedestrian_green","all_red","pedestrian_green","vehicle_green","pedestrian_flashing")[(tick//200)%6]
                phase["vehicle_go"]=phase["phase"]=="vehicle_green"
                phase["pedestrian_walk"]=phase["phase"]=="pedestrian_green"
                service._advance_simulation_locked(.05)
                self.assertNotEqual(service._protected_world.occupancy(),(True,True))
            now[0]=60.
            service.configure_simulation(paused=True)
            service.configure_simulation(engine="legacy")
            restored=service.latest_frame()
            self.assertEqual(restored.content,original.content)
            self.assertGreater(restored.mode_generation,batch[0].mode_generation)
            self.assertFalse(selected_observation_is_current(batch[0].observation))
            service.configure_simulation(engine="protected")
            service.configure_simulation(paused=False)
            with patch.object(service._protected_world,"step",side_effect=RuntimeError("fixture fault")):
                now[0]+=.1
                with self.assertRaises(AppError): service.latest_frame()
            self.assertIsNone(service.latest_frame())
            self.assertTrue(service.status()["simulation_fault"])
            self.assertFalse(service.simulation_frames_for(SIMULATION_CAMERA_SOURCE_IDS))
            with self.assertRaises(AppError): service.configure_simulation(paused=False)
            service.configure_simulation(engine="legacy")
            self.assertEqual(service.latest_frame().content,original.content)
            service.set_simulation(False)

    def test_protected_camera_benchmark_exact_motion(self):
        from app.services.camera_frames import CameraFrameService
        from app.services.simulation_experiments import _ModeSimulation
        from app.services.signal_rules import signal_rules_service
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            for seed in (42,73):
                for density in ("light","normal","busy"):
                    clock=[0.]
                    service=CameraFrameService(simulation_seed=seed,simulation_monotonic=lambda:clock[0])
                    phase={"phase":"vehicle_green","vehicle_go":True,"pedestrian_walk":False,
                           "seconds_remaining":12,"base_cycle_seconds":34,"mode":"fixed",
                           "active_profile":"fixture","active_rules":[]}
                    with patch.object(service,"_simulation_signal_state_locked",side_effect=lambda:dict(phase)):
                        service.configure_simulation(density=density,engine="protected")
                        service.set_simulation(True)
                        benchmark=_ModeSimulation(mode="fixed",density=density,seed=seed,
                            duration_seconds=120,sample_interval_seconds=1,
                            policy_config=signal_rules_service.get_config(),zones=[],temp_root=Path(tmp),
                            protected_slots=True)
                        world=service._protected_world
                        other=benchmark.protected_world
                        self.assertEqual(world.demand_digest,other.demand_digest)
                        self.assertEqual(world.demand_manifest,other.demand_manifest)
                        self.assertEqual(service.latest_frame().simulation_demand_digest,other.demand_digest)
                        self.assertEqual(service.simulation_scene_for("simulation_camera")["observation"]["demand_digest"],other.demand_digest)
                        def state(w):
                            return ([(v.x,v.y,v.width,v.speed,v.direction) for v in w.vehicles],
                                    [(v.x,v.y,v.speed,v.direction) for v in w.pedestrians],
                                    w.vehicle_visits,w.pedestrian_visits)
                        self.assertEqual(state(world),state(other))
                        for tick in range(2400):
                            phase["phase"]=("vehicle_green","pedestrian_green","all_red","pedestrian_green","vehicle_green","pedestrian_flashing")[(tick//200)%6]
                            phase["vehicle_go"]=phase["phase"]=="vehicle_green"
                            phase["pedestrian_walk"]=phase["phase"]=="pedestrian_green"
                            expected=world.permission(phase["phase"])
                            service._advance_simulation_locked(.05)
                            _,actual=benchmark._advance_world(.05,tick*.05,phase)
                            self.assertEqual(actual,expected)
                            self.assertEqual(state(world),state(other))
                            self.assertNotEqual(world.occupancy(),(True,True))
                        self.assertGreater(sum(world.vehicle_visits)+sum(world.pedestrian_visits),0)
                        service.set_simulation(False)

    def test_shared_live_slot_motion(self):
        from app.services.camera_frames import CameraFrameService
        from app.services.simulation_experiments import _ModeSimulation
        from app.services.signal_rules import signal_rules_service
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            service=CameraFrameService(simulation_seed=42,simulation_monotonic=lambda:0.)
            with patch.object(service,"_simulation_signal_state_locked",return_value={
                "phase":"vehicle_green","vehicle_go":True,"pedestrian_walk":False,
                "seconds_remaining":12,"base_cycle_seconds":34,"mode":"fixed",
                "active_profile":"fixture","active_rules":[]}):
                service.set_simulation(True)
            benchmark=_ModeSimulation(mode="fixed",density="normal",seed=42,
                duration_seconds=30,sample_interval_seconds=1,
                policy_config=signal_rules_service.get_config(),zones=[],
                temp_root=Path(tmp),live_slot_demand=True)
            def state(vehicles,pedestrians):
                return ([(v.x,v.y,v.width,v.speed,v.direction) for v in vehicles],
                        [(v.x,v.y,v.speed,v.direction) for v in pedestrians])
            self.assertEqual(state(service._vehicles,service._pedestrians),
                             state(benchmark.vehicles,benchmark.pedestrians))
            for tick in range(1200):
                phase=("vehicle_green","vehicle_yellow","all_red","pedestrian_green","pedestrian_flashing","all_red")[(tick//200)%6]
                signal={"vehicle_go":phase=="vehicle_green","pedestrian_walk":phase=="pedestrian_green"}
                service._advance_vehicles_locked(.05,phase)
                service._advance_pedestrians_locked(.05,phase)
                benchmark._advance_vehicles(.05,tick*.05,signal)
                benchmark._advance_pedestrians(.05,tick*.05,signal)
                self.assertEqual(state(service._vehicles,service._pedestrians),
                                 state(benchmark.vehicles,benchmark.pedestrians))
            service.set_simulation(False)

    def test_actual_legacy_agents(self):
        from app.services.camera_frames import CameraFrameService
        def run(times, seed):
            current = [0.0]
            service = CameraFrameService(simulation_seed=seed, simulation_monotonic=lambda: current[0])
            # Fixed synthetic phase input isolates movement repeatability; no external observations.
            phase = {"phase": "vehicle_green", "vehicle_go": True, "pedestrian_walk": False,
                     "seconds_remaining": 12, "base_cycle_seconds": 34, "mode": "fixed",
                     "active_profile": "fixture", "active_rules": []}
            with patch.object(service, "_simulation_signal_state_locked", return_value=phase):
                service.set_simulation(True)
                for now in times:
                    current[0] = now
                    service.simulation_scene_for("simulation_camera")
                scene = service.simulation_scene_for("simulation_camera")
                other = service.simulation_scene_for("simulation_camera_d")
                self.assertEqual(scene["vehicles"], other["vehicles"])
                self.assertEqual(scene["pedestrians"], other["pedestrians"])
                service.configure_simulation(paused=True)
                current[0] += 10
                self.assertEqual(service.simulation_scene_for("simulation_camera")["simulation_time_seconds"], scene["simulation_time_seconds"])
                service.set_simulation(False)
                self.assertIsNone(service.simulation_scene_for("simulation_camera"))
                return scene["vehicles"], scene["pedestrians"], scene["simulation_time_seconds"]

        a = run([i / 100 for i in range(1, 101)], 42)
        b = run([0.031, 0.179, 0.263, 0.999, 1.0], 42)
        self.assertEqual(a, b)
        self.assertNotEqual(a, run([1.0], 43))


if __name__ == "__main__":
    unittest.main()
