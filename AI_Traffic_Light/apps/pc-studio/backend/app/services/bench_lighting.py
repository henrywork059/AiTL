"""Synthetic binary lighting demo; never a physical lighting driver."""
from __future__ import annotations

from time import monotonic
from typing import Callable

from .bench_output import (
    BenchAck, BenchOutputController, DEMO_CAPABILITY, FakeBenchAdapter, MAX_LEASE_MS,
)


class FakeLightingDemo:
    """Translate a single synthetic lighting pulse into the existing fake lease.

    No brightness, electrical parameters, flashing patterns or live integration.
    The controller remains the sole owner of arming, lease and fault state.
    """

    def __init__(self, *, enabled: bool = False, clock: Callable[[], float] = monotonic,
                 adapter: FakeBenchAdapter | None = None) -> None:
        self._adapter = adapter if adapter is not None else FakeBenchAdapter(clock)
        self._controller = BenchOutputController(enabled=enabled, clock=clock, adapter=self._adapter)

    def connect(self) -> None:
        self._controller.off()
        self._adapter.connect()

    def arm(self, *, authorized: bool = False) -> bool:
        return self._controller.arm(authorized=authorized)

    def pulse(self, duration_ms: int) -> BenchAck | None:
        return self._controller.request(DEMO_CAPABILITY, duration_ms)

    def off(self) -> None:
        self._controller.off()

    def disconnect(self) -> None:
        self._controller.disconnect()

    def watchdog_tick(self) -> None:
        self._controller.watchdog_tick()

    def status(self) -> dict:
        state = self._controller.status()
        return {**state, "capability": "synthetic_lighting",
                "lighting_state": "on" if state["active"] else "off",
                "max_duration_ms": MAX_LEASE_MS,
                "device_capability": {"direction": "output", "support": "simulation-only",
                                      "available": state["enabled"] and state["connected"]},
                "physical_lighting_available": False}
