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
from app.services.crosswalk_observations import crosswalk_observation
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
        self._controller_mode: str | None = None
        self._virtual_preview_enabled = False
        self._last_virtual_update = 0.0
        self._frame_signatures: dict[str, tuple[tuple[Any, ...], ...]] = {}
        self._observation_meta: dict[str, dict[str, Any]] = {}
        self._emergency_evidence: dict[str, tuple[float, int]] = {}
        self._active_routes: set[str] = set()
        self._priority_requests: dict[str, dict[str, Any]] = {}

    def _stop_locked(self) -> None:
        self._controllers.clear()
        self._rules_key = None
        self._last_tick = None
        self._elapsed_seconds = 0.0
        self._running = False
        self._controller_mode = None
        self._frame_signatures.clear()
        self._observation_meta.clear()
        self._emergency_evidence.clear()
        self._active_routes.clear()
        self._priority_requests.clear()

    def status(self, *, simulation_enabled: bool, simulation_paused: bool = False,
               virtual_preview: bool | None = None) -> dict[str, Any]:
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
            if virtual_preview is not None:
                self._virtual_preview_enabled = virtual_preview
                self._last_virtual_update = time.monotonic()
            if not simulation_enabled and (
                not self._virtual_preview_enabled
                or time.monotonic() - self._last_virtual_update > 6.0
            ):
                self._virtual_preview_enabled = False
                self._stop_locked()
                return self._response(crosswalks, neighbors, False, False, {}, False)

            now = self._clock()
            settings_key = json.dumps(self._rules.get_config(), sort_keys=True)
            mode = "simulation" if simulation_enabled else "virtual"
            if not self._running or settings_key != self._rules_key or mode != self._controller_mode:
                self._stop_locked()
                self._running = True
                self._rules_key = settings_key
                self._controller_mode = mode
            if self._last_tick is not None and not simulation_paused:
                self._elapsed_seconds += max(0.0, now - self._last_tick)
            self._last_tick = now

            valid_ids = {item["id"] for item in crosswalks}
            for stale_id in set(self._controllers) - valid_ids:
                del self._controllers[stale_id]
                self._frame_signatures.pop(stale_id, None)
                self._observation_meta.pop(stale_id, None)
                self._emergency_evidence.pop(stale_id, None)
                self._priority_requests.pop(stale_id, None)
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
            return self._response(
                crosswalks, neighbors, True, simulation_paused, states, simulation_enabled,
                emergency_routes_enabled=any(link.get("emergency_route", "off") != "off" for link in links),
            )

    def _response(
        self,
        crosswalks: list[dict[str, Any]],
        neighbors: dict[str, set[str]],
        running: bool,
        paused: bool,
        states: dict[str, dict[str, Any]],
        camera_simulation_enabled: bool,
        *,
        emergency_routes_enabled: bool = False,
    ) -> dict[str, Any]:
        return {
            "simulation_only": True,
            "simulation_enabled": camera_simulation_enabled,
            "virtual_preview_enabled": running and not camera_simulation_enabled,
            "simulation_paused": paused if running else False,
            "coordination_enabled": running and emergency_routes_enabled,
            "emergency_routes_enabled": emergency_routes_enabled,
            "movement_conflicts_configured": False,
            "hardware_actuation_enabled": False,
            "crosswalks": {
                item["id"]: {
                    "crosswalk_id": item["id"],
                    "controller_id": item["id"],
                    "signal": states.get(item["id"]),
                    "status": "paused" if running and paused else "simulated" if running and camera_simulation_enabled else "virtual" if running else "unavailable",
                    "neighbors": sorted(neighbors[item["id"]]),
                    **(self._observation_meta.get(item["id"], {
                        "observation_provenance": "unavailable", "camera_sources": [],
                        "camera_coverage": "unavailable", "region_class_counts": {},
                    }) if running else {
                        "observation_provenance": "unavailable", "camera_sources": [],
                        "camera_coverage": "unavailable", "region_class_counts": {},
                    }),
                    "emergency_priority": (
                        self._priority_requests[item["id"]]
                        if running and item["id"] in self._priority_requests
                        and self._clock() < self._priority_requests[item["id"]]["expires_at"]
                        else None
                    ),
                    "coordination_reason": (
                        "Configured emergency corridor; virtual protected vehicle service only."
                        if emergency_routes_enabled else "No emergency routes configured."
                    ),
                }
                for item in crosswalks
            },
        }

    def ingest_camera_results(
        self, results: dict[str, dict[str, Any]], *, simulation_enabled: bool,
        simulation_paused: bool = False, model_id: str | None = None,
        virtual_preview: bool = False,
    ) -> None:
        """Automatically route fresh camera detections to only their assigned crossing.

        Runs from the inference worker, independent of whether Network is open.
        No real-world signal output and no crosswalk-to-crosswalk commands.
        """
        self.status(simulation_enabled=simulation_enabled, simulation_paused=simulation_paused,
                    virtual_preview=virtual_preview)
        if not simulation_enabled and not virtual_preview:
            return
        crosswalks = self._crosswalks.get()["crosswalks"]
        with self._lock:
            for crosswalk in crosswalks:
                crosswalk_id = crosswalk["id"]
                controller = self._controllers.get(crosswalk_id)
                if controller is None:
                    continue
                observation, signature, meta = crosswalk_observation(
                    crosswalk, results, model_id=model_id,
                )
                self._observation_meta[crosswalk_id] = meta
                if observation is None:
                    self._emergency_evidence.pop(crosswalk_id, None)
                    if crosswalk_id in self._frame_signatures:
                        controller.clear_observation()
                        self._frame_signatures.pop(crosswalk_id, None)
                elif self._frame_signatures.get(crosswalk_id) != signature:
                    controller.observe(observation)
                    self._frame_signatures[crosswalk_id] = signature
                    ambulance_observed = any(
                        float(classes.get("ambulance", 0)) > 0
                        for classes in meta["region_class_counts"].values()
                    )
                    if ambulance_observed:
                        first, samples = self._emergency_evidence.get(crosswalk_id, (self._clock(), 0))
                        self._emergency_evidence[crosswalk_id] = (first, samples + 1)
                    else:
                        self._emergency_evidence.pop(crosswalk_id, None)

            # Only a user-specified directed one-hop route can request a neighbour's
            # virtual vehicle phase. All-red/pedestrian transitions remain local.
            now = self._clock()
            eligible: set[str] = set()
            for link in self._crosswalks.get().get("network", {}).get("links", []):
                direction = link.get("emergency_route", "off")
                if direction == "source_to_destination":
                    source_id, target_id = link["source_crosswalk_id"], link["destination_crosswalk_id"]
                elif direction == "destination_to_source":
                    source_id, target_id = link["destination_crosswalk_id"], link["source_crosswalk_id"]
                else:
                    continue
                first, samples = self._emergency_evidence.get(source_id, (now, 0))
                if samples < 2 or now - first < 1.0:
                    continue
                eligible.add(link["id"])
                if link["id"] in self._active_routes:
                    continue
                controller = self._controllers.get(target_id)
                if controller and controller.request_simulated_emergency_vehicle(self._elapsed_seconds, source_id):
                    self._active_routes.add(link["id"])
                    self._priority_requests[target_id] = {
                        "source_crosswalk_id": source_id,
                        "reason": "Confirmed ambulance class; bounded protected vehicle green requested.",
                        "expires_at": now + 30.0,
                    }
            self._active_routes.intersection_update(eligible)

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
