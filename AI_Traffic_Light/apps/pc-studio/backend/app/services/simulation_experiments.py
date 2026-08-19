from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import csv
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
from app.services.signal_rules import SignalRulesService, signal_rules_service
from app.services.zones import zone_service

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_STORAGE_ROOT = PROJECT_ROOT / "outputs" / "simulation_experiments"
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,96}$")
DENSITIES = {"light", "normal", "busy"}

# Keep these numeric reference points aligned with the V024 camera simulator. The
# experiment runner intentionally avoids touching the live CameraFrameService so
# a benchmark cannot reset or perturb the operator's current simulation state.
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
ROAD_TOP = 179
ROAD_BOTTOM = 625
CROSSING_LEFT = 520
CROSSING_RIGHT = 760
EASTBOUND_STOP_LINE = 495
WESTBOUND_STOP_LINE = 785
TOP_PEDESTRIAN_WAIT_Y = 126
BOTTOM_PEDESTRIAN_WAIT_Y = 674
JUNCTION_CENTRE_X = (CROSSING_LEFT + CROSSING_RIGHT) / 2

STEP_SECONDS = 0.1
MAX_STORED_RUNS = 200


@dataclass
class _Vehicle:
    vehicle_id: str
    x: float
    y: int
    width: int
    speed: float
    direction: int
    class_name: str
    wait_started_s: float | None = None
    passed_centre: bool = False


@dataclass
class _Pedestrian:
    pedestrian_id: str
    x: int
    y: float
    speed: float
    direction: int
    wait_started_s: float | None = None


class _BenchmarkSignalRulesService(SignalRulesService):
    """SignalRulesService adapter with a deterministic monotonic benchmark clock.

    The production controller intentionally uses ``time.monotonic()`` for stale
    observations and demand-memory age. A benchmark runs much faster than wall
    time, so this isolated adapter supplies simulation time while preserving the
    production controller's phase/rule/cooldown/arbitration implementation.
    """

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
                "zone_class_counts": deepcopy(observation.get("zone_class_counts", {})) if isinstance(observation.get("zone_class_counts", {}), dict) else {},
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
        fresh = self._last_observation_monotonic is not None and now - self._last_observation_monotonic <= float(profile["stale_data_seconds"])
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


