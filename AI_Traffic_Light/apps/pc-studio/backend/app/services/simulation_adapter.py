"""Fixed-step scheduling for the existing synthetic scene; no I/O or threads."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import math

STEP_NS = 50_000_000
MAX_CATCHUP_NS = 2_000_000_000
NS_PER_SECOND = 1_000_000_000


def _ns(seconds: float) -> int:
    if not math.isfinite(seconds) or seconds < 0:
        raise ValueError("Simulation time must be finite and nonnegative.")
    return round(seconds * NS_PER_SECOND)


@dataclass(frozen=True)
class SimulationClockSnapshot:
    time_s: float
    paused: bool
    seed: int


class LegacySimulationAdapter:
    """Schedule the existing world callbacks under their owner's lock.

    Only complete fixed steps advance time. Rendering and snapshots never
    contribute fractional steps; excess catch-up beyond two seconds is dropped.
    The adapter does not own agents, policy, frame identity or transport.
    """

    def __init__(self, advance_world: Callable[[float], None]) -> None:
        self._advance_world = advance_world
        self._clock_ns = 0
        self._remainder_ns = 0
        self._anchor_ns: int | None = None
        self._paused = False
        self._seed = 0

    @property
    def time_s(self) -> float:
        return self._clock_ns / NS_PER_SECOND

    @property
    def paused(self) -> bool:
        return self._paused

    def reset(self, *, seed: int, now: float, paused: bool = False) -> None:
        self._clock_ns = self._remainder_ns = 0
        self._anchor_ns = _ns(now)
        self._paused = paused
        self._seed = seed

    def stop(self) -> None:
        self._anchor_ns = None
        self._remainder_ns = 0
        self._paused = False

    def set_paused(self, paused: bool, now: float) -> None:
        # Preserve the committed clock and substep remainder, not time spent paused.
        self._anchor_ns = _ns(now)
        self._paused = paused

    def reanchor_time(self, seconds: float) -> None:
        """Private compatibility seam for existing controlled phase fixtures."""
        self._clock_ns = _ns(seconds)
        self._remainder_ns = 0

    def snapshot(self) -> SimulationClockSnapshot:
        return SimulationClockSnapshot(self.time_s, self.paused, self._seed)

    def step(self, elapsed_s: float) -> int:
        return self._step_ns(_ns(elapsed_s))

    def sync(self, now: float) -> int:
        current = _ns(now)
        previous = self._anchor_ns
        if previous is not None and current < previous:
            return 0
        self._anchor_ns = current
        return self._step_ns(current - previous) if previous is not None else 0

    def _step_ns(self, elapsed_ns: int) -> int:
        if self._paused:
            return 0
        self._remainder_ns += min(elapsed_ns, MAX_CATCHUP_NS)
        steps = self._remainder_ns // STEP_NS
        for _ in range(steps):
            self._remainder_ns -= STEP_NS
            self._clock_ns += STEP_NS
            self._advance_world(STEP_NS / NS_PER_SECOND)
        return steps
