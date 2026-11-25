"""Offline synthetic lighting regressions; no physical hardware."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/pc-studio/backend"))
from app.services.bench_lighting import FakeLightingDemo
from app.services.bench_output import FakeBenchAdapter, MAX_LEASE_MS


class Clock:
    now = 0.0

    def __call__(self):
        return self.now


class LightingTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.adapter = FakeBenchAdapter(self.clock)
        self.demo = FakeLightingDemo(enabled=True, clock=self.clock, adapter=self.adapter)
        self.demo.connect()

    def assert_off(self):
        state = self.demo.status()
        self.assertEqual(state["lighting_state"], "off")
        self.assertFalse(state["armed"])
        self.assertFalse(state["physical_output_allowed"])
        self.assertFalse(state["physical_lighting_available"])
        self.assertFalse(self.adapter.active)

    def arm(self):
        self.assertTrue(self.demo.arm(authorized=True))

    def test_disabled_default_and_authorization(self):
        disabled = FakeLightingDemo(clock=self.clock)
        disabled.connect()
        self.assertFalse(disabled.arm(authorized=True))
        self.assertIsNone(disabled.pulse(100))
        self.assertFalse(disabled.status()["device_capability"]["available"])
        self.assertFalse(self.demo.arm(authorized=1))
        self.assertIsNone(self.demo.pulse(100))
        self.assert_off()
        with self.assertRaises(TypeError):
            FakeLightingDemo(adapter=object())

    def test_binary_pulse_and_provenance(self):
        self.arm()
        self.assertTrue(self.demo.pulse(MAX_LEASE_MS).accepted)
        state = self.demo.status()
        self.assertEqual(state["lighting_state"], "on")
        self.assertEqual(state["capability"], "synthetic_lighting")
        self.assertEqual(state["provenance"], "illustrative/synthetic")
        self.assertEqual(state["device_capability"]["support"], "simulation-only")
        self.assertFalse(state["physical_lighting_available"])
        self.clock.now = 2.0
        self.assertFalse(self.adapter.active)
        self.assert_off()

    def test_invalid_duration_and_overlap(self):
        for duration in (0, -1, MAX_LEASE_MS + 1, True, 1.5, "100"):
            self.arm()
            self.assertIsNone(self.demo.pulse(duration))
            self.assert_off()
        self.arm()
        self.assertIsNotNone(self.demo.pulse(100))
        self.assertIsNone(self.demo.pulse(100))
        self.assert_off()

    def test_ack_faults(self):
        for mode in ("missing", "rejected", "wrong_id", "late"):
            self.adapter.ack_mode = mode
            self.arm()
            self.assertIsNone(self.demo.pulse(100))
            self.assert_off()

    def test_off_and_disconnect(self):
        self.arm()
        self.assertIsNotNone(self.demo.pulse(100))
        self.demo.off()
        self.assert_off()
        self.arm()
        self.assertIsNotNone(self.demo.pulse(100))
        self.demo.disconnect()
        self.assert_off()
        self.assertFalse(self.demo.status()["device_capability"]["available"])
        self.demo.connect()
        self.assertIsNone(self.demo.pulse(100))
        self.assert_off()

    def test_unobserved_reconnect_disarms(self):
        self.arm()
        self.adapter.disconnect()
        self.adapter.connect()
        self.assertIsNone(self.demo.pulse(100))
        self.assert_off()
        self.assertEqual(self.demo.status()["reason"], "connection_changed")


if __name__ == "__main__":
    unittest.main()
