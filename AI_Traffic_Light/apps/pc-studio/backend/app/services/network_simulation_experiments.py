from __future__ import annotations

from collections import deque
from copy import deepcopy
from dataclasses import dataclass
import csv
import hashlib
from io import StringIO
import json
import math
from pathlib import Path
import random
import re
import tempfile
import time
from typing import Any, Callable
import uuid

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.core.json_store import read_json, write_json_atomic
from app.core.logging_config import get_logger
from app.services.intersection_network import intersection_network_service
from app.services.signal_rules import SignalRulesService, signal_rules_service
from app.services.zones import zone_service

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_STORAGE_ROOT = PROJECT_ROOT / "outputs" / "simulation_experiments"
RUN_ID_PATTERN = re.compile(r"^netexp_[A-Za-z0-9._-]{1,88}$")
DENSITIES = {"light", "normal", "busy"}
STEP_SECONDS = 0.5
MAX_STORED_RUNS = 100

# Exogenous demand remains intentionally simple and deterministic. The same
# generated arrival plan is supplied to Fixed and Adaptive. Policy-dependent
# upstream service can still change the timing of transferred arrivals at the
# downstream intersection; that is an experiment outcome, not a changed input.
VEHICLE_RATES_PER_MINUTE = {
    "light": (5.0, 2.5),
    "normal": (10.0, 5.0),
    "busy": (18.0, 9.0),
}
PEDESTRIAN_RATES_PER_MINUTE = {
    "light": (2.0, 2.0),
    "normal": (5.0, 4.0),
    "busy": (9.0, 7.0),
}
VEHICLE_SERVICE_PER_SECOND = 0.9
PEDESTRIAN_SERVICE_PER_SECOND = 1.6


@dataclass
class _VehicleArrival:
    at_s: float
    vehicle_id: str
    class_name: str
    continues_to_destination: bool


@dataclass
class _QueuedVehicle:
    vehicle_id: str
    class_name: str
    queued_at_s: float
    network_started_at_s: float
    continues_to_destination: bool = False
    origin: str = "external"
    source_departed_at_s: float | None = None


@dataclass
class _Transfer:
    arrive_at_s: float
    vehicle: _QueuedVehicle


@dataclass
class _PedestrianArrival:
    at_s: float
    pedestrian_id: str


class _BenchmarkSignalRulesService(SignalRulesService):
    """Signal-rules adapter using simulation time for stale/memory evaluation."""

    def __init__(self, *, config_path: Path, history_path: Path) -> None:
        self._benchmark_clock_s = 0.0
        super().__init__(config_path=config_path, history_path=history_path)

    def set_benchmark_clock(self, clock_s: float) -> None:
        self._benchmark_clock_s = max(0.0, float(clock_s))

    def observe(self, observation: dict[str, Any]) -> None:
        now = self._benchmark_clock_s
        with self._lock:
            self._last_observation = {
                "pedestrians_waiting": max(0, int(observation.get("pedestrians_waiting", 0) or 0)),
                "pedestrians_crossing": max(0, int(observation.get("pedestrians_crossing", 0) or 0)),
                "vehicles_waiting": max(0, int(observation.get("vehicles_waiting", 0) or 0)),
                "zone_class_counts": deepcopy(observation.get("zone_class_counts", {}))
                if isinstance(observation.get("zone_class_counts", {}), dict)
                else {},
                "source_frame_number": observation.get("source_frame_number"),
                "source_timestamp_ms": observation.get("source_timestamp_ms"),
                "data_source": observation.get("data_source"),
            }
            self._last_observation_monotonic = now
            self._update_memory_locked(self._pedestrian_wait, self._last_observation["pedestrians_waiting"], now)
            self._update_memory_locked(self._vehicle_wait, self._last_observation["vehicles_waiting"], now)
            self._update_memory_locked(self._crossing, self._last_observation["pedestrians_crossing"], now)

    def _observation_values_locked(self, profile: dict[str, Any]) -> tuple[dict[str, Any], bool, str | None]:
        now = self._benchmark_clock_s
        fresh = self._last_observation_monotonic is not None and now - self._last_observation_monotonic <= float(
            profile["stale_data_seconds"]
        )
        memory_window = float(profile["demand_memory_seconds"])

        def memory_count(memory: Any, current: int) -> int:
            if current > 0:
                return current
            if memory.last_seen_monotonic is not None and now - memory.last_seen_monotonic <= memory_window:
                return max(1, memory.last_count)
            return 0

        base = dict(self._last_observation)
        base.setdefault("pedestrians_waiting", 0)
        base.setdefault("pedestrians_crossing", 0)
        base.setdefault("vehicles_waiting", 0)
        base.setdefault("zone_class_counts", {})
        base["pedestrians_waiting"] = memory_count(self._pedestrian_wait, int(base["pedestrians_waiting"]))
        base["pedestrians_crossing"] = memory_count(self._crossing, int(base["pedestrians_crossing"]))
        base["vehicles_waiting"] = memory_count(self._vehicle_wait, int(base["vehicles_waiting"]))
        base["pedestrian_wait_seconds"] = self._memory_age(self._pedestrian_wait, now, memory_window)
        base["vehicle_wait_seconds"] = self._memory_age(self._vehicle_wait, now, memory_window)
        base["crossing_dwell_seconds"] = self._memory_age(self._crossing, now, memory_window)
        base["mobility_assistance"] = False
        base["incident_person_fallen"] = False
        config = self._load_config_locked()
        if config["mode"] == "test":
            base.update(self._test_inputs)
            fresh = True
        fallback_reason = None if fresh else "Adaptive observations are stale or unavailable; normal configured timing is active."
        return base, fresh, fallback_reason


