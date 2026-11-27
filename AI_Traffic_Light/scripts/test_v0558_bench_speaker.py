"""Offline speaker metadata regressions; no sound or physical hardware."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/pc-studio/backend"))
from app.services.bench_speaker import FakeSpeakerDemo, MAX_VOLUME_PERCENT
from app.services.bench_output import FakeBenchAdapter, MAX_LEASE_MS


class Clock:
    now = 0.0

    def __call__(self):
        return self.now


class SpeakerTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.adapter = FakeBenchAdapter(self.clock)
        self.demo = FakeSpeakerDemo(enabled=True, clock=self.clock, adapter=self.adapter)
        self.demo.connect()

    def arm(self):
        self.assertTrue(self.demo.arm(authorized=True))

    def play(self):
        return self.demo.play("demo_attention", 50, 100)

    def assert_off(self):
        state = self.demo.status()
        self.assertEqual(state["speaker_state"], "off")
        self.assertFalse(state["armed"])
        for key in ("prompt_id", "prompt_text", "volume_percent"):
            self.assertIsNone(state[key])
        for key in ("audio_playback", "physical_output_allowed", "physical_speaker_available"):
            self.assertFalse(state[key])
        self.assertFalse(self.adapter.active)

    def test_default_and_authorization(self):
        disabled = FakeSpeakerDemo(clock=self.clock)
        disabled.connect()
        self.assertFalse(disabled.arm(authorized=True))
        self.assertIsNone(disabled.play("demo_attention", 50, 100))
        self.assertFalse(disabled.status()["device_capability"]["available"])
        self.assertFalse(self.demo.arm(authorized=1))
        self.assertIsNone(self.play())
        self.assert_off()
        with self.assertRaises(TypeError):
            FakeSpeakerDemo(adapter=object())

    def test_metadata_and_expiry(self):
        self.arm()
        self.assertTrue(self.demo.play("demo_accessibility", MAX_VOLUME_PERCENT, MAX_LEASE_MS).accepted)
        state = self.demo.status()
        self.assertEqual(state["speaker_state"], "simulated_active")
        self.assertEqual(state["prompt_id"], "demo_accessibility")
        self.assertIn("Demonstration only", state["prompt_text"])
        self.assertEqual(state["volume_percent"], MAX_VOLUME_PERCENT)
        self.assertEqual(state["provenance"], "illustrative/synthetic")
        self.assertFalse(state["audio_playback"])
        self.assertFalse(state["physical_speaker_available"])
        self.clock.now = 2.0
        self.demo.watchdog_tick()
        self.assert_off()

    def test_invalid_requests(self):
        for prompt, volume, duration in [("custom speech", 50, 100), ([], 50, 100),
                                         ("demo_attention", 0, 100), ("demo_attention", 101, 100),
                                         ("demo_attention", True, 100), ("demo_attention", 1.5, 100),
                                         ("demo_attention", 50, 0), ("demo_attention", 50, 2001),
                                         ("demo_attention", 50, True)]:
            self.arm()
            self.assertIsNone(self.demo.play(prompt, volume, duration))
            self.assert_off()

    def test_overlap_and_invalid_while_active(self):
        self.arm()
        self.assertIsNotNone(self.play())
        self.assertIsNone(self.play())
        self.assert_off()
        self.arm()
        self.assertIsNotNone(self.play())
        self.assertIsNone(self.demo.play("invalid", 50, 100))
        self.assert_off()

    def test_ack_faults(self):
        for mode in ("missing", "rejected", "wrong_id", "late"):
            self.adapter.ack_mode = mode
            self.arm()
            self.assertIsNone(self.play())
            self.assert_off()

    def test_stop_disconnect_reconnect(self):
        self.arm()
        self.assertIsNotNone(self.play())
        self.demo.off()
        self.assert_off()
        self.arm()
        self.assertIsNotNone(self.play())
        self.demo.disconnect()
        self.assert_off()
        self.assertFalse(self.demo.status()["device_capability"]["available"])
        self.demo.connect()
        self.assertIsNone(self.play())
        self.assert_off()

    def test_unobserved_reconnect(self):
        self.arm()
        self.assertIsNotNone(self.play())
        self.adapter.disconnect()
        self.adapter.connect()
        self.assertIsNone(self.play())
        self.assert_off()
        self.assertEqual(self.demo.status()["reason"], "connection_changed")


if __name__ == "__main__":
    unittest.main()
