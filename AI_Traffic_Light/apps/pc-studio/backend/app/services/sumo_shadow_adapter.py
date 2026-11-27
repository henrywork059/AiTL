"""Opt-in synthetic shadow clock. No camera, detector or signal authority."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import math
from typing import Protocol

STEP_S = 0.2
MAX_STEPS = 50


@dataclass(frozen=True)
class ShadowAgent:
    kind: str
    engine_id: str
    x_m: float
    y_m: float
    speed_m_s: float
    road_id: str

    @property
    def id(self) -> str:
        return f"sumo:{self.kind}:{self.engine_id}"


@dataclass(frozen=True)
class ShadowSnapshot:
    seed: int
    tick: int
    paused: bool
    agents: tuple[ShadowAgent, ...]
    provenance: str = "synthetic_sumo_shadow"

    @property
    def time_s(self) -> float:
        return self.tick / 5


class ShadowSession(Protocol):
    def advance(self) -> None: ...
    def agents(self) -> tuple[ShadowAgent, ...]: ...
    def close(self) -> None: ...


class SumoShadowAdapter:
    """Single-owner explicit stepping; a failed session cannot publish stale data.

    The injected factory must own startup/cleanup, including startup failure.
    Agent IDs are stable within a run; consumers must discard snapshots on reset.
    """

    def __init__(self, factory: Callable[[int], ShadowSession]) -> None:
        self._factory = factory
        self._session: ShadowSession | None = None
        self._snapshot: ShadowSnapshot | None = None

    def reset(self, *, seed: int) -> ShadowSnapshot:
        if type(seed) is not int or not 0 <= seed <= 2**31 - 1:
            raise ValueError("Seed must be a nonnegative 32-bit signed integer.")
        self.shutdown()
        try:
            self._session = self._factory(seed)
            self._snapshot = ShadowSnapshot(seed, 0, False, ())
            return self._snapshot
        except Exception:
            self.shutdown()
            raise

    def snapshot(self) -> ShadowSnapshot | None:
        return self._snapshot

    def set_paused(self, paused: bool) -> None:
        if type(paused) is not bool:
            raise ValueError("Pause must be boolean.")
        current = self._require_snapshot()
        self._snapshot = ShadowSnapshot(current.seed, current.tick, paused, current.agents)

    def _require_snapshot(self) -> ShadowSnapshot:
        if self._session is None or self._snapshot is None:
            raise RuntimeError("Shadow session is not running.")
        return self._snapshot

    def step(self, steps: int = 1) -> ShadowSnapshot:
        if type(steps) is not int or not 1 <= steps <= MAX_STEPS:
            raise ValueError("Step count must be an integer from 1 to 50.")
        current = self._require_snapshot()
        if current.paused:
            return current
        session = self._session
        assert session is not None
        try:
            for _ in range(steps):
                session.advance()
                agents = tuple(sorted(session.agents(), key=lambda a: a.id))
                if len({a.id for a in agents}) != len(agents) or any(
                    a.kind not in {"vehicle", "pedestrian"} or not a.engine_id or
                    not all(math.isfinite(v) for v in (a.x_m, a.y_m, a.speed_m_s)) or
                    a.speed_m_s < 0 for a in agents
                ):
                    raise ValueError("Invalid shadow agent data.")
                current = ShadowSnapshot(current.seed, current.tick + 1, False, agents)
            self._snapshot = current
            return current
        except Exception:
            self.shutdown()
            raise

    def shutdown(self) -> None:
        session, self._session = self._session, None
        self._snapshot = None
        if session is not None:
            session.close()
