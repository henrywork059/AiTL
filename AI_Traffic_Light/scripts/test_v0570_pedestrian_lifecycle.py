"""Deterministic existing synthetic pedestrian movement checks; no signal policy changes."""
from pathlib import Path
import sys
import unittest
import random
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/pc-studio/backend"))
from app.services.camera_frames import (CameraFrameService, _SimPedestrian,
    TOP_PEDESTRIAN_WAIT_Y, BOTTOM_PEDESTRIAN_WAIT_Y, FRAME_HEIGHT)

class PedestrianLifecycleTests(unittest.TestCase):
    def fixture(self, direction, y, speed=90):
        person = _SimPedestrian(x=620, y=float(y), speed=float(speed), direction=direction, color=(10,20,30))
        owner = SimpleNamespace(_pedestrians=[person], _simulation_rng=random.Random(42))
        return owner, person

    def step(self, owner, phase, n=1):
        for _ in range(n):
            CameraFrameService._advance_pedestrians_locked(owner, .05, phase)

    def test_wait_walk_clear_both_directions(self):
        for direction, curb in [(1, TOP_PEDESTRIAN_WAIT_Y), (-1, BOTTOM_PEDESTRIAN_WAIT_Y)]:
            with self.subTest(direction=direction):
                owner, p = self.fixture(direction, curb - direction*20)
                self.step(owner, "vehicle_green", 20)
                self.assertEqual(p.y, curb)
                for phase in ["pedestrian_flashing", "all_red", "vehicle_green"]:
                    self.step(owner, phase, 10)
                    self.assertEqual(p.y, curb)
                self.step(owner, "pedestrian_green", 10)
                self.assertGreater((p.y-curb)*direction, 0)
                before = p.y
                self.step(owner, "pedestrian_flashing", 10)
                self.assertAlmostEqual((p.y-before)*direction, 45)

    def test_slow_clearance_observation(self):
        for direction, curb in [(1, TOP_PEDESTRIAN_WAIT_Y), (-1, BOTTOM_PEDESTRIAN_WAIT_Y)]:
            owner, slow = self.fixture(direction, curb, 30)
            normal_owner, normal = self.fixture(direction, curb, 90)
            self.step(owner, "pedestrian_green", 20)
            self.step(normal_owner, "pedestrian_green", 20)
            self.assertAlmostEqual((slow.y-curb)*direction, 30)
            self.assertAlmostEqual((normal.y-curb)*direction, 90)
            before = slow.y
            self.step(owner, "pedestrian_flashing", 20)
            self.assertAlmostEqual((slow.y-before)*direction, 30)

    def test_seeded_reentry(self):
        for direction, y in [(1, FRAME_HEIGHT+24), (-1, 21)]:
            owner, p = self.fixture(direction, y)
            other, q = self.fixture(direction, y)
            self.step(owner, "pedestrian_green")
            self.step(other, "pedestrian_green")
            self.assertEqual(p.y, q.y)
            if direction > 0:
                self.assertTrue(28 <= p.y <= 70)
            else:
                self.assertTrue(FRAME_HEIGHT-10 <= p.y <= FRAME_HEIGHT+26)
            before = p.y
            self.step(owner, "vehicle_green")
            self.assertGreater((p.y-before)*direction, 0)

if __name__ == "__main__":
    unittest.main()