class _IntersectionRuntime:
    def __init__(
        self,
        *,
        intersection: dict[str, Any],
        mode: str,
        profile: str,
        policy_config: dict[str, Any],
        zone_types: dict[str, str],
        temp_root: Path,
        controller_factory: Callable[[Path, Path], Any] | None = None,
    ) -> None:
        self.intersection = deepcopy(intersection)
        self.intersection_id = str(intersection["id"])
        self.mode = mode
        self.profile = profile
        self.zone_types = dict(zone_types)

        config = deepcopy(policy_config)
        config["mode"] = mode
        config["dry_run"] = False
        config["active_profile"] = profile
        config_path = temp_root / f"{mode}_{self.intersection_id}_policy.json"
        history_path = temp_root / f"{mode}_{self.intersection_id}_history.jsonl"
        config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        self.history_path = history_path
        if controller_factory is None:
            self.controller = _BenchmarkSignalRulesService(config_path=config_path, history_path=history_path)
        else:
            self.controller = controller_factory(config_path, history_path)

        self.vehicle_queue: deque[_QueuedVehicle] = deque()
        self.pedestrian_queue: deque[float] = deque()
        self.vehicle_waits: list[float] = []
        self.pedestrian_waits: list[float] = []
        self.vehicle_queue_samples: list[int] = []
        self.pedestrian_queue_samples: list[int] = []
        self.vehicle_queue_seconds = 0.0
        self.pedestrian_queue_seconds = 0.0
        self.vehicle_queue_occupied_seconds = 0.0
        self.pedestrian_queue_occupied_seconds = 0.0
        self.vehicles_served = 0
        self.pedestrians_served = 0
        self.external_vehicle_arrivals = 0
        self.transfer_vehicle_arrivals = 0
        self.external_pedestrian_arrivals = 0
        self.phase_time_seconds: dict[str, float] = {}
        self.phase_transitions = 0
        self.cycles_completed = 0
        self._previous_phase_key: str | None = None
        self._vehicle_service_credit = 0.0
        self._pedestrian_service_credit = 0.0

    def enqueue_external_vehicle(self, event: _VehicleArrival) -> None:
        self.vehicle_queue.append(
            _QueuedVehicle(
                vehicle_id=event.vehicle_id,
                class_name=event.class_name,
                queued_at_s=event.at_s,
                network_started_at_s=event.at_s,
                continues_to_destination=event.continues_to_destination,
            )
        )
        self.external_vehicle_arrivals += 1

    def enqueue_transfer(self, transfer: _Transfer) -> None:
        vehicle = transfer.vehicle
        vehicle.queued_at_s = transfer.arrive_at_s
        vehicle.origin = "transfer"
        vehicle.continues_to_destination = False
        self.vehicle_queue.append(vehicle)
        self.transfer_vehicle_arrivals += 1

    def enqueue_pedestrian(self, event: _PedestrianArrival) -> None:
        self.pedestrian_queue.append(event.at_s)
        self.external_pedestrian_arrivals += 1

    def observation(self) -> dict[str, Any]:
        class_counts: dict[str, int] = {}
        for vehicle in self.vehicle_queue:
            class_counts[vehicle.class_name] = class_counts.get(vehicle.class_name, 0) + 1

        zone_class_counts: dict[str, dict[str, int]] = {}
        for zone_id in self.intersection.get("zone_ids", []):
            zone_type = self.zone_types.get(str(zone_id))
            if zone_type == "vehicle_queue":
                zone_class_counts[str(zone_id)] = dict(class_counts)
            elif zone_type in {"pedestrian_waiting", "crossing"}:
                zone_class_counts[str(zone_id)] = {"person": len(self.pedestrian_queue)} if self.pedestrian_queue else {}
            elif zone_type == "counting_region":
                combined = dict(class_counts)
                if self.pedestrian_queue:
                    combined["person"] = len(self.pedestrian_queue)
                zone_class_counts[str(zone_id)] = combined
            else:
                zone_class_counts[str(zone_id)] = {}

        return {
            "vehicles_waiting": len(self.vehicle_queue),
            "pedestrians_waiting": len(self.pedestrian_queue),
            "pedestrians_crossing": 0,
            "zone_class_counts": zone_class_counts,
            "data_source": "network_simulation_experiment",
        }

    def signal(self, clock_s: float) -> dict[str, Any]:
        if hasattr(self.controller, "set_benchmark_clock"):
            self.controller.set_benchmark_clock(clock_s)
        self.controller.observe(self.observation())
        return self.controller.signal_state(clock_s)

    def advance_signal_metrics(self, signal: dict[str, Any], dt: float) -> None:
        phase = str(signal.get("phase") or "unknown")
        self.phase_time_seconds[phase] = self.phase_time_seconds.get(phase, 0.0) + dt
        phase_key = str(signal.get("phase_key") or phase)
        if self._previous_phase_key is not None and phase_key != self._previous_phase_key:
            self.phase_transitions += 1
            if phase_key == "vehicle_green":
                self.cycles_completed += 1
        self._previous_phase_key = phase_key

    def serve_vehicles(self, *, clock_s: float, dt: float, vehicle_go: bool) -> list[_QueuedVehicle]:
        if not vehicle_go:
            self._vehicle_service_credit = 0.0
            return []
        self._vehicle_service_credit += VEHICLE_SERVICE_PER_SECOND * dt
        served: list[_QueuedVehicle] = []
        while self._vehicle_service_credit + 1e-9 >= 1.0 and self.vehicle_queue:
            self._vehicle_service_credit -= 1.0
            vehicle = self.vehicle_queue.popleft()
            self.vehicle_waits.append(max(0.0, clock_s - vehicle.queued_at_s))
            self.vehicles_served += 1
            served.append(vehicle)
        return served

    def serve_pedestrians(self, *, clock_s: float, dt: float, pedestrian_walk: bool) -> None:
        if not pedestrian_walk:
            self._pedestrian_service_credit = 0.0
            return
        self._pedestrian_service_credit += PEDESTRIAN_SERVICE_PER_SECOND * dt
        while self._pedestrian_service_credit + 1e-9 >= 1.0 and self.pedestrian_queue:
            self._pedestrian_service_credit -= 1.0
            queued_at_s = self.pedestrian_queue.popleft()
            self.pedestrian_waits.append(max(0.0, clock_s - queued_at_s))
            self.pedestrians_served += 1

    def record_queue_time(self, dt: float) -> None:
        vehicle_count = len(self.vehicle_queue)
        pedestrian_count = len(self.pedestrian_queue)
        self.vehicle_queue_seconds += vehicle_count * dt
        self.pedestrian_queue_seconds += pedestrian_count * dt
        if vehicle_count:
            self.vehicle_queue_occupied_seconds += dt
        if pedestrian_count:
            self.pedestrian_queue_occupied_seconds += dt

    def sample_queues(self) -> None:
        self.vehicle_queue_samples.append(len(self.vehicle_queue))
        self.pedestrian_queue_samples.append(len(self.pedestrian_queue))

    def finalize_waits(self, clock_s: float) -> None:
        for vehicle in self.vehicle_queue:
            self.vehicle_waits.append(max(0.0, clock_s - vehicle.queued_at_s))
        for queued_at_s in self.pedestrian_queue:
            self.pedestrian_waits.append(max(0.0, clock_s - queued_at_s))

    def controller_stats(self) -> dict[str, Any]:
        applications: dict[str, int] = {}
        extension_seconds = 0.0
        reduction_seconds = 0.0
        if self.history_path.is_file():
            for line in self.history_path.read_text(encoding="utf-8").splitlines():
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("event_type") != "rule_applied":
                    continue
                details = event.get("details") if isinstance(event.get("details"), dict) else {}
                rule_id = str(details.get("rule_id") or "unknown")
                applications[rule_id] = applications.get(rule_id, 0) + 1
                previous = float(details.get("previous_duration_seconds", 0.0) or 0.0)
                effective = float(details.get("effective_duration_seconds", previous) or previous)
                delta = effective - previous
                if delta > 0:
                    extension_seconds += delta
                elif delta < 0:
                    reduction_seconds += abs(delta)
        return {
            "scenario_application_count": sum(applications.values()),
            "scenario_applications": dict(sorted(applications.items())),
            "extension_seconds": round(extension_seconds, 1),
            "reduction_seconds": round(reduction_seconds, 1),
        }

    def result(self, duration_seconds: int, last_signal: dict[str, Any] | None) -> dict[str, Any]:
        duration_minutes = duration_seconds / 60.0
        return {
            "intersection_id": self.intersection_id,
            "label": self.intersection.get("label"),
            "profile": self.profile,
            "metrics": {
                "waiting": {
                    "vehicle": _distribution(self.vehicle_waits),
                    "pedestrian": _distribution(self.pedestrian_waits),
                },
                "queues": {
                    "vehicle": _queue_distribution(
                        self.vehicle_queue_samples,
                        self.vehicle_queue_seconds,
                        self.vehicle_queue_occupied_seconds,
                        duration_seconds,
                    ),
                    "pedestrian": _queue_distribution(
                        self.pedestrian_queue_samples,
                        self.pedestrian_queue_seconds,
                        self.pedestrian_queue_occupied_seconds,
                        duration_seconds,
                    ),
                },
                "throughput": {
                    "vehicles_served": self.vehicles_served,
                    "pedestrians_served": self.pedestrians_served,
                    "vehicles_per_minute": round(self.vehicles_served / duration_minutes, 2) if duration_minutes else 0.0,
                    "pedestrians_per_minute": round(self.pedestrians_served / duration_minutes, 2) if duration_minutes else 0.0,
                    "external_vehicle_arrivals": self.external_vehicle_arrivals,
                    "transfer_vehicle_arrivals": self.transfer_vehicle_arrivals,
                    "external_pedestrian_arrivals": self.external_pedestrian_arrivals,
                },
                "signal": {
                    "phase_time_seconds": {key: round(value, 1) for key, value in sorted(self.phase_time_seconds.items())},
                    "phase_share_percent": {
                        key: round(value / duration_seconds * 100.0, 1)
                        for key, value in sorted(self.phase_time_seconds.items())
                    },
                    "phase_transitions": self.phase_transitions,
                    "cycles_completed": self.cycles_completed,
                    **self.controller_stats(),
                },
            },
            "final_signal": last_signal,
        }


