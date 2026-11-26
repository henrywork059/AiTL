"""Engine-neutral evaluation events, not live control or legacy metric replacement.

Directed normalized service gate: approach [-1,0), service [0,1),
exit [1,infinity). Vehicle passage at 0.5; pedestrian completion on observed
service-to-exit transition. A queue is an approach agent with normalized
displacement speed <= 0.01 gate lengths/s on consecutive samples.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

STEP_S = .2
STOP_SPEED = .01


@dataclass(frozen=True)
class GateObservation:
    ident: str
    kind: str
    progress: float
    x: float
    y: float
    span: float
    gate: str
    # Optional explicit adjacent-road transition from a trusted route adapter.
    entry_observed: bool = False
    # A route reset/reentry is never an observed crossing.


class GateMetrics:
    def __init__(self):
        self.tick = 0
        self.previous = {}
        self.passed = set()
        self.entered = set()
        self.wait_samples = {"vehicle": 0, "pedestrian": 0}
        self.peak_queue = {"vehicle": 0, "pedestrian": 0}
        self.passages = 0
        self.crossings = 0
        self.censored_service = 0
        self._waiting = {}
        self._completed_wait = {"vehicle": [], "pedestrian": []}
        self._censored_wait = {"vehicle": [], "pedestrian": []}

    def sample(self, tick: int, rows: list[GateObservation]) -> dict:
        if type(tick) is not int or tick != self.tick + 1:
            raise ValueError("Expected consecutive 0.2 s samples")
        current = {a.ident: a for a in rows}
        if len(current) != len(rows) or any(
            not a.ident or not a.gate or a.kind not in self.wait_samples or
            not all(math.isfinite(v) for v in (a.progress, a.x, a.y, a.span)) or a.span <= 0
            for a in rows):
            raise ValueError("Invalid gate observations")
        queues = {"vehicle": 0, "pedestrian": 0}
        waiting_now = {}
        continuous_keys = set()
        for ident, a in current.items():
            old = self.previous.get(ident)
            if old is not None and old.kind != a.kind:
                raise ValueError("Agent kind changed")
            key = (ident, a.gate)
            # Gate changes, missing samples and backwards recirculation retire
            # the visit; they cannot manufacture a passage or crossing.
            continuous = (old is not None and old.gate == a.gate and old.span == a.span and
                          a.progress >= old.progress - .25 and
                          math.hypot(a.x-old.x, a.y-old.y) <= a.span * .5)
            if not continuous:
                self.censored_service += int(key in self.entered)
                self.passed.discard(key)
                self.entered.discard(key)
            # A route fork may change the approach gate on the entry sample.
            # Require a consecutive approach observation and bounded displacement;
            # the route adapter must establish the actual adjacent-road transition.
            if (a.kind == "pedestrian" and a.entry_observed and old is not None and
                    old.progress < 0 <= a.progress < 1 and
                    math.hypot(a.x-old.x, a.y-old.y) <= a.span * .5):
                self.entered.add(key)
            if continuous:
                continuous_keys.add(key)
                speed = math.hypot(a.x-old.x, a.y-old.y) / a.span / STEP_S
                if -1 <= a.progress < 0 and -1 <= old.progress < 0 and speed <= STOP_SPEED:
                    queues[a.kind] += 1
                    prior = self._waiting.get(key)
                    waiting_now[key] = (a.kind, (prior[1] if prior else 0) + 1)
                if a.kind == "vehicle" and key not in self.passed and old.progress < .5 <= a.progress:
                    self.passages += 1
                    self.passed.add(key)
                if a.kind == "pedestrian":
                    if old.progress < 0 <= a.progress < 1:
                        self.entered.add(key)
                    if key in self.entered and 0 <= old.progress < 1 <= a.progress:
                        self.crossings += 1
                        self.entered.remove(key)
            # A completed visit may be counted again only after an explicit
            # return to approach or a discontinuity.
            if a.progress < 0:
                self.passed.discard(key)
                if key in self.entered:
                    self.entered.remove(key)
                    self.censored_service += 1
        active_keys = {(a.ident, a.gate) for a in rows}
        self.censored_service += len(self.entered - active_keys)
        self.entered.intersection_update(active_keys)
        self.passed.intersection_update(active_keys)
        for kind, count in queues.items():
            self.wait_samples[kind] += count
            self.peak_queue[kind] = max(self.peak_queue[kind], count)
        for key, (kind, count) in self._waiting.items():
            if key not in waiting_now:
                target = self._completed_wait if key in continuous_keys else self._censored_wait
                target[kind].append(count)
        self._waiting = waiting_now
        self.previous = current
        self.tick = tick
        return {"tick":tick,"t_seconds":round(tick * STEP_S, 6),
                "vehicle_queue":queues["vehicle"],"pedestrian_queue":queues["pedestrian"],
                "vehicle_passages":self.passages,"pedestrian_crossings":self.crossings}

    def waiting_episodes(self) -> dict:
        """Sampled stationary approach episodes; horizon and lost visits censored.

        An episode ends on a continuous nonqueued observation; a disappeared
        or discontinuous visit is censored, never treated as a completed wait.
        Total observed episode time equals the queue-integral agent-seconds.
        """
        result = {}
        for kind in self.wait_samples:
            completed = self._completed_wait[kind]
            censored = self._censored_wait[kind] + [
                n for k, n in self._waiting.values() if k == kind]
            result[kind] = {
                "completed_count": len(completed),
                "censored_count": len(censored),
                "completed_seconds": [round(n * STEP_S, 6) for n in completed],
                "censored_observed_seconds": [round(n * STEP_S, 6) for n in censored],
                "observed_agent_seconds": round((sum(completed) + sum(censored)) * STEP_S, 6),
            }
        return result

    def summary(self) -> dict:
        return {"samples":self.tick,"vehicle_passages":self.passages,
                "pedestrian_crossings":self.crossings,
                "vehicle_wait_agent_s":round(self.wait_samples["vehicle"] * STEP_S, 6),
                "pedestrian_wait_agent_s":round(self.wait_samples["pedestrian"] * STEP_S, 6),
                "peak_vehicle_queue":self.peak_queue["vehicle"],
                "peak_pedestrian_queue":self.peak_queue["pedestrian"],
                "censored_pedestrian_visits":self.censored_service + len(self.entered)}
