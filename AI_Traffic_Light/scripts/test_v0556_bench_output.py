"""Deterministic fake-only bench output regressions; no physical hardware."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/pc-studio/backend"))
from app.services.bench_output import BenchOutputController, FakeBenchAdapter, DEMO_CAPABILITY, MAX_LEASE_MS


class Clock:
    now = 0.0

    def __call__(self):
        return self.now


class BenchTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.adapter = FakeBenchAdapter(self.clock)
        self.adapter.connect()
        self.controller = BenchOutputController(enabled=True, clock=self.clock, adapter=self.adapter)

    def arm(self):
        self.assertTrue(self.controller.arm(authorized=True))

    def assert_off(self):
        status = self.controller.status()
        self.assertFalse(status["active"])
        self.assertFalse(status["armed"])
        self.assertFalse(status["physical_output_allowed"])
        self.assertFalse(self.adapter.active)

    def test_disabled_and_authorization(self):
        disabled = BenchOutputController(adapter=self.adapter, clock=self.clock)
        self.assertFalse(disabled.arm(authorized=True))
        self.assertIsNone(disabled.request(DEMO_CAPABILITY, 100))
        self.assertFalse(self.controller.arm(authorized=False))
        self.assertFalse(self.controller.arm(authorized=1))
        self.assert_off()
        with self.assertRaises(TypeError):
            BenchOutputController(adapter=object())

    def test_bounds_and_unsupported(self):
        for capability, duration in [("traffic_signal", 100), ("lighting_output", 100),
                                     (DEMO_CAPABILITY, 0), (DEMO_CAPABILITY, MAX_LEASE_MS + 1),
                                     (DEMO_CAPABILITY, True), (DEMO_CAPABILITY, 1.5)]:
            self.arm()
            self.assertIsNone(self.controller.request(capability, duration))
            self.assert_off()

    def test_ack_and_expiry(self):
        self.arm()
        ack = self.controller.request(DEMO_CAPABILITY, 100)
        self.assertTrue(ack.accepted)
        self.assertTrue(self.controller.status()["active"])
        self.clock.now = 0.1
        self.controller.watchdog_tick()
        self.assert_off()
        self.assertIsNone(self.controller.request(DEMO_CAPABILITY, 100))
        self.assertEqual(self.controller.status()["reason"], "lease_expired")

    def test_ack_faults(self):
        for mode in ("missing", "rejected", "wrong_id", "late"):
            self.adapter.ack_mode = mode
            self.arm()
            self.assertIsNone(self.controller.request(DEMO_CAPABILITY, 100))
            self.assert_off()
            self.assertEqual(self.controller.status()["reason"], "ack_failed_or_timeout")

    def test_overlap_and_explicit_off(self):
        self.arm()
        self.assertIsNotNone(self.controller.request(DEMO_CAPABILITY, 100))
        self.assertIsNone(self.controller.request(DEMO_CAPABILITY, 100))
        self.assert_off()
        self.arm()
        self.assertIsNotNone(self.controller.request(DEMO_CAPABILITY, 100))
        self.controller.off()
        self.assert_off()

    def test_disconnect_requires_rearm(self):
        self.arm()
        self.assertIsNotNone(self.controller.request(DEMO_CAPABILITY, 100))
        self.controller.disconnect()
        self.assert_off()
        self.adapter.connect()
        self.assertIsNone(self.controller.request(DEMO_CAPABILITY, 100))
        self.assert_off()
        self.arm()
        self.assertIsNotNone(self.controller.request(DEMO_CAPABILITY, 100))
        self.adapter.disconnect()
        self.controller.watchdog_tick()
        self.assert_off()

    def test_unobserved_reconnect_requires_rearm(self):
        self.arm()
        self.adapter.disconnect()
        self.adapter.connect()
        self.assertIsNone(self.controller.request(DEMO_CAPABILITY, 100))
        self.assert_off()
        self.assertEqual(self.controller.status()["reason"], "connection_changed")

    def test_adapter_lease_expires_without_controller_tick(self):
        self.arm()
        self.assertIsNotNone(self.controller.request(DEMO_CAPABILITY, MAX_LEASE_MS))
        self.clock.now = 2.0
        self.assertFalse(self.adapter.active)
        self.assert_off()


if __name__ == "__main__":
    unittest.main()