class _NetworkModeSimulation:
    def __init__(
        self,
        *,
        mode: str,
        duration_seconds: int,
        sample_interval_seconds: int,
        source_intersection: dict[str, Any],
        destination_intersection: dict[str, Any],
        link: dict[str, Any],
        policy_config: dict[str, Any],
        profile_override: str | None,
        zone_types: dict[str, str],
        source_vehicle_arrivals: list[_VehicleArrival],
        destination_vehicle_arrivals: list[_VehicleArrival],
        source_pedestrian_arrivals: list[_PedestrianArrival],
        destination_pedestrian_arrivals: list[_PedestrianArrival],
        temp_root: Path,
        controller_factory: Callable[[Path, Path], Any] | None = None,
    ) -> None:
        self.mode = mode
        self.duration_seconds = duration_seconds
        self.sample_interval_seconds = sample_interval_seconds
        self.link = deepcopy(link)
        self.source_vehicle_arrivals = source_vehicle_arrivals
        self.destination_vehicle_arrivals = destination_vehicle_arrivals
        self.source_pedestrian_arrivals = source_pedestrian_arrivals
        self.destination_pedestrian_arrivals = destination_pedestrian_arrivals
        self._source_vehicle_index = 0
        self._destination_vehicle_index = 0
        self._source_pedestrian_index = 0
        self._destination_pedestrian_index = 0
        self.pipeline: list[_Transfer] = []
        self.pipeline_samples: list[int] = []
        self.transfers_departed = 0
        self.transfers_arrived = 0
        self.transfer_events: dict[str, dict[str, Any]] = {}
        self.corridor_completed = 0
        self.corridor_travel_times: list[float] = []
        self.timeline: list[dict[str, Any]] = []
        self._sample_at_s = 0.0

        profiles = policy_config.get("profiles") if isinstance(policy_config, dict) else None
        if not isinstance(profiles, dict):
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "Signal profile configuration is unavailable.", status_code=422)

        source_profile = profile_override or str(source_intersection.get("signal_profile") or policy_config.get("active_profile") or "")
        destination_profile = profile_override or str(destination_intersection.get("signal_profile") or policy_config.get("active_profile") or "")
        for intersection_id, profile in (
            (source_intersection["id"], source_profile),
            (destination_intersection["id"], destination_profile),
        ):
            if profile not in profiles:
                raise AppError(
                    ErrorCode.TRAFFIC_RULE_INVALID,
                    "Network experiment profile must identify an existing signal profile.",
                    status_code=422,
                    details={"intersection_id": intersection_id, "profile": profile, "available_profiles": sorted(profiles)},
                )

        self.source = _IntersectionRuntime(
            intersection=source_intersection,
            mode=mode,
            profile=source_profile,
            policy_config=policy_config,
            zone_types=zone_types,
            temp_root=temp_root,
            controller_factory=controller_factory,
        )
        self.destination = _IntersectionRuntime(
            intersection=destination_intersection,
            mode=mode,
            profile=destination_profile,
            policy_config=policy_config,
            zone_types=zone_types,
            temp_root=temp_root,
            controller_factory=controller_factory,
        )

    def run(self) -> dict[str, Any]:
        clock = 0.0
        last_source_signal: dict[str, Any] | None = None
        last_destination_signal: dict[str, Any] | None = None
        while clock < self.duration_seconds - 1e-9:
            dt = min(STEP_SECONDS, self.duration_seconds - clock)
            self._inject_arrivals(clock)
            self._deliver_transfers(clock)

            source_signal = self.source.signal(clock)
            destination_signal = self.destination.signal(clock)
            last_source_signal = source_signal
            last_destination_signal = destination_signal
            self.source.advance_signal_metrics(source_signal, dt)
            self.destination.advance_signal_metrics(destination_signal, dt)

            served_source = self.source.serve_vehicles(
                clock_s=clock,
                dt=dt,
                vehicle_go=bool(source_signal.get("vehicle_go")),
            )
            for vehicle in served_source:
                if vehicle.continues_to_destination:
                    vehicle.source_departed_at_s = clock
                    scheduled_arrival = clock + float(self.link["travel_time_seconds"])
                    self.pipeline.append(_Transfer(arrive_at_s=scheduled_arrival, vehicle=vehicle))
                    self.transfers_departed += 1
                    self.transfer_events[vehicle.vehicle_id] = {
                        "vehicle_id": vehicle.vehicle_id,
                        "class_name": vehicle.class_name,
                        "departed_at_s": round(clock, 1),
                        "scheduled_arrival_s": round(scheduled_arrival, 1),
                        "arrived_at_s": None,
                    }

            served_destination = self.destination.serve_vehicles(
                clock_s=clock,
                dt=dt,
                vehicle_go=bool(destination_signal.get("vehicle_go")),
            )
            for vehicle in served_destination:
                if vehicle.origin == "transfer":
                    self.corridor_completed += 1
                    self.corridor_travel_times.append(max(0.0, clock - vehicle.network_started_at_s))

            self.source.serve_pedestrians(
                clock_s=clock,
                dt=dt,
                pedestrian_walk=bool(source_signal.get("pedestrian_walk")),
            )
            self.destination.serve_pedestrians(
                clock_s=clock,
                dt=dt,
                pedestrian_walk=bool(destination_signal.get("pedestrian_walk")),
            )
            self.source.record_queue_time(dt)
            self.destination.record_queue_time(dt)

            clock += dt
            self._deliver_transfers(clock)
            if clock + 1e-9 >= self._sample_at_s:
                self.source.sample_queues()
                self.destination.sample_queues()
                self.pipeline_samples.append(len(self.pipeline))
                self._append_timeline(clock, source_signal, destination_signal)
                self._sample_at_s += self.sample_interval_seconds

        self.source.finalize_waits(self.duration_seconds)
        self.destination.finalize_waits(self.duration_seconds)
        return self._build_result(last_source_signal, last_destination_signal)

    def _inject_arrivals(self, clock_s: float) -> None:
        while (
            self._source_vehicle_index < len(self.source_vehicle_arrivals)
            and self.source_vehicle_arrivals[self._source_vehicle_index].at_s <= clock_s + 1e-9
        ):
            self.source.enqueue_external_vehicle(self.source_vehicle_arrivals[self._source_vehicle_index])
            self._source_vehicle_index += 1
        while (
            self._destination_vehicle_index < len(self.destination_vehicle_arrivals)
            and self.destination_vehicle_arrivals[self._destination_vehicle_index].at_s <= clock_s + 1e-9
        ):
            self.destination.enqueue_external_vehicle(self.destination_vehicle_arrivals[self._destination_vehicle_index])
            self._destination_vehicle_index += 1
        while (
            self._source_pedestrian_index < len(self.source_pedestrian_arrivals)
            and self.source_pedestrian_arrivals[self._source_pedestrian_index].at_s <= clock_s + 1e-9
        ):
            self.source.enqueue_pedestrian(self.source_pedestrian_arrivals[self._source_pedestrian_index])
            self._source_pedestrian_index += 1
        while (
            self._destination_pedestrian_index < len(self.destination_pedestrian_arrivals)
            and self.destination_pedestrian_arrivals[self._destination_pedestrian_index].at_s <= clock_s + 1e-9
        ):
            self.destination.enqueue_pedestrian(self.destination_pedestrian_arrivals[self._destination_pedestrian_index])
            self._destination_pedestrian_index += 1

    def _deliver_transfers(self, clock_s: float) -> None:
        if not self.pipeline:
            return
        due = [transfer for transfer in self.pipeline if transfer.arrive_at_s <= clock_s + 1e-9]
        if not due:
            return
        self.pipeline = [transfer for transfer in self.pipeline if transfer.arrive_at_s > clock_s + 1e-9]
        for transfer in sorted(due, key=lambda item: (item.arrive_at_s, item.vehicle.vehicle_id)):
            self.destination.enqueue_transfer(transfer)
            self.transfers_arrived += 1
            event = self.transfer_events.get(transfer.vehicle.vehicle_id)
            if event is not None:
                event["arrived_at_s"] = round(transfer.arrive_at_s, 1)

    def _append_timeline(
        self,
        clock_s: float,
        source_signal: dict[str, Any],
        destination_signal: dict[str, Any],
    ) -> None:
        self.timeline.append(
            {
                "t": round(min(clock_s, float(self.duration_seconds)), 1),
                "source": {
                    "intersection_id": self.source.intersection_id,
                    "phase": source_signal.get("phase"),
                    "phase_key": source_signal.get("phase_key"),
                    "vehicle_queue": len(self.source.vehicle_queue),
                    "pedestrian_queue": len(self.source.pedestrian_queue),
                    "vehicles_served": self.source.vehicles_served,
                    "active_rules": list(source_signal.get("active_rules", [])),
                },
                "destination": {
                    "intersection_id": self.destination.intersection_id,
                    "phase": destination_signal.get("phase"),
                    "phase_key": destination_signal.get("phase_key"),
                    "vehicle_queue": len(self.destination.vehicle_queue),
                    "pedestrian_queue": len(self.destination.pedestrian_queue),
                    "vehicles_served": self.destination.vehicles_served,
                    "active_rules": list(destination_signal.get("active_rules", [])),
                },
                "pipeline_count": len(self.pipeline),
                "transfers_departed": self.transfers_departed,
                "transfers_arrived": self.transfers_arrived,
                "corridor_completed": self.corridor_completed,
            }
        )

    def _build_result(
        self,
        last_source_signal: dict[str, Any] | None,
        last_destination_signal: dict[str, Any] | None,
    ) -> dict[str, Any]:
        duration_minutes = self.duration_seconds / 60.0
        source_result = self.source.result(self.duration_seconds, last_source_signal)
        destination_result = self.destination.result(self.duration_seconds, last_destination_signal)
        total_queue_samples = [
            source + destination
            for source, destination in zip(self.source.vehicle_queue_samples, self.destination.vehicle_queue_samples)
        ]
        total_vehicle_wait = sum(self.source.vehicle_waits) + sum(self.destination.vehicle_waits)
        return {
            "mode": self.mode,
            "intersections": {
                self.source.intersection_id: source_result,
                self.destination.intersection_id: destination_result,
            },
            "network_metrics": {
                "transfers_departed": self.transfers_departed,
                "transfers_arrived": self.transfers_arrived,
                "configured_link_travel_time_seconds": float(self.link["travel_time_seconds"]),
                "transfer_pipeline_average": round(sum(self.pipeline_samples) / len(self.pipeline_samples), 2)
                if self.pipeline_samples
                else 0.0,
                "transfer_pipeline_peak": max(self.pipeline_samples, default=0),
                "corridor_completed": self.corridor_completed,
                "corridor_completed_per_minute": round(self.corridor_completed / duration_minutes, 2)
                if duration_minutes
                else 0.0,
                "corridor_travel_time": _distribution(self.corridor_travel_times),
                "total_vehicle_wait_seconds": round(total_vehicle_wait, 2),
                "total_vehicle_queue_average": round(sum(total_queue_samples) / len(total_queue_samples), 2)
                if total_queue_samples
                else 0.0,
                "total_vehicle_queue_p95": round(_percentile(total_queue_samples, 0.95), 2),
                "total_vehicle_queue_peak": max(total_queue_samples, default=0),
            },
            "timeline": self.timeline,
            "transfer_events": [self.transfer_events[key] for key in sorted(self.transfer_events)],
            "observation_provenance": "simulation",
            "transfer_provenance": "synthetic_network_simulation",
            "cooperative_control_active": False,
            "emergency_priority_active": False,
            "scope_note": (
                "Two-intersection independent-controller simulation baseline. Vehicles can transfer over the configured link, "
                "but neighbour context does not alter either controller in V026."
            ),
        }


