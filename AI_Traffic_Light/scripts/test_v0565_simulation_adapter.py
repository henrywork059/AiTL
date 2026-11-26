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
