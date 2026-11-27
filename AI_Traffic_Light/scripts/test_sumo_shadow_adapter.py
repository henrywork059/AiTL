"""Offline shadow contract regressions; no optional package required."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'apps/pc-studio/backend'))
from app.services.sumo_shadow_adapter import ShadowAgent, SumoShadowAdapter


class Session:
    def __init__(self, seed):
        self.seed = seed
        self.tick = 0
        self.closed = False
        self.fail = False
        self.invalid = False

    def advance(self):
        if self.fail:
            raise RuntimeError('lost engine')
        self.tick += 1

    def agents(self):
        x = float('nan') if self.invalid else self.seed + self.tick / 5
        return (ShadowAgent('vehicle', '0', x, 1, 1, 'WC'),
                ShadowAgent('pedestrian', '0', x, 2, 1, 'WC'))

    def close(self):
        self.closed = True


class Tests(unittest.TestCase):
    def setUp(self):
        self.sessions = []
        def factory(seed):
            self.sessions.append(Session(seed))
            return self.sessions[-1]
        self.adapter = SumoShadowAdapter(factory)
        self.addCleanup(self.adapter.shutdown)

    def test_repeatability_pause_and_identity(self):
        self.adapter.reset(seed=42)
        a = self.adapter.step(5)
        self.assertEqual(a.time_s, 1)
        self.assertEqual([p.id for p in a.agents], ['sumo:pedestrian:0', 'sumo:vehicle:0'])
        self.adapter.set_paused(True)
        self.assertEqual(self.adapter.step(2).tick, 5)
        self.adapter.reset(seed=42)
        self.assertTrue(self.sessions[0].closed)
        for _ in range(5):
            b = self.adapter.step()
        self.assertEqual(a, b)
        self.adapter.set_paused(True)
        self.adapter.set_paused(False)
        self.assertEqual(self.adapter.step().tick, 6)

    def test_invalid_configuration_does_not_mutate(self):
        a = self.adapter.reset(seed=1)
        for seed in (-1, True, 2**31):
            with self.assertRaises(ValueError):
                self.adapter.reset(seed=seed)
        for steps in (0, 51, True, 0.2):
            with self.assertRaises(ValueError):
                self.adapter.step(steps)
        self.assertEqual(a, self.adapter.snapshot())

    def test_failure_clears_snapshot_and_allows_reset(self):
        for field in ('fail', 'invalid'):
            self.adapter.reset(seed=1)
            self.adapter.step()
            setattr(self.sessions[-1], field, True)
            with self.assertRaises((RuntimeError, ValueError)):
                self.adapter.step()
            self.assertTrue(self.sessions[-1].closed)
            self.assertIsNone(self.adapter.snapshot())
        self.adapter.reset(seed=1)
        self.assertEqual(self.adapter.step().tick, 1)
        self.adapter.shutdown()
        self.adapter.shutdown()
        self.assertIsNone(self.adapter.snapshot())

    def test_unavailable_factory(self):
        def missing(seed):
            raise FileNotFoundError('SUMO unavailable')
        adapter = SumoShadowAdapter(missing)
        with self.assertRaises(FileNotFoundError):
            adapter.reset(seed=42)
        self.assertIsNone(adapter.snapshot())


if __name__ == '__main__':
    unittest.main()