class NetworkSimulationExperimentService:
    """Run/persist a deterministic two-intersection independent-control baseline."""

    def __init__(
        self,
        *,
        storage_root: Path | None = None,
        config_provider: Callable[[], dict[str, Any]] | None = None,
        network_provider: Callable[[], dict[str, Any]] | None = None,
        zones_provider: Callable[[], list[dict[str, Any]]] | None = None,
        controller_factory: Callable[[Path, Path], Any] | None = None,
    ) -> None:
        self._storage_root = (storage_root or DEFAULT_STORAGE_ROOT).expanduser().resolve()
        self._config_provider = config_provider or signal_rules_service.get_config
        self._network_provider = network_provider or intersection_network_service.get
        self._zones_provider = zones_provider or zone_service.zones
        self._controller_factory = controller_factory

    def run(
        self,
        *,
        duration_seconds: int,
        density: str,
        seed: int,
        sample_interval_seconds: int,
        profile: str | None,
        label: str = "",
        link_id: str | None = None,
        transfer_share_percent: int = 70,
    ) -> dict[str, Any]:
        density = density.strip().lower()
        if density not in DENSITIES:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "Experiment density must be light, normal, or busy.", status_code=422)
        if not 30 <= int(duration_seconds) <= 1800:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "Experiment duration must be between 30 and 1800 seconds.", status_code=422)
        if not 1 <= int(sample_interval_seconds) <= 10:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "Experiment sample interval must be between 1 and 10 seconds.", status_code=422)
        if not 0 <= int(transfer_share_percent) <= 100:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "transfer_share_percent must be between 0 and 100.", status_code=422)

        network = deepcopy(self._network_provider())
        link, source_intersection, destination_intersection = self._resolve_pair(network, link_id)
        policy = deepcopy(self._config_provider())
        zones = deepcopy(self._zones_provider())
        zone_types = {
            str(zone.get("id")): str(zone.get("type"))
            for zone in zones
            if isinstance(zone, dict) and zone.get("id") and zone.get("type")
        }
        arrivals = _arrival_plan(
            duration_seconds=int(duration_seconds),
            density=density,
            seed=int(seed),
            transfer_share_percent=int(transfer_share_percent),
        )

        created_at_ms = int(time.time() * 1000)
        run_id = f"netexp_{created_at_ms}_{uuid.uuid4().hex[:8]}"
        with tempfile.TemporaryDirectory(prefix="aitl_network_experiment_") as temporary:
            temp_root = Path(temporary)
            fixed = _NetworkModeSimulation(
                mode="fixed",
                duration_seconds=int(duration_seconds),
                sample_interval_seconds=int(sample_interval_seconds),
                source_intersection=source_intersection,
                destination_intersection=destination_intersection,
                link=link,
                policy_config=policy,
                profile_override=profile,
                zone_types=zone_types,
                temp_root=temp_root,
                controller_factory=self._controller_factory,
                **arrivals,
            ).run()
            adaptive = _NetworkModeSimulation(
                mode="adaptive",
                duration_seconds=int(duration_seconds),
                sample_interval_seconds=int(sample_interval_seconds),
                source_intersection=source_intersection,
                destination_intersection=destination_intersection,
                link=link,
                policy_config=policy,
                profile_override=profile,
                zone_types=zone_types,
                temp_root=temp_root,
                controller_factory=self._controller_factory,
                **arrivals,
            ).run()

        result = {
            "run_id": run_id,
            "created_at_ms": created_at_ms,
            "label": label.strip(),
            "scenario": {
                "kind": "two_intersection_network",
                "duration_seconds": int(duration_seconds),
                "density": density,
                "seed": int(seed),
                "sample_interval_seconds": int(sample_interval_seconds),
                "profile_override": profile,
                "transfer_share_percent": int(transfer_share_percent),
                "link": deepcopy(link),
                "source_intersection": _intersection_snapshot(source_intersection),
                "destination_intersection": _intersection_snapshot(destination_intersection),
                "comparison": ["fixed", "adaptive"],
                "arrival_plan": _arrival_plan_snapshot(arrivals),
                "cooperative_control_active": False,
            },
            "fixed": fixed,
            "adaptive": adaptive,
            "comparison": _network_comparison(fixed, adaptive),
            "prototype_only": True,
            "scope_note": (
                "Controlled local two-intersection simulation benchmark only. Vehicle transfer is synthetic; "
                "V026 does not use neighbour context to coordinate signal timing."
            ),
        }
        self._write_run(result)
        self._trim_old_runs()
        return result

    def list(self, limit: int = 50) -> dict[str, Any]:
        limit = max(1, min(int(limit), 100))
        try:
            paths = (
                sorted(self._storage_root.glob("netexp_*.json"), key=lambda path: path.stat().st_mtime_ns, reverse=True)
                if self._storage_root.is_dir()
                else []
            )
            items: list[dict[str, Any]] = []
            for path in paths[:limit]:
                try:
                    payload = read_json(path)
                except (OSError, json.JSONDecodeError, TypeError):
                    continue
                if isinstance(payload, dict):
                    items.append(self._summary(payload))
        except OSError as exc:
            raise AppError(ErrorCode.TRAFFIC_EXPERIMENT_READ_FAILED, status_code=500) from exc
        return {
            "experiments": items,
            "total": len(paths),
            "storage_path": self._relative_storage_root(),
            "prototype_only": True,
            "cooperative_control_active": False,
        }

    def get(self, run_id: str) -> dict[str, Any]:
        path = self._run_path(run_id)
        if not path.is_file():
            raise AppError(
                ErrorCode.TRAFFIC_EXPERIMENT_READ_FAILED,
                "Network simulation experiment was not found.",
                status_code=404,
                details={"run_id": run_id},
            )
        try:
            payload = read_json(path)
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            raise AppError(
                ErrorCode.TRAFFIC_EXPERIMENT_READ_FAILED,
                status_code=500,
                details={"run_id": run_id},
            ) from exc
        if not isinstance(payload, dict):
            raise AppError(
                ErrorCode.TRAFFIC_EXPERIMENT_READ_FAILED,
                "Stored network simulation experiment is invalid.",
                status_code=500,
                details={"run_id": run_id},
            )
        return payload

    def delete(self, run_id: str) -> dict[str, Any]:
        path = self._run_path(run_id)
        if not path.exists():
            raise AppError(
                ErrorCode.TRAFFIC_EXPERIMENT_READ_FAILED,
                "Network simulation experiment was not found.",
                status_code=404,
                details={"run_id": run_id},
            )
        try:
            path.unlink()
        except OSError as exc:
            raise AppError(
                ErrorCode.TRAFFIC_EXPERIMENT_DELETE_FAILED,
                status_code=500,
                details={"run_id": run_id},
            ) from exc
        return {"deleted": True, "run_id": run_id}

    def export_csv(self, run_id: str) -> str:
        result = self.get(run_id)
        fixed_timeline = result.get("fixed", {}).get("timeline", [])
        adaptive_timeline = result.get("adaptive", {}).get("timeline", [])
        rows = max(len(fixed_timeline), len(adaptive_timeline))
        output = StringIO()
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(
            [
                "t_seconds",
                "fixed_source_phase",
                "fixed_source_vehicle_queue",
                "fixed_source_pedestrian_queue",
                "fixed_source_vehicles_served",
                "fixed_source_active_rules",
                "fixed_destination_phase",
                "fixed_destination_vehicle_queue",
                "fixed_destination_pedestrian_queue",
                "fixed_destination_vehicles_served",
                "fixed_destination_active_rules",
                "fixed_pipeline_count",
                "fixed_transfers_departed",
                "fixed_transfers_arrived",
                "fixed_corridor_completed",
                "adaptive_source_phase",
                "adaptive_source_vehicle_queue",
                "adaptive_source_pedestrian_queue",
                "adaptive_source_vehicles_served",
                "adaptive_source_active_rules",
                "adaptive_destination_phase",
                "adaptive_destination_vehicle_queue",
                "adaptive_destination_pedestrian_queue",
                "adaptive_destination_vehicles_served",
                "adaptive_destination_active_rules",
                "adaptive_pipeline_count",
                "adaptive_transfers_departed",
                "adaptive_transfers_arrived",
                "adaptive_corridor_completed",
            ]
        )
        for index in range(rows):
            fixed = fixed_timeline[index] if index < len(fixed_timeline) else {}
            adaptive = adaptive_timeline[index] if index < len(adaptive_timeline) else {}
            fixed_source = fixed.get("source", {})
            fixed_destination = fixed.get("destination", {})
            adaptive_source = adaptive.get("source", {})
            adaptive_destination = adaptive.get("destination", {})
            writer.writerow(
                [
                    fixed.get("t", adaptive.get("t", "")),
                    fixed_source.get("phase", ""),
                    fixed_source.get("vehicle_queue", ""),
                    fixed_source.get("pedestrian_queue", ""),
                    fixed_source.get("vehicles_served", ""),
                    "|".join(fixed_source.get("active_rules", [])),
                    fixed_destination.get("phase", ""),
                    fixed_destination.get("vehicle_queue", ""),
                    fixed_destination.get("pedestrian_queue", ""),
                    fixed_destination.get("vehicles_served", ""),
                    "|".join(fixed_destination.get("active_rules", [])),
                    fixed.get("pipeline_count", ""),
                    fixed.get("transfers_departed", ""),
                    fixed.get("transfers_arrived", ""),
                    fixed.get("corridor_completed", ""),
                    adaptive_source.get("phase", ""),
                    adaptive_source.get("vehicle_queue", ""),
                    adaptive_source.get("pedestrian_queue", ""),
                    adaptive_source.get("vehicles_served", ""),
                    "|".join(adaptive_source.get("active_rules", [])),
                    adaptive_destination.get("phase", ""),
                    adaptive_destination.get("vehicle_queue", ""),
                    adaptive_destination.get("pedestrian_queue", ""),
                    adaptive_destination.get("vehicles_served", ""),
                    "|".join(adaptive_destination.get("active_rules", [])),
                    adaptive.get("pipeline_count", ""),
                    adaptive.get("transfers_departed", ""),
                    adaptive.get("transfers_arrived", ""),
                    adaptive.get("corridor_completed", ""),
                ]
            )
        return output.getvalue()

    @staticmethod
    def _resolve_pair(
        network: dict[str, Any], link_id: str | None
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        intersections = {
            str(item.get("id")): item
            for item in network.get("intersections", [])
            if isinstance(item, dict) and item.get("id")
        }
        enabled_links = [
            item
            for item in network.get("links", [])
            if isinstance(item, dict) and bool(item.get("enabled", True))
        ]
        if link_id is not None:
            enabled_links = [item for item in enabled_links if str(item.get("id")) == link_id]
        enabled_links.sort(key=lambda item: str(item.get("id")))
        if not enabled_links:
            raise AppError(
                ErrorCode.TRAFFIC_NETWORK_INVALID,
                "Network experiment requires an enabled directed intersection link.",
                status_code=422,
                details={"link_id": link_id},
            )
        link = deepcopy(enabled_links[0])
        source = intersections.get(str(link.get("source_intersection_id")))
        destination = intersections.get(str(link.get("destination_intersection_id")))
        if source is None or destination is None or not source.get("enabled", True) or not destination.get("enabled", True):
            raise AppError(
                ErrorCode.TRAFFIC_NETWORK_INVALID,
                "Network experiment link must connect two enabled configured intersections.",
                status_code=422,
                details={"link_id": link.get("id")},
            )
        return link, deepcopy(source), deepcopy(destination)

    def _write_run(self, result: dict[str, Any]) -> None:
        try:
            write_json_atomic(self._run_path(str(result["run_id"])), result)
        except (OSError, TypeError, ValueError) as exc:
            logger.exception("Network simulation experiment write failed")
            raise AppError(ErrorCode.TRAFFIC_EXPERIMENT_WRITE_FAILED, status_code=500) from exc

    def _trim_old_runs(self) -> None:
        try:
            paths = sorted(self._storage_root.glob("netexp_*.json"), key=lambda path: path.stat().st_mtime_ns, reverse=True)
            for path in paths[MAX_STORED_RUNS:]:
                path.unlink(missing_ok=True)
        except OSError:
            logger.warning("Network simulation experiment retention cleanup failed", exc_info=True)

    def _run_path(self, run_id: str) -> Path:
        if not RUN_ID_PATTERN.fullmatch(run_id):
            raise AppError(
                ErrorCode.TRAFFIC_EXPERIMENT_READ_FAILED,
                "Network simulation experiment id is invalid.",
                status_code=422,
                details={"run_id": run_id},
            )
        return self._storage_root / f"{run_id}.json"

    def _relative_storage_root(self) -> str:
        try:
            return str(self._storage_root.relative_to(PROJECT_ROOT)).replace("\\", "/")
        except ValueError:
            return str(self._storage_root)

    @staticmethod
    def _summary(payload: dict[str, Any]) -> dict[str, Any]:
        scenario = payload.get("scenario") if isinstance(payload.get("scenario"), dict) else {}
        comparison = payload.get("comparison") if isinstance(payload.get("comparison"), dict) else {}
        return {
            "run_id": payload.get("run_id"),
            "created_at_ms": payload.get("created_at_ms"),
            "label": payload.get("label", ""),
            "scenario": scenario,
            "headline": {
                "corridor_completed": comparison.get("corridor_completed"),
                "corridor_travel_average": comparison.get("corridor_travel_average"),
                "total_vehicle_wait": comparison.get("total_vehicle_wait"),
                "total_vehicle_queue_average": comparison.get("total_vehicle_queue_average"),
            },
        }


def _arrival_plan(
    *,
    duration_seconds: int,
    density: str,
    seed: int,
    transfer_share_percent: int,
) -> dict[str, list[Any]]:
    rng = random.Random(seed + {"light": 1103, "normal": 2207, "busy": 3301}[density])
    source_vehicle_rate, destination_vehicle_rate = VEHICLE_RATES_PER_MINUTE[density]
    source_ped_rate, destination_ped_rate = PEDESTRIAN_RATES_PER_MINUTE[density]

    return {
        "source_vehicle_arrivals": _vehicle_arrivals(
            rng,
            rate_per_minute=source_vehicle_rate,
            duration_seconds=duration_seconds,
            prefix="src",
            transfer_share_percent=transfer_share_percent,
        ),
        "destination_vehicle_arrivals": _vehicle_arrivals(
            rng,
            rate_per_minute=destination_vehicle_rate,
            duration_seconds=duration_seconds,
            prefix="dst",
            transfer_share_percent=0,
        ),
        "source_pedestrian_arrivals": _pedestrian_arrivals(
            rng,
            rate_per_minute=source_ped_rate,
            duration_seconds=duration_seconds,
            prefix="srcp",
        ),
        "destination_pedestrian_arrivals": _pedestrian_arrivals(
            rng,
            rate_per_minute=destination_ped_rate,
            duration_seconds=duration_seconds,
            prefix="dstp",
        ),
    }


def _arrival_plan_snapshot(arrivals: dict[str, list[Any]]) -> dict[str, Any]:
    source_vehicles = arrivals["source_vehicle_arrivals"]
    destination_vehicles = arrivals["destination_vehicle_arrivals"]
    source_pedestrians = arrivals["source_pedestrian_arrivals"]
    destination_pedestrians = arrivals["destination_pedestrian_arrivals"]
    canonical = {
        "source_vehicle_arrivals": [
            [round(item.at_s, 3), item.vehicle_id, item.class_name, item.continues_to_destination]
            for item in source_vehicles
        ],
        "destination_vehicle_arrivals": [
            [round(item.at_s, 3), item.vehicle_id, item.class_name, item.continues_to_destination]
            for item in destination_vehicles
        ],
        "source_pedestrian_arrivals": [[round(item.at_s, 3), item.pedestrian_id] for item in source_pedestrians],
        "destination_pedestrian_arrivals": [
            [round(item.at_s, 3), item.pedestrian_id] for item in destination_pedestrians
        ],
    }
    fingerprint = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "source_vehicle_count": len(source_vehicles),
        "source_transfer_candidate_count": sum(1 for item in source_vehicles if item.continues_to_destination),
        "destination_external_vehicle_count": len(destination_vehicles),
        "source_pedestrian_count": len(source_pedestrians),
        "destination_pedestrian_count": len(destination_pedestrians),
        "fingerprint_sha256": fingerprint,
        "note": "Fixed and Adaptive receive this same seeded exogenous arrival plan; transfer departure timing remains policy-dependent.",
    }