class _ModeSimulation:
    def __init__(
        self,
        *,
        mode: str,
        density: str,
        seed: int,
        duration_seconds: int,
        sample_interval_seconds: int,
        policy_config: dict[str, Any],
        zones: list[dict[str, Any]],
        temp_root: Path,
    ) -> None:
        self.mode = mode
        self.density = density
        self.seed = seed
        self.duration_seconds = duration_seconds
        self.sample_interval_seconds = sample_interval_seconds
        self.zones = deepcopy(zones)
        density_offset = {"light": 101, "normal": 211, "busy": 307}[density]
        self.rng = random.Random(seed + density_offset)

        config = deepcopy(policy_config)
        config["mode"] = mode
        config["dry_run"] = False
        config_path = temp_root / f"{mode}_policy.json"
        history_path = temp_root / f"{mode}_controller_history.jsonl"
        config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        self.controller = _BenchmarkSignalRulesService(config_path=config_path, history_path=history_path)
        self.controller_history_path = history_path

        self.vehicles = self._make_vehicles()
        self.pedestrians = self._make_pedestrians()
        self.vehicle_waits: list[float] = []
        self.pedestrian_waits: list[float] = []
        self.vehicle_passages = 0
        self.pedestrian_crossings = 0
        self.vehicle_queue_seconds = 0.0
        self.pedestrian_queue_seconds = 0.0
        self.vehicle_queue_occupied_seconds = 0.0
        self.pedestrian_queue_occupied_seconds = 0.0
        self.simultaneous_queue_seconds = 0.0
        self.vehicle_queue_samples: list[int] = []
        self.pedestrian_queue_samples: list[int] = []
        self.phase_time_seconds: dict[str, float] = {}
        self.phase_transitions = 0
        self.cycles_completed = 0
        self.protected_overlap_seconds = 0.0
        self.timeline: list[dict[str, Any]] = []
        self._previous_phase_key: str | None = None
        self._sample_at_s = 0.0

    def _make_vehicles(self) -> list[_Vehicle]:
        count = {"light": 4, "normal": 8, "busy": 12}[self.density]
        vehicles: list[_Vehicle] = []
        for index in range(count):
            direction = 1 if index % 2 == 0 else -1
            lane_index = index // 2
            vehicle_type = "bus" if index % 5 == 4 else "car"
            width = 220 if vehicle_type == "bus" else self.rng.randint(125, 170)
            if direction > 0:
                x = -240.0 + lane_index * 300
                y = 265
            else:
                x = float(FRAME_WIDTH + 60 - width - lane_index * 300)
                y = 455
            vehicles.append(
                _Vehicle(
                    vehicle_id=f"v{index + 1}",
                    x=x,
                    y=y,
                    width=width,
                    speed=float(self.rng.randint(92, 125)),
                    direction=direction,
                    class_name=vehicle_type,
                )
            )
        return vehicles

    def _make_pedestrians(self) -> list[_Pedestrian]:
        count = {"light": 4, "normal": 7, "busy": 11}[self.density]
        pedestrians: list[_Pedestrian] = []
        for index in range(count):
            direction = 1 if index % 2 == 0 else -1
            x = CROSSING_LEFT + 42 + (index * 47) % (CROSSING_RIGHT - CROSSING_LEFT - 84)
            if direction > 0:
                y = float(max(65, TOP_PEDESTRIAN_WAIT_Y - (index // 2) * 22))
            else:
                y = float(min(710, BOTTOM_PEDESTRIAN_WAIT_Y + (index // 2) * 18))
            pedestrians.append(
                _Pedestrian(
                    pedestrian_id=f"p{index + 1}",
                    x=x,
                    y=y,
                    speed=float(self.rng.randint(88, 106)),
                    direction=direction,
                )
            )
        return pedestrians

    @staticmethod
    def _pedestrian_waiting(pedestrian: _Pedestrian) -> bool:
        if pedestrian.direction > 0:
            return abs(pedestrian.y - TOP_PEDESTRIAN_WAIT_Y) <= 0.5
        return abs(pedestrian.y - BOTTOM_PEDESTRIAN_WAIT_Y) <= 0.5

    @staticmethod
    def _pedestrian_crossing(pedestrian: _Pedestrian) -> bool:
        return ROAD_TOP <= pedestrian.y <= ROAD_BOTTOM

    @staticmethod
    def _point_in_polygon(point: tuple[float, float], polygon: list[list[int]]) -> bool:
        x, y = point
        inside = False
        if len(polygon) < 3:
            return False
        previous_x, previous_y = polygon[-1]
        for current_x, current_y in polygon:
            if (current_y > y) != (previous_y > y):
                denominator = previous_y - current_y
                if denominator != 0:
                    intersection_x = (previous_x - current_x) * (y - current_y) / denominator + current_x
                    if x < intersection_x:
                        inside = not inside
            previous_x, previous_y = current_x, current_y
        return inside

    def _zone_class_counts(self) -> dict[str, dict[str, int]]:
        countable = [zone for zone in self.zones if zone.get("type") not in {"ignore", "counting_line"}]
        ignored = [zone for zone in self.zones if zone.get("type") == "ignore"]
        counts: dict[str, dict[str, int]] = {str(zone["id"]): {} for zone in countable}

        def add(point: tuple[float, float], class_name: str) -> None:
            if any(self._point_in_polygon(point, zone.get("polygon", [])) for zone in ignored):
                return
            for zone in countable:
                if self._point_in_polygon(point, zone.get("polygon", [])):
                    zone_id = str(zone["id"])
                    counts[zone_id][class_name] = counts[zone_id].get(class_name, 0) + 1

        for vehicle in self.vehicles:
            add((vehicle.x + vehicle.width / 2.0, float(vehicle.y)), vehicle.class_name)
        for pedestrian in self.pedestrians:
            add((float(pedestrian.x), pedestrian.y), "person")
        return counts

    def _current_observation(self, vehicle_waiting: set[str]) -> dict[str, Any]:
        return {
            "pedestrians_waiting": sum(1 for item in self.pedestrians if self._pedestrian_waiting(item)),
            "pedestrians_crossing": sum(1 for item in self.pedestrians if self._pedestrian_crossing(item)),
            "vehicles_waiting": len(vehicle_waiting),
            "zone_class_counts": self._zone_class_counts(),
        }

    def run(self) -> dict[str, Any]:
        clock = 0.0
        vehicle_waiting: set[str] = set()
        last_signal: dict[str, Any] | None = None
        self._sample_at_s = 0.0

        while clock < self.duration_seconds - 1e-9:
            dt = min(STEP_SECONDS, self.duration_seconds - clock)
            observation = self._current_observation(vehicle_waiting)
            self.controller.set_benchmark_clock(clock)
            self.controller.observe({**observation, "data_source": "simulation_experiment"})
            signal = self.controller.signal_state(clock)
            last_signal = signal

            self._record_signal_time(signal, dt)
            vehicle_waiting = self._advance_vehicles(dt, clock, signal)
            self._advance_pedestrians(dt, clock, signal)

            ped_waiting_count = sum(1 for item in self.pedestrians if self._pedestrian_waiting(item))
            self.vehicle_queue_seconds += len(vehicle_waiting) * dt
            self.pedestrian_queue_seconds += ped_waiting_count * dt
            if vehicle_waiting:
                self.vehicle_queue_occupied_seconds += dt
            if ped_waiting_count:
                self.pedestrian_queue_occupied_seconds += dt
            if vehicle_waiting and ped_waiting_count:
                self.simultaneous_queue_seconds += dt
            self._record_overlap(signal, dt)

            clock += dt
            if clock + 1e-9 >= self._sample_at_s:
                self._append_timeline(clock, signal, vehicle_waiting, ped_waiting_count)
                self._sample_at_s += self.sample_interval_seconds

        self._finalize_open_waits(self.duration_seconds)
        controller_stats = self._controller_stats()
        return self._build_result(last_signal, controller_stats)

    def _record_signal_time(self, signal: dict[str, Any], dt: float) -> None:
        phase = str(signal["phase"])
        self.phase_time_seconds[phase] = self.phase_time_seconds.get(phase, 0.0) + dt
        phase_key = str(signal.get("phase_key") or phase)
        if self._previous_phase_key is not None and phase_key != self._previous_phase_key:
            self.phase_transitions += 1
            if phase_key == "vehicle_green":
                self.cycles_completed += 1
        self._previous_phase_key = phase_key

    def _advance_vehicles(self, dt: float, clock: float, signal: dict[str, Any]) -> set[str]:
        vehicle_go = bool(signal.get("vehicle_go"))
        gap = 22.0
        waiting_now: set[str] = set()

        def move_group(group: list[_Vehicle]) -> None:
            ahead: _Vehicle | None = None
            for vehicle in group:
                old_x = vehicle.x
                expected = old_x + vehicle.speed * dt * vehicle.direction
                proposed = expected
                if vehicle.direction > 0:
                    front = old_x + vehicle.width
                    committed = front > EASTBOUND_STOP_LINE
                    if not vehicle_go and not committed:
                        proposed = min(proposed, EASTBOUND_STOP_LINE - 8 - vehicle.width)
                    if ahead is not None:
                        proposed = min(proposed, ahead.x - gap - vehicle.width)
                else:
                    front = old_x
                    committed = front < WESTBOUND_STOP_LINE
                    if not vehicle_go and not committed:
                        proposed = max(proposed, WESTBOUND_STOP_LINE + 8)
                    if ahead is not None:
                        proposed = max(proposed, ahead.x + ahead.width + gap)

                vehicle.x = proposed
                moved = abs(vehicle.x - old_x)
                expected_movement = abs(vehicle.speed * dt)
                blocked = moved + 0.05 < expected_movement and not committed
                if blocked:
                    waiting_now.add(vehicle.vehicle_id)
                    if vehicle.wait_started_s is None:
                        vehicle.wait_started_s = clock
                elif vehicle.wait_started_s is not None:
                    self.vehicle_waits.append(max(0.0, clock - vehicle.wait_started_s))
                    vehicle.wait_started_s = None

                old_centre = old_x + vehicle.width / 2
                new_centre = vehicle.x + vehicle.width / 2
                crossed = (
                    vehicle.direction > 0 and old_centre < JUNCTION_CENTRE_X <= new_centre
                ) or (
                    vehicle.direction < 0 and old_centre > JUNCTION_CENTRE_X >= new_centre
                )
                if crossed and not vehicle.passed_centre:
                    self.vehicle_passages += 1
                    vehicle.passed_centre = True
                ahead = vehicle

        eastbound = sorted((v for v in self.vehicles if v.direction > 0), key=lambda item: item.x, reverse=True)
        westbound = sorted((v for v in self.vehicles if v.direction < 0), key=lambda item: item.x)
        move_group(eastbound)
        move_group(westbound)

        for vehicle in self.vehicles:
            if vehicle.direction > 0 and vehicle.x > FRAME_WIDTH + 120:
                peers = [item.x for item in self.vehicles if item.direction > 0 and item is not vehicle]
                vehicle.x = min(
                    -vehicle.width - self.rng.randint(80, 180),
                    min(peers, default=-120.0) - vehicle.width - self.rng.randint(70, 140),
                )
                vehicle.passed_centre = False
                vehicle.wait_started_s = None
            elif vehicle.direction < 0 and vehicle.x + vehicle.width < -120:
                peers = [item.x + item.width for item in self.vehicles if item.direction < 0 and item is not vehicle]
                vehicle.x = max(
                    float(FRAME_WIDTH + self.rng.randint(80, 180)),
                    max(peers, default=float(FRAME_WIDTH + 120)) + self.rng.randint(70, 140),
                )
                vehicle.passed_centre = False
                vehicle.wait_started_s = None
        return waiting_now

    def _advance_pedestrians(self, dt: float, clock: float, signal: dict[str, Any]) -> None:
        can_start_crossing = bool(signal.get("pedestrian_walk"))
        for pedestrian in self.pedestrians:
            old_y = pedestrian.y
            was_waiting = self._pedestrian_waiting(pedestrian)
            if pedestrian.direction > 0:
                if pedestrian.y < TOP_PEDESTRIAN_WAIT_Y:
                    pedestrian.y = min(TOP_PEDESTRIAN_WAIT_Y, pedestrian.y + pedestrian.speed * dt)
                elif pedestrian.y <= TOP_PEDESTRIAN_WAIT_Y + 0.5 and not can_start_crossing:
                    pedestrian.y = float(TOP_PEDESTRIAN_WAIT_Y)
                else:
                    pedestrian.y += pedestrian.speed * dt
                completed = old_y < BOTTOM_PEDESTRIAN_WAIT_Y <= pedestrian.y
                if pedestrian.y > FRAME_HEIGHT + 25:
                    pedestrian.y = float(70 - self.rng.randint(0, 42))
            else:
                if pedestrian.y > BOTTOM_PEDESTRIAN_WAIT_Y:
                    pedestrian.y = max(BOTTOM_PEDESTRIAN_WAIT_Y, pedestrian.y - pedestrian.speed * dt)
                elif pedestrian.y >= BOTTOM_PEDESTRIAN_WAIT_Y - 0.5 and not can_start_crossing:
                    pedestrian.y = float(BOTTOM_PEDESTRIAN_WAIT_Y)
                else:
                    pedestrian.y -= pedestrian.speed * dt
                completed = old_y > TOP_PEDESTRIAN_WAIT_Y >= pedestrian.y
                if pedestrian.y < 20:
                    pedestrian.y = float(FRAME_HEIGHT - 10 + self.rng.randint(0, 36))

            is_waiting = self._pedestrian_waiting(pedestrian)
            if is_waiting and pedestrian.wait_started_s is None:
                pedestrian.wait_started_s = clock
            elif was_waiting and not is_waiting and pedestrian.wait_started_s is not None:
                self.pedestrian_waits.append(max(0.0, clock - pedestrian.wait_started_s))
                pedestrian.wait_started_s = None
            if completed:
                self.pedestrian_crossings += 1

    def _record_overlap(self, signal: dict[str, Any], dt: float) -> None:
        if signal.get("phase") not in {"pedestrian_green", "pedestrian_flashing"}:
            return
        pedestrians_in_crossing = any(self._pedestrian_crossing(item) for item in self.pedestrians)
        if not pedestrians_in_crossing:
            return
        vehicles_in_crossing = any(
            (vehicle.x < CROSSING_RIGHT and vehicle.x + vehicle.width > CROSSING_LEFT)
            for vehicle in self.vehicles
        )
        if vehicles_in_crossing:
            self.protected_overlap_seconds += dt

    def _append_timeline(self, clock: float, signal: dict[str, Any], vehicle_waiting: set[str], ped_waiting_count: int) -> None:
        self.vehicle_queue_samples.append(len(vehicle_waiting))
        self.pedestrian_queue_samples.append(ped_waiting_count)
        self.timeline.append(
            {
                "t": round(min(clock, float(self.duration_seconds)), 1),
                "phase": signal.get("phase"),
                "phase_key": signal.get("phase_key"),
                "vehicle_queue": len(vehicle_waiting),
                "pedestrian_queue": ped_waiting_count,
                "vehicle_passages": self.vehicle_passages,
                "pedestrian_crossings": self.pedestrian_crossings,
                "active_rules": list(signal.get("active_rules", [])),
            }
        )

    def _finalize_open_waits(self, clock: float) -> None:
        for vehicle in self.vehicles:
            if vehicle.wait_started_s is not None:
                self.vehicle_waits.append(max(0.0, clock - vehicle.wait_started_s))
        for pedestrian in self.pedestrians:
            if pedestrian.wait_started_s is not None:
                self.pedestrian_waits.append(max(0.0, clock - pedestrian.wait_started_s))

    def _controller_stats(self) -> dict[str, Any]:
        applications: dict[str, int] = {}
        extension_seconds = 0.0
        reduction_seconds = 0.0
        if self.controller_history_path.is_file():
            for line in self.controller_history_path.read_text(encoding="utf-8").splitlines():
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
            "rule_application_count": sum(applications.values()),
            "rule_applications": dict(sorted(applications.items())),
            "extension_seconds": round(extension_seconds, 1),
            "reduction_seconds": round(reduction_seconds, 1),
        }

    def _build_result(self, last_signal: dict[str, Any] | None, controller_stats: dict[str, Any]) -> dict[str, Any]:
        duration_minutes = self.duration_seconds / 60.0
        vehicle_green_seconds = self.phase_time_seconds.get("vehicle_green", 0.0)
        return {
            "mode": self.mode,
            "metrics": {
                "waiting": {
                    "vehicle": _distribution(self.vehicle_waits),
                    "pedestrian": _distribution(self.pedestrian_waits),
                },
                "queues": {
                    "vehicle": _queue_distribution(self.vehicle_queue_samples, self.vehicle_queue_seconds, self.vehicle_queue_occupied_seconds, self.duration_seconds),
                    "pedestrian": _queue_distribution(self.pedestrian_queue_samples, self.pedestrian_queue_seconds, self.pedestrian_queue_occupied_seconds, self.duration_seconds),
                    "simultaneous_queue_seconds": round(self.simultaneous_queue_seconds, 2),
                    "simultaneous_queue_share_percent": round(self.simultaneous_queue_seconds / self.duration_seconds * 100.0, 1),
                },
                "throughput": {
                    "vehicle_passages": self.vehicle_passages,
                    "pedestrian_crossings": self.pedestrian_crossings,
                    "vehicle_per_minute": round(self.vehicle_passages / duration_minutes, 2) if duration_minutes else 0.0,
                    "pedestrian_per_minute": round(self.pedestrian_crossings / duration_minutes, 2) if duration_minutes else 0.0,
                    "combined_services": self.vehicle_passages + self.pedestrian_crossings,
                    "combined_services_per_minute": round((self.vehicle_passages + self.pedestrian_crossings) / duration_minutes, 2) if duration_minutes else 0.0,
                    "vehicle_passages_per_green_minute": round(self.vehicle_passages / (vehicle_green_seconds / 60.0), 2) if vehicle_green_seconds > 0 else 0.0,
                },
                "signal": {
                    "phase_time_seconds": {key: round(value, 1) for key, value in sorted(self.phase_time_seconds.items())},
                    "phase_share_percent": {
                        key: round(value / self.duration_seconds * 100.0, 1)
                        for key, value in sorted(self.phase_time_seconds.items())
                    },
                    "phase_transitions": self.phase_transitions,
                    "cycles_completed": self.cycles_completed,
                    "clearance_time_seconds": round(self.phase_time_seconds.get("vehicle_yellow", 0.0) + self.phase_time_seconds.get("all_red", 0.0), 1),
                    "clearance_share_percent": round((self.phase_time_seconds.get("vehicle_yellow", 0.0) + self.phase_time_seconds.get("all_red", 0.0)) / self.duration_seconds * 100.0, 1),
                    **controller_stats,
                },
                "diagnostics": {
                    "protected_overlap_seconds": round(self.protected_overlap_seconds, 1),
                    "protected_overlap_detected": self.protected_overlap_seconds > 0.05,
                    "note": "Simulation diagnostic only; this is not a public-road safety certification metric.",
                },
            },
            "final_signal": last_signal,
            "timeline": self.timeline,
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
        return {"count": 0, "average_seconds": 0.0, "median_seconds": 0.0, "p95_seconds": 0.0, "max_seconds": 0.0, "total_seconds": 0.0}
    return {
        "count": len(values),
        "average_seconds": round(sum(values) / len(values), 2),
        "median_seconds": round(_percentile(values, 0.5), 2),
        "p95_seconds": round(_percentile(values, 0.95), 2),
        "max_seconds": round(max(values), 2),
        "total_seconds": round(sum(values), 2),
    }


def _queue_distribution(values: list[int], queue_seconds: float, occupied_seconds: float, duration_seconds: float) -> dict[str, Any]:
    return {
        "sample_count": len(values),
        "average": round(sum(values) / len(values), 2) if values else 0.0,
        "p95": round(_percentile(values, 0.95), 2),
        "max": max(values, default=0),
        "queue_seconds": round(queue_seconds, 2),
        "occupied_seconds": round(occupied_seconds, 2),
        "occupied_share_percent": round(occupied_seconds / duration_seconds * 100.0, 1) if duration_seconds else 0.0,
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


class SimulationExperimentService:
    """Run and persist deterministic Fixed-vs-Adaptive prototype comparisons."""

    def __init__(
        self,
        *,
        storage_root: Path | None = None,
        config_provider: Callable[[], dict[str, Any]] | None = None,
        zones_provider: Callable[[], list[dict[str, Any]]] | None = None,
    ) -> None:
        self._storage_root = (storage_root or DEFAULT_STORAGE_ROOT).expanduser().resolve()
        self._config_provider = config_provider or signal_rules_service.get_config
        self._zones_provider = zones_provider or zone_service.zones

    def run(
        self,
        *,
        duration_seconds: int,
        density: str,
        seed: int,
        sample_interval_seconds: int,
        profile: str | None,
        label: str = "",
    ) -> dict[str, Any]:
        density = density.strip().lower()
        if density not in DENSITIES:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "Experiment density must be light, normal, or busy.", status_code=422)
        if not 30 <= int(duration_seconds) <= 1800:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "Experiment duration must be between 30 and 1800 seconds.", status_code=422)
        if not 1 <= int(sample_interval_seconds) <= 10:
            raise AppError(ErrorCode.TRAFFIC_RULE_INVALID, "Experiment sample interval must be between 1 and 10 seconds.", status_code=422)

        policy = deepcopy(self._config_provider())
        profiles = policy.get("profiles") if isinstance(policy, dict) else None
        selected_profile = profile or str(policy.get("active_profile") or "")
        if not isinstance(profiles, dict) or selected_profile not in profiles:
            raise AppError(
                ErrorCode.TRAFFIC_RULE_INVALID,
                "Experiment profile must identify an existing signal profile.",
                status_code=422,
                details={"profile": selected_profile, "available_profiles": sorted(profiles or {})},
            )
        policy["active_profile"] = selected_profile
        zones = deepcopy(self._zones_provider())

        created_at_ms = int(time.time() * 1000)
        run_id = f"exp_{created_at_ms}_{uuid.uuid4().hex[:8]}"
        with tempfile.TemporaryDirectory(prefix="aitl_experiment_") as temporary:
            temp_root = Path(temporary)
            fixed = _ModeSimulation(
                mode="fixed",
                density=density,
                seed=int(seed),
                duration_seconds=int(duration_seconds),
                sample_interval_seconds=int(sample_interval_seconds),
                policy_config=policy,
                zones=zones,
                temp_root=temp_root,
            ).run()
            adaptive = _ModeSimulation(
                mode="adaptive",
                density=density,
                seed=int(seed),
                duration_seconds=int(duration_seconds),
                sample_interval_seconds=int(sample_interval_seconds),
                policy_config=policy,
                zones=zones,
                temp_root=temp_root,
            ).run()

        result = {
            "run_id": run_id,
            "created_at_ms": created_at_ms,
            "label": label.strip(),
            "scenario": {
                "duration_seconds": int(duration_seconds),
                "density": density,
                "seed": int(seed),
                "sample_interval_seconds": int(sample_interval_seconds),
                "profile": selected_profile,
                "comparison": ["fixed", "adaptive"],
                "zones": [
                    {"id": zone.get("id"), "label": zone.get("label"), "type": zone.get("type")}
                    for zone in zones
                    if zone.get("type") not in {"ignore", "counting_line"}
                ],
            },
            "fixed": fixed,
            "adaptive": adaptive,
            "comparison": self._comparison(fixed, adaptive),
            "prototype_only": True,
            "scope_note": "Controlled local simulation benchmark only; results do not establish public-road performance or safety.",
        }
        self._write_run(result)
        self._trim_old_runs()
        return result

    def list(self, limit: int = 50) -> dict[str, Any]:
        limit = max(1, min(int(limit), 200))
        try:
            paths = sorted(self._storage_root.glob("exp_*.json"), key=lambda path: path.stat().st_mtime_ns, reverse=True) if self._storage_root.is_dir() else []
            items: list[dict[str, Any]] = []
            for path in paths[:limit]:
                try:
                    payload = read_json(path)
                except (OSError, json.JSONDecodeError, TypeError):
                    continue
                if not isinstance(payload, dict):
                    continue
                items.append(self._summary(payload))
        except OSError as exc:
            raise AppError(ErrorCode.TRAFFIC_EXPERIMENT_READ_FAILED, status_code=500) from exc
        return {"experiments": items, "total": len(paths), "storage_path": self._relative_storage_root(), "prototype_only": True}

    def get(self, run_id: str) -> dict[str, Any]:
        path = self._run_path(run_id)
        if not path.is_file():
            raise AppError(ErrorCode.TRAFFIC_EXPERIMENT_READ_FAILED, "Simulation experiment was not found.", status_code=404, details={"run_id": run_id})
        try:
            payload = read_json(path)
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            raise AppError(ErrorCode.TRAFFIC_EXPERIMENT_READ_FAILED, status_code=500, details={"run_id": run_id}) from exc
        if not isinstance(payload, dict):
            raise AppError(ErrorCode.TRAFFIC_EXPERIMENT_READ_FAILED, "Stored simulation experiment is invalid.", status_code=500, details={"run_id": run_id})
        return payload

    def delete(self, run_id: str) -> dict[str, Any]:
        path = self._run_path(run_id)
        if not path.exists():
            raise AppError(ErrorCode.TRAFFIC_EXPERIMENT_READ_FAILED, "Simulation experiment was not found.", status_code=404, details={"run_id": run_id})
        try:
            path.unlink()
        except OSError as exc:
            raise AppError(ErrorCode.TRAFFIC_EXPERIMENT_DELETE_FAILED, status_code=500, details={"run_id": run_id}) from exc
        return {"deleted": True, "run_id": run_id}

    def export_csv(self, run_id: str) -> str:
        result = self.get(run_id)
        fixed_timeline = result.get("fixed", {}).get("timeline", [])
        adaptive_timeline = result.get("adaptive", {}).get("timeline", [])
        rows = max(len(fixed_timeline), len(adaptive_timeline))
        output = StringIO()
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow([
            "t_seconds",
            "fixed_phase", "fixed_vehicle_queue", "fixed_pedestrian_queue", "fixed_vehicle_passages", "fixed_pedestrian_crossings", "fixed_active_rules",
            "adaptive_phase", "adaptive_vehicle_queue", "adaptive_pedestrian_queue", "adaptive_vehicle_passages", "adaptive_pedestrian_crossings", "adaptive_active_rules",
        ])
        for index in range(rows):
            fixed = fixed_timeline[index] if index < len(fixed_timeline) else {}
            adaptive = adaptive_timeline[index] if index < len(adaptive_timeline) else {}
            writer.writerow([
                fixed.get("t", adaptive.get("t", "")),
                fixed.get("phase", ""), fixed.get("vehicle_queue", ""), fixed.get("pedestrian_queue", ""), fixed.get("vehicle_passages", ""), fixed.get("pedestrian_crossings", ""), "|".join(fixed.get("active_rules", [])),
                adaptive.get("phase", ""), adaptive.get("vehicle_queue", ""), adaptive.get("pedestrian_queue", ""), adaptive.get("vehicle_passages", ""), adaptive.get("pedestrian_crossings", ""), "|".join(adaptive.get("active_rules", [])),
            ])
        return output.getvalue()

    def _write_run(self, result: dict[str, Any]) -> None:
        try:
            write_json_atomic(self._run_path(str(result["run_id"])), result)
        except (OSError, TypeError, ValueError) as exc:
            logger.exception("Simulation experiment write failed")
            raise AppError(ErrorCode.TRAFFIC_EXPERIMENT_WRITE_FAILED, status_code=500) from exc

    def _trim_old_runs(self) -> None:
        try:
            paths = sorted(self._storage_root.glob("exp_*.json"), key=lambda path: path.stat().st_mtime_ns, reverse=True)
            for path in paths[MAX_STORED_RUNS:]:
                path.unlink(missing_ok=True)
        except OSError:
            logger.warning("Simulation experiment retention cleanup failed", exc_info=True)

    def _run_path(self, run_id: str) -> Path:
        if not RUN_ID_PATTERN.fullmatch(run_id):
            raise AppError(ErrorCode.TRAFFIC_EXPERIMENT_READ_FAILED, "Simulation experiment id is invalid.", status_code=422, details={"run_id": run_id})
        return self._storage_root / f"{run_id}.json"

    def _relative_storage_root(self) -> str:
        try:
            return str(self._storage_root.relative_to(PROJECT_ROOT)).replace("\\", "/")
        except ValueError:
            return str(self._storage_root)

    @staticmethod
    def _summary(payload: dict[str, Any]) -> dict[str, Any]:
        comparison = payload.get("comparison") if isinstance(payload.get("comparison"), dict) else {}
        return {
            "run_id": payload.get("run_id"),
            "created_at_ms": payload.get("created_at_ms"),
            "label": payload.get("label", ""),
            "scenario": payload.get("scenario", {}),
            "headline": {
                "vehicle_wait": comparison.get("vehicle_wait_average"),
                "pedestrian_wait": comparison.get("pedestrian_wait_average"),
                "vehicle_throughput": comparison.get("vehicle_throughput"),
                "pedestrian_throughput": comparison.get("pedestrian_throughput"),
            },
        }

    @staticmethod
    def _comparison(fixed: dict[str, Any], adaptive: dict[str, Any]) -> dict[str, Any]:
        fixed_metrics = fixed["metrics"]
        adaptive_metrics = adaptive["metrics"]
        return {
            "vehicle_wait_average": _delta(fixed_metrics["waiting"]["vehicle"]["average_seconds"], adaptive_metrics["waiting"]["vehicle"]["average_seconds"], lower_is_better=True),
            "vehicle_wait_p95": _delta(fixed_metrics["waiting"]["vehicle"]["p95_seconds"], adaptive_metrics["waiting"]["vehicle"]["p95_seconds"], lower_is_better=True),
            "pedestrian_wait_average": _delta(fixed_metrics["waiting"]["pedestrian"]["average_seconds"], adaptive_metrics["waiting"]["pedestrian"]["average_seconds"], lower_is_better=True),
            "pedestrian_wait_p95": _delta(fixed_metrics["waiting"]["pedestrian"]["p95_seconds"], adaptive_metrics["waiting"]["pedestrian"]["p95_seconds"], lower_is_better=True),
            "vehicle_queue_average": _delta(fixed_metrics["queues"]["vehicle"]["average"], adaptive_metrics["queues"]["vehicle"]["average"], lower_is_better=True),
            "pedestrian_queue_average": _delta(fixed_metrics["queues"]["pedestrian"]["average"], adaptive_metrics["queues"]["pedestrian"]["average"], lower_is_better=True),
            "vehicle_throughput": _delta(fixed_metrics["throughput"]["vehicle_per_minute"], adaptive_metrics["throughput"]["vehicle_per_minute"], lower_is_better=False),
            "pedestrian_throughput": _delta(fixed_metrics["throughput"]["pedestrian_per_minute"], adaptive_metrics["throughput"]["pedestrian_per_minute"], lower_is_better=False),
            "vehicle_green_efficiency": _delta(fixed_metrics["throughput"]["vehicle_passages_per_green_minute"], adaptive_metrics["throughput"]["vehicle_passages_per_green_minute"], lower_is_better=False),
            "combined_throughput": _delta(fixed_metrics["throughput"]["combined_services_per_minute"], adaptive_metrics["throughput"]["combined_services_per_minute"], lower_is_better=False),
            "simultaneous_queue_time": _delta(fixed_metrics["queues"]["simultaneous_queue_seconds"], adaptive_metrics["queues"]["simultaneous_queue_seconds"], lower_is_better=True),
            "protected_overlap_seconds": _delta(fixed_metrics["diagnostics"]["protected_overlap_seconds"], adaptive_metrics["diagnostics"]["protected_overlap_seconds"], lower_is_better=True),
        }


simulation_experiment_service = SimulationExperimentService()
