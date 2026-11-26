"""Isolated native projection lifecycle. No camera, capture or signal authority."""
from __future__ import annotations

from app.services.sumo_projection import NativeProjection, Projection
from app.services.sumo_shadow_adapter import SumoShadowAdapter
from app.services.sumo_shadow_fixture import PHASES
from app.services.sumo_shadow_runtime import GeneratedSession


class NativeProjectionSession:
    def __init__(self, factory=GeneratedSession):
        self._factory = factory
        self._session = None
        self._projection = None
        self._generation = 0
        self._adapter = SumoShadowAdapter(self._open)

    def _open(self, seed):
        session = self._factory(seed)
        try:
            self._projection = NativeProjection(Projection.load(session.network_path), self._generation)
        except BaseException:
            session.close()
            raise
        self._session = session
        return session

    def reset(self, seed: int):
        self.close()
        self._generation += 1
        try:
            self._adapter.reset(seed=seed)
            return self.read()
        except BaseException:
            self.close()
            raise

    def read(self):
        snapshot = self._adapter.snapshot()
        if snapshot is None or self._projection is None:
            return None
        try:
            return self._projection.render(snapshot)
        except BaseException:
            self.close()
            raise

    def step(self, phase: str):
        if not isinstance(phase, str) or phase not in PHASES or self._session is None:
            raise ValueError("Invalid native projection phase or inactive session")
        try:
            self._session.set_phase(phase)
            self._adapter.step()
            return self.read()
        except BaseException:
            self.close()
            raise

    def pause(self, paused: bool):
        self._adapter.set_paused(paused)
        return self.read()

    def close(self):
        self._projection = self._session = None
        self._adapter.shutdown()
