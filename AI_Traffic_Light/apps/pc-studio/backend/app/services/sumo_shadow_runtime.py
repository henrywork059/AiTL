"""Opt-in asynchronous shadow observation; never supplies live control or detections."""
from __future__ import annotations

from collections import deque
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Condition, Thread

from app.services.sumo_shadow_adapter import SumoShadowAdapter
from app.services.sumo_shadow_fixture import PHASES, generate_controlled_fixture
from app.services.sumo_shadow_process import LibsumoSession


class GeneratedSession(LibsumoSession):
    def __init__(self, seed: int):
        self._temp = TemporaryDirectory(prefix='mesh-shadow-')
        root = Path(self._temp.name)
        try:
            generate_controlled_fixture(root)
            super().__init__(root, seed, controlled=True)
        except BaseException:
            self._temp.cleanup()
            raise

    def close(self) -> None:
        try:
            super().close()
        finally:
            self._temp.cleanup()


class ShadowRuntime:
    """Single worker owns native I/O; camera owner enqueues only committed phases.

    Four 50 ms legacy steps make one 200 ms shadow step. Mixed phases grant
    all-red. A failed/overloaded generation is invalidated rather than skipping
    steps. Reset/stop invalidate publication immediately, then reap asynchronously.
    """
    def __init__(self, factory=GeneratedSession, *, max_backlog: int = 100):
        self._factory = factory
        self._max_backlog = max_backlog
        self._cv = Condition()
        self._events = deque()
        self._generation = 0
        self._thread: Thread | None = None
        self._closed = False
        self._state = 'idle'
        self._reason = None
        self._snapshot = None
        self._permission = None
        self._phases = []
        self._legacy_steps = 0
        self._requested_phase = None

    def _invalidate_locked(self, state: str, reason=None) -> None:
        self._generation += 1
        self._events.clear()
        self._phases.clear()
        self._snapshot = self._permission = self._requested_phase = None
        self._legacy_steps = 0
        self._state, self._reason = state, reason

    def reset(self, seed: int) -> None:
        with self._cv:
            if self._closed:
                return
            self._invalidate_locked('starting')
            if self._thread is None:
                self._thread = Thread(target=self._run, name='mesh-sumo-shadow', daemon=True)
                try:
                    self._thread.start()
                except Exception:
                    self._thread = None
                    self._invalidate_locked('unavailable', 'worker_start_failed')
                    return
            self._events.append((self._generation, 'reset', seed))
            self._cv.notify()

    def observe(self, phase: str) -> None:
        with self._cv:
            if self._state not in ('starting', 'running') or self._closed:
                return
            self._legacy_steps += 1
            self._phases.append(phase if phase in PHASES else 'all_red')
            if len(self._phases) != 4:
                return
            permission = self._phases[0] if len(set(self._phases)) == 1 else 'all_red'
            self._phases.clear()
            if len(self._events) >= self._max_backlog:
                self._invalidate_locked('unavailable', 'backlog_exceeded')
                self._events.append((self._generation, 'stop', None))
            else:
                self._events.append((self._generation, 'step', permission))
            self._cv.notify()

    def stop(self) -> None:
        with self._cv:
            if self._closed:
                return
            self._invalidate_locked('idle')
            if self._thread is not None:
                self._events.append((self._generation, 'stop', None))
                self._cv.notify()

    def close(self) -> None:
        with self._cv:
            self._closed = True
            self._invalidate_locked('idle')
            thread = self._thread
            if thread is not None:
                self._events.append((self._generation, 'close', None))
                self._cv.notify()
        if thread is not None:
            thread.join(timeout=60)
            if thread.is_alive():
                raise RuntimeError('Shadow worker did not stop')

    def status(self) -> dict:
        with self._cv:
            snap = self._snapshot
            result = {'status': self._state, 'reason': self._reason,
                      'provenance': 'synthetic_sumo_shadow', 'generation': self._generation,
                      'legacy_steps': self._legacy_steps, 'requested_phase': self._requested_phase,
                      'applied_permission': self._permission}
        result['snapshot'] = None if snap is None else {
            'seed': snap.seed, 'tick': snap.tick, 'time_s': snap.time_s,
            'agents': [dict(asdict(a), id=a.id) for a in snap.agents]}
        return result

    def _run(self) -> None:
        session = None
        # The wrapped factory captures the session without sharing native handles.
        def factory(seed):
            nonlocal session
            session = self._factory(seed)
            return session
        adapter = SumoShadowAdapter(factory)
        while True:
            with self._cv:
                self._cv.wait_for(lambda: bool(self._events))
                generation, action, arg = self._events.popleft()
            try:
                if action in ('stop', 'close'):
                    adapter.shutdown()
                    session = None
                    if action == 'close':
                        return
                    continue
                if action == 'reset':
                    snap = adapter.reset(seed=arg)
                    permission = None
                else:
                    if session is None:
                        raise RuntimeError('Missing shadow session')
                    session.set_phase(arg)
                    snap = adapter.step()
                    permission = session.last_permission
                with self._cv:
                    if generation == self._generation:
                        self._snapshot, self._permission = snap, permission
                        self._requested_phase = arg if action == 'step' else None
                        self._state = 'running'
            except Exception:
                try:
                    adapter.shutdown()
                except Exception:
                    pass
                session = None
                with self._cv:
                    if generation == self._generation:
                        self._invalidate_locked('unavailable', 'engine_failure')
                if action == 'close':
                    return
