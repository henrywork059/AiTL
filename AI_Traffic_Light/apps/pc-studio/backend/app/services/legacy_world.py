"""Shared synthetic pixel-world motion and deterministic demand; no policy or I/O."""
from __future__ import annotations
from dataclasses import dataclass

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
DENSITY_COUNTS = {"light": (4, 4), "normal": (8, 7), "busy": (12, 11)}
DENSITY_SEED_OFFSETS = {"light": 101, "normal": 211, "busy": 307}
VEHICLE_WIDTHS = {"car": (125, 155), "suv": (145, 175), "van": (170, 205), "bus": (220, 255)}


@dataclass(frozen=True)
class VehicleSpec:
    x: float
    y: int
    width: int
    speed: float
    direction: int
    vehicle_type: str


@dataclass(frozen=True)
class PedestrianSpec:
    x: int
    y: float
    speed: float
    direction: int


def vehicle_specs(density, rng, *, live_slots=True):
    for index in range(DENSITY_COUNTS[density][0]):
        direction = 1 if index % 2 == 0 else -1
        lane_index = index // 2
        if live_slots:
            kind = ("car", "suv", "van", "bus")[index % 4]
            width = rng.randint(*VEHICLE_WIDTHS[kind])
        else:
            kind = "bus" if index % 5 == 4 else "car"
            width = 220 if kind == "bus" else rng.randint(125, 170)
        x = -240.0 + lane_index * 300 if direction > 0 else float(FRAME_WIDTH + 60 - width - lane_index * 300)
        yield VehicleSpec(x, 265 if direction > 0 else 455, width,
                          float(rng.randint(92, 125)), direction, kind)


def pedestrian_specs(density, rng):
    for index in range(DENSITY_COUNTS[density][1]):
        direction = 1 if index % 2 == 0 else -1
        x = CROSSING_LEFT + 42 + (index * 47) % (CROSSING_RIGHT - CROSSING_LEFT - 84)
        y = float(max(65, TOP_PEDESTRIAN_WAIT_Y - (index // 2) * 22)) if direction > 0 else float(min(710, BOTTOM_PEDESTRIAN_WAIT_Y + (index // 2) * 18))
        yield PedestrianSpec(x, y, float(rng.randint(88, 106)), direction)


def advance_vehicles(vehicles, rng, dt, vehicle_go, *, on_move=None, on_respawn=None):
    """Preserve legacy following/stop-line behavior; callbacks precede reentry."""
    for direction in (1, -1):
        group = sorted((v for v in vehicles if v.direction * direction > 0),
                       key=lambda item: item.x, reverse=direction > 0)
        ahead = None
        for vehicle in group:
            old_x = vehicle.x
            proposed = old_x + vehicle.speed * dt * vehicle.direction
            if direction > 0:
                committed = old_x + vehicle.width > EASTBOUND_STOP_LINE
                if not vehicle_go and not committed:
                    proposed = min(proposed, EASTBOUND_STOP_LINE - 8 - vehicle.width)
                if ahead is not None:
                    proposed = min(proposed, ahead.x - 22.0 - vehicle.width)
            else:
                committed = old_x < WESTBOUND_STOP_LINE
                if not vehicle_go and not committed:
                    proposed = max(proposed, WESTBOUND_STOP_LINE + 8)
                if ahead is not None:
                    proposed = max(proposed, ahead.x + ahead.width + 22.0)
            vehicle.x = proposed
            if on_move is not None:
                on_move(vehicle, old_x, committed)
            ahead = vehicle
    for vehicle in vehicles:
        if vehicle.direction > 0 and vehicle.x > FRAME_WIDTH + 120:
            peers = [item.x for item in vehicles if item.direction > 0 and item is not vehicle]
            vehicle.x = min(-vehicle.width - rng.randint(80, 180),
                            min(peers, default=-120.0) - vehicle.width - rng.randint(70, 140))
        elif vehicle.direction < 0 and vehicle.x + vehicle.width < -120:
            peers = [item.x + item.width for item in vehicles if item.direction < 0 and item is not vehicle]
            vehicle.x = max(float(FRAME_WIDTH + rng.randint(80, 180)),
                            max(peers, default=float(FRAME_WIDTH + 120)) + rng.randint(70, 140))
        else:
            continue
        if on_respawn is not None:
            on_respawn(vehicle)


def advance_pedestrians(pedestrians, rng, dt, can_start_crossing, *, on_move=None):
    for pedestrian in pedestrians:
        old_y = pedestrian.y
        if pedestrian.direction > 0:
            if pedestrian.y < TOP_PEDESTRIAN_WAIT_Y:
                pedestrian.y = min(TOP_PEDESTRIAN_WAIT_Y, pedestrian.y + pedestrian.speed * dt)
            elif pedestrian.y <= TOP_PEDESTRIAN_WAIT_Y + .5 and not can_start_crossing:
                pedestrian.y = float(TOP_PEDESTRIAN_WAIT_Y)
            else:
                pedestrian.y += pedestrian.speed * dt
            completed = old_y < BOTTOM_PEDESTRIAN_WAIT_Y <= pedestrian.y
            if pedestrian.y > FRAME_HEIGHT + 25:
                pedestrian.y = float(70 - rng.randint(0, 42))
        else:
            if pedestrian.y > BOTTOM_PEDESTRIAN_WAIT_Y:
                pedestrian.y = max(BOTTOM_PEDESTRIAN_WAIT_Y, pedestrian.y - pedestrian.speed * dt)
            elif pedestrian.y >= BOTTOM_PEDESTRIAN_WAIT_Y - .5 and not can_start_crossing:
                pedestrian.y = float(BOTTOM_PEDESTRIAN_WAIT_Y)
            else:
                pedestrian.y -= pedestrian.speed * dt
            completed = old_y > TOP_PEDESTRIAN_WAIT_Y >= pedestrian.y
            if pedestrian.y < 20:
                pedestrian.y = float(FRAME_HEIGHT - 10 + rng.randint(0, 36))
        if on_move is not None:
            on_move(pedestrian, old_y, completed)