def _vehicle_arrivals(
    rng: random.Random,
    *,
    rate_per_minute: float,
    duration_seconds: int,
    prefix: str,
    transfer_share_percent: int,
) -> list[_VehicleArrival]:
    events: list[_VehicleArrival] = []
    if rate_per_minute <= 0:
        return events
    clock = 0.0
    rate_per_second = rate_per_minute / 60.0
    index = 0
    while True:
        clock += rng.expovariate(rate_per_second)
        if clock > duration_seconds:
            break
        index += 1
        class_name = "bus" if rng.random() < 0.16 else "car"
        continues = rng.random() * 100.0 < transfer_share_percent
        events.append(
            _VehicleArrival(
                at_s=round(clock, 3),
                vehicle_id=f"{prefix}_{index:04d}",
                class_name=class_name,
                continues_to_destination=continues,
            )
        )
    return events


def _pedestrian_arrivals(
    rng: random.Random,
    *,
    rate_per_minute: float,
    duration_seconds: int,
    prefix: str,
) -> list[_PedestrianArrival]:
    events: list[_PedestrianArrival] = []
    if rate_per_minute <= 0:
        return events
    clock = 0.0
    rate_per_second = rate_per_minute / 60.0
    index = 0
    while True:
        clock += rng.expovariate(rate_per_second)
        if clock > duration_seconds:
            break
        index += 1
        events.append(_PedestrianArrival(at_s=round(clock, 3), pedestrian_id=f"{prefix}_{index:04d}"))
    return events


