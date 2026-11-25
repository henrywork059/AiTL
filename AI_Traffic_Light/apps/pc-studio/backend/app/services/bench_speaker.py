"""Synthetic speaker metadata only; no audio generation or physical driver."""
from __future__ import annotations

from threading import RLock
from time import monotonic
from typing import Callable

from .bench_output import BenchAck, BenchOutputController, DEMO_CAPABILITY, FakeBenchAdapter, MAX_LEASE_MS

PROMPTS = {
    "demo_attention": "Demonstration only: attention notice.",
    "demo_accessibility": "Demonstration only: accessible guidance notice.",
}
MAX_VOLUME_PERCENT = 100  # Synthetic normalized setting, not acoustic output.


class FakeSpeakerDemo:
    """Delegate arming and leases to the existing controller; never play sound."""

    def __init__(self, *, enabled: bool = False, clock: Callable[[], float] = monotonic,
                 adapter: FakeBenchAdapter | None = None) -> None:
        self._adapter = adapter if adapter is not None else FakeBenchAdapter(clock)
        self._controller = BenchOutputController(enabled=enabled, clock=clock, adapter=self._adapter)
        self._lock = RLock()
        self._prompt: str | None = None
        self._volume: int | None = None

    def _clear(self) -> None:
        self._prompt = None
        self._volume = None

    def connect(self) -> None:
        with self._lock:
            self.off()
            self._adapter.connect()

    def arm(self, *, authorized: bool = False) -> bool:
        with self._lock:
            self._clear()
            return self._controller.arm(authorized=authorized)

    def play(self, prompt_id: str, volume_percent: int, duration_ms: int) -> BenchAck | None:
        with self._lock:
            if (type(prompt_id) is not str or prompt_id not in PROMPTS
                    or type(volume_percent) is not int or not 1 <= volume_percent <= MAX_VOLUME_PERCENT):
                self.off()
                return None
            ack = self._controller.request(DEMO_CAPABILITY, duration_ms)
            self._clear()
            if ack is not None:
                self._prompt, self._volume = prompt_id, volume_percent
            return ack

    def off(self) -> None:
        with self._lock:
            self._controller.off()
            self._clear()

    def disconnect(self) -> None:
        with self._lock:
            self._controller.disconnect()
            self._clear()

    def watchdog_tick(self) -> None:
        self.status()

    def status(self) -> dict:
        with self._lock:
            state = self._controller.status()
            if not state["active"]:
                self._clear()
            return {**state, "capability": "synthetic_speaker",
                    "speaker_state": "simulated_active" if state["active"] else "off",
                    "prompt_id": self._prompt, "prompt_text": PROMPTS.get(self._prompt),
                    "volume_percent": self._volume, "max_volume_percent": MAX_VOLUME_PERCENT,
                    "max_duration_ms": MAX_LEASE_MS, "audio_playback": False,
                    "device_capability": {"direction": "output", "support": "simulation-only",
                                          "available": state["enabled"] and state["connected"]},
                    "physical_speaker_available": False}
