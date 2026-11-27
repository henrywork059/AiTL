"""Occupancy-protected recirculating pixel world; simulation only.

Preserves production geometry, slot types, speed, following gap and respawn.
Initial vehicle queues are placed upstream rather than inside the service gate.
No metre calibration, SUMO equivalence, or physical control is implied.
"""
from __future__ import annotations

from app.services.legacy_world import (
    EASTBOUND_STOP_LINE, WESTBOUND_STOP_LINE, CROSSING_LEFT, CROSSING_RIGHT,
    TOP_PEDESTRIAN_WAIT_Y, BOTTOM_PEDESTRIAN_WAIT_Y, advance_vehicles,
    advance_pedestrians,
)


class ProtectedCrosswalk:
    def __init__(self, vehicles, pedestrians, rng):
        self.vehicles = vehicles
        self.pedestrians = pedestrians
        self.rng = rng
        self.vehicle_visits = [0] * len(vehicles)
        self.pedestrian_visits = [0] * len(pedestrians)
        self._vehicle_slots = {id(v): i for i, v in enumerate(vehicles)}
        self._pedestrian_slots = {id(p): i for i, p in enumerate(pedestrians)}
        # Keep existing slot ordering and demand; eliminate initial gate occupancy.
        for direction in (1, -1):
            group = sorted((v for v in vehicles if v.direction == direction),
                           key=lambda v: v.x, reverse=direction > 0)
            limit = EASTBOUND_STOP_LINE - 8 if direction > 0 else WESTBOUND_STOP_LINE + 8
            for v in group:
                if direction > 0:
                    v.x = min(v.x, limit - v.width)
                    limit = v.x - 22.0
                else:
                    v.x = max(v.x, limit)
                    limit = v.x + v.width + 22.0
        for p in pedestrians:
            p.y = min(p.y, TOP_PEDESTRIAN_WAIT_Y) if p.direction > 0 else max(p.y, BOTTOM_PEDESTRIAN_WAIT_Y)

    def occupancy(self):
        # Once the front crosses its stop line, hold the opposing admission
        # until the rear has cleared the crossing. A walker is committed from
        # curb departure to the opposite curb, including clearance.
        vehicles = any((v.direction > 0 and v.x + v.width > EASTBOUND_STOP_LINE and v.x < CROSSING_RIGHT) or
                       (v.direction < 0 and v.x < WESTBOUND_STOP_LINE and v.x + v.width > CROSSING_LEFT)
                       for v in self.vehicles)
        pedestrians = any(TOP_PEDESTRIAN_WAIT_Y < p.y < BOTTOM_PEDESTRIAN_WAIT_Y for p in self.pedestrians)
        return vehicles, pedestrians

    def permission(self, requested):
        vehicles, pedestrians = self.occupancy()
        if vehicles and pedestrians:
            raise RuntimeError("Conflicting protected crosswalk occupancy")
        if requested == "vehicle_green" and not pedestrians:
            return "vehicle_green"
        if requested == "pedestrian_green" and not vehicles:
            return "pedestrian_green"
        return "all_red"

    def step(self, dt, requested):
        applied = self.permission(requested)
        def vehicle_reentry(vehicle):
            self.vehicle_visits[self._vehicle_slots[id(vehicle)]] += 1
        def pedestrian_move(person, old_y, completed):
            if (person.direction > 0 and person.y < old_y) or (person.direction < 0 and person.y > old_y):
                self.pedestrian_visits[self._pedestrian_slots[id(person)]] += 1
        advance_vehicles(self.vehicles, self.rng, dt, applied == "vehicle_green", on_respawn=vehicle_reentry, monotonic=True)
        advance_pedestrians(self.pedestrians, self.rng, dt, applied == "pedestrian_green", on_move=pedestrian_move)
        # Assert the resulting state before the owner publishes it.
        self.permission("all_red")
        return applied
