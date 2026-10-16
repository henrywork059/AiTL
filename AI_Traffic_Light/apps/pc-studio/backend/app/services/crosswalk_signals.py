"""Independent simulation signal runtimes per saved crosswalk.

Network links are topology only; no neighbour commands or physical actuation.
"""
from __future__ import annotations

import json
from pathlib import Path
from threading import RLock
import time
from typing import Any, Callable

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.services.crosswalks import CrosswalkService, crosswalk_service
from app.services.signal_rules import (
    PROJECT_ROOT, SignalRulesService, signal_rules_service,
)


class CrosswalkSignalService:
    def __init__(
        self,
        *,
        crosswalks: CrosswalkService | None = None,
        shared_rules: SignalRulesService | None = None,
        clock: Callable[[], float] = time.monotonic,
        history_root: Path | None = None,
    ) -> None:
        self._crosswalks = crosswalks or crosswalk_service
        self._rules = shared_rules or signal_rules_service
        self._clock = clock
        self._history_root = history_root or PROJECT_ROOT / "outputs" / "signal_rules" / "crosswalks"
        self._lock = RLock()
        self._controllers: dict[str, SignalRulesService] = {}
        self._rules_key: str | None = None
        self._last_tick: float | None = None
        self._elapsed_seconds = 0.0
        self._running = False

    def _stop_locked(self) -> None:
        self._controllers.clear()
        self._rules_key = None
        self._last_tick = None
        self._elapsed_seconds = 0.0
        self._running = False

    def status(self, *, simulation_enabled: bool, simulation_paused: bool = False) -> dict[str, Any]:
        """Advance each controller on one simulation clock; never copy another crosswalk's phase."""
        config = self._crosswalks.get()
        crosswalks = config["crosswalks"]
        links = config.get("network", {}).get("links", [])
        neighbors: dict[str, set[str]] = {item["id"]: set() for item in crosswalks}
        for link in links:
            source, destination = link["source_crosswalk_id"], link["destination_crosswalk_id"]
            if source in neighbors and destination in neighbors:
                neighbors[source].add(destination)
                neighbors[destination].add(source)

        with self._lock:
            if not simulation_enabled:
                self._stop_locked()
                return self._response(crosswalks, neighbors, False, False, {})

            now = self._clock()
            settings_key = json.dumps(self._rules.get_config(), sort_keys=True)
            if not self._running or settings_key != self._rules_key:
                self._stop_locked()
                self._running = True
                self._rules_key = settings_key
            if self._last_tick is not None and not simulation_paused:
                self._elapsed_seconds += max(0.0, now - self._last_tick)
            self._last_tick = now

            valid_ids = {item["id"] for item in crosswalks}
            for stale_id in set(self._controllers) - valid_ids:
                del self._controllers[stale_id]
            states: dict[str, dict[str, Any]] = {}
            for item in crosswalks:
                crosswalk_id = item["id"]
                if crosswalk_id not in self._controllers:
                    # Same user-configured rule profile; entirely separate phase, memory and decisions.
                    self._controllers[crosswalk_id] = SignalRulesService(
                        config_path=self._rules.config_path,
                        history_path=self._history_root / (crosswalk_id + ".jsonl"),
                    )
                state = self._controllers[crosswalk_id].signal_state(self._elapsed_seconds)
                states[crosswalk_id] = state
            return self._response(crosswalks, neighbors, True, simulation_paused, states)

    @staticmethod
    def _response(
        crosswalks: list[dict[str, Any]],
        neighbors: dict[str, set[str]],
        running: bool,
        paused: bool,
        states: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "simulation_only": True,
            "simulation_enabled": running,
            "simulation_paused": paused if running else False,
            "coordination_enabled": False,
            "movement_conflicts_configured": False,
            "hardware_actuation_enabled": False,
            "crosswalks": {
                item["id"]: {
                    "crosswalk_id": item["id"],
                    "controller_id": item["id"],
                    "signal": states.get(item["id"]),
                    "status": "paused" if running and paused else "simulated" if running else "unavailable",
                    "neighbors": sorted(neighbors[item["id"]]),
                    "observation_provenance": "unavailable",
                    "coordination_reason": "Network edges do not specify conflicting movements.",
                }
                for item in crosswalks
            },
        }

    def observe(self, crosswalk_id: str, observation: dict[str, Any]) -> None:
        """Future camera/region adapter: update only one existing simulation controller."""
        with self._lock:
            controller = self._controllers.get(crosswalk_id) if self._running else None
            if controller is None:
                raise AppError(
                    ErrorCode.CROSSWALK_INVALID,
                    "The crosswalk has no active simulated controller.",
                    status_code=409,
                )
            controller.observe(observation)

    def set_test_inputs(self, crosswalk_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
        """Allow independent, simulation-only test inputs without changing global test state."""
        with self._lock:
            controller = self._controllers.get(crosswalk_id) if self._running else None
            if controller is None or self._rules.get_config()["mode"] != "test":
                raise AppError(
                    ErrorCode.CROSSWALK_INVALID,
                    "Enable simulation and Test mode before setting crosswalk test inputs.",
                    status_code=409,
                )
            return controller.set_test_inputs(inputs)


crosswalk_signal_service = CrosswalkSignalService()