def _intersection_snapshot(intersection: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": intersection.get("id"),
        "label": intersection.get("label"),
        "signal_profile": intersection.get("signal_profile"),
        "zone_ids": list(intersection.get("zone_ids", [])),
    }


def _percentile(values: list[float] | list[int], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _distribution(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "count": 0,
            "average_seconds": 0.0,
            "median_seconds": 0.0,
            "p95_seconds": 0.0,
            "max_seconds": 0.0,
            "total_seconds": 0.0,
        }
    return {
        "count": len(values),
        "average_seconds": round(sum(values) / len(values), 2),
        "median_seconds": round(_percentile(values, 0.5), 2),
        "p95_seconds": round(_percentile(values, 0.95), 2),
        "max_seconds": round(max(values), 2),
        "total_seconds": round(sum(values), 2),
    }


def _queue_distribution(
    values: list[int],
    queue_seconds: float,
    occupied_seconds: float,
    duration_seconds: float,
) -> dict[str, Any]:
    return {
        "sample_count": len(values),
        "average": round(sum(values) / len(values), 2) if values else 0.0,
        "p95": round(_percentile(values, 0.95), 2),
        "max": max(values, default=0),
        "queue_seconds": round(queue_seconds, 2),
        "occupied_seconds": round(occupied_seconds, 2),
        "occupied_share_percent": round(occupied_seconds / duration_seconds * 100.0, 1)
        if duration_seconds
        else 0.0,
    }


def _delta(fixed: float, adaptive: float, *, lower_is_better: bool) -> dict[str, Any]:
    difference = adaptive - fixed
    percent_change = (difference / fixed * 100.0) if abs(fixed) > 1e-9 else None
    if abs(difference) < 1e-9:
        direction = "same"
    elif (difference < 0) == lower_is_better:
        direction = "better"
    else:
        direction = "worse"
    return {
        "fixed": round(fixed, 2),
        "adaptive": round(adaptive, 2),
        "difference": round(difference, 2),
        "percent_change": round(percent_change, 1) if percent_change is not None else None,
        "adaptive_direction": direction,
        "lower_is_better": lower_is_better,
    }


def _network_comparison(fixed: dict[str, Any], adaptive: dict[str, Any]) -> dict[str, Any]:
    fixed_metrics = fixed["network_metrics"]
    adaptive_metrics = adaptive["network_metrics"]
    return {
        "corridor_completed": _delta(
            fixed_metrics["corridor_completed_per_minute"],
            adaptive_metrics["corridor_completed_per_minute"],
            lower_is_better=False,
        ),
        "corridor_travel_average": _delta(
            fixed_metrics["corridor_travel_time"]["average_seconds"],
            adaptive_metrics["corridor_travel_time"]["average_seconds"],
            lower_is_better=True,
        ),
        "corridor_travel_p95": _delta(
            fixed_metrics["corridor_travel_time"]["p95_seconds"],
            adaptive_metrics["corridor_travel_time"]["p95_seconds"],
            lower_is_better=True,
        ),
        "total_vehicle_wait": _delta(
            fixed_metrics["total_vehicle_wait_seconds"],
            adaptive_metrics["total_vehicle_wait_seconds"],
            lower_is_better=True,
        ),
        "total_vehicle_queue_average": _delta(
            fixed_metrics["total_vehicle_queue_average"],
            adaptive_metrics["total_vehicle_queue_average"],
            lower_is_better=True,
        ),
        "total_vehicle_queue_p95": _delta(
            fixed_metrics["total_vehicle_queue_p95"],
            adaptive_metrics["total_vehicle_queue_p95"],
            lower_is_better=True,
        ),
        "transfer_pipeline_average": _delta(
            fixed_metrics["transfer_pipeline_average"],
            adaptive_metrics["transfer_pipeline_average"],
            lower_is_better=True,
        ),
    }


network_simulation_experiment_service = NetworkSimulationExperimentService()
