"""Experimental native geometry projection; never an authoritative camera frame.

One isotropic transform for network geometry and observations. Four image views
are exact flips, and exports use the same transform. No legacy road geometry,
agent slots, detections, or traffic policy is synthesized here.
"""
from __future__ import annotations

import csv
from copy import deepcopy
from dataclasses import dataclass
import io
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import cv2
import numpy as np

from app.services.sumo_shadow_adapter import ShadowSnapshot
from app.services.observation_identity import (SIMULATION_VIEW_FLIPS, simulation_view_point,
    SUMO_EVALUATION_ORIGIN, EVALUATION_ORIGINS)

WIDTH, HEIGHT = 1280, 720
MARGIN = 24
VIEW_FLIPS = SIMULATION_VIEW_FLIPS
PROVENANCE = SUMO_EVALUATION_ORIGIN
# Exact BGR colours of the native synthetic raster, in stable index order.
RASTER_PALETTE = ((29,33,37),(75,80,86),(130,137,142),(225,225,225),
                  (255,170,65),(225,240,255),(65,220,245))


def raster_color(color, indexed):
    return RASTER_PALETTE.index(color) if indexed else color


@dataclass(frozen=True)
class LaneShape:
    ident: str
    kind: str
    points: tuple[tuple[float, float], ...]
    width_m: float
    surface: str = "stroke"


@dataclass(frozen=True)
class Projection:
    bounds: tuple[float, float, float, float]
    scale: float
    offset_x: float
    offset_y: float
    lanes: tuple[LaneShape, ...]

    @classmethod
    def load(cls, path: Path, *, walking_area_polygons=False) -> Projection:
        root = ET.parse(path).getroot()
        lanes = []
        for edge in root.findall("edge"):
            function = edge.get("function", "")
            for lane in edge.findall("lane"):
                points = tuple(tuple(float(v) for v in xy.split(",")[:2])
                               for xy in lane.attrib["shape"].split())
                width = float(lane.get("width", "3.2"))
                if len(points) < 2 or any(len(pt) != 2 or not all(map(math.isfinite, pt)) for pt in points) or not math.isfinite(width) or width <= 0:
                    raise ValueError("Invalid native lane geometry")
                kind = "crossing" if function == "crossing" else (
                    "walk" if function == "walkingarea" or lane.get("allow") == "pedestrian" else "road")
                # netconvert walkingarea shape is a boundary polygon, not a lane centreline.
                surface="polygon" if walking_area_polygons and function=="walkingarea" else "stroke"
                lanes.append(LaneShape(lane.attrib["id"], kind, points, width,surface))
        if not lanes or len({lane.ident for lane in lanes}) != len(lanes):
            raise ValueError("Missing or duplicate native lanes")
        # Include lane extents in bounds, not only the centre lines.
        lo_x = min(x - lane.width_m / 2 for lane in lanes for x, _ in lane.points)
        hi_x = max(x + lane.width_m / 2 for lane in lanes for x, _ in lane.points)
        lo_y = min(y - lane.width_m / 2 for lane in lanes for _, y in lane.points)
        hi_y = max(y + lane.width_m / 2 for lane in lanes for _, y in lane.points)
        scale = min((WIDTH - 2 * MARGIN) / (hi_x - lo_x),
                    (HEIGHT - 2 * MARGIN) / (hi_y - lo_y))
        return cls((lo_x, lo_y, hi_x, hi_y), scale,
                   (WIDTH - scale * (hi_x - lo_x)) / 2,
                   (HEIGHT - scale * (hi_y - lo_y)) / 2, tuple(lanes))

    def pixel(self, x: float, y: float, source_id: str = "simulation_camera") -> tuple[float, float]:
        if source_id not in VIEW_FLIPS or not all(map(math.isfinite, (x, y))):
            raise ValueError("Invalid projection input")
        lo_x, lo_y, hi_x, hi_y = self.bounds
        px = self.offset_x + (x - lo_x) * self.scale
        py = self.offset_y + (hi_y - y) * self.scale
        if not (0 <= px < WIDTH and 0 <= py < HEIGHT):
            raise ValueError("Native agent outside projection canvas")
        return simulation_view_point(px, py, WIDTH, HEIGHT, source_id)

    def world(self, px: float, py: float, source_id: str = "simulation_camera") -> tuple[float, float]:
        if source_id not in VIEW_FLIPS or not all(map(math.isfinite, (px, py))) or not (0 <= px < WIDTH and 0 <= py < HEIGHT):
            raise ValueError("Invalid pixel coordinate")
        flip = VIEW_FLIPS[source_id]
        if flip in (1, -1):
            px = WIDTH - 1 - px
        if flip in (0, -1):
            py = HEIGHT - 1 - py
        return (self.bounds[0] + (px - self.offset_x) / self.scale,
                self.bounds[3] - (py - self.offset_y) / self.scale)

    def geometry_canvas(self, *, indexed=False) -> np.ndarray:
        canvas = np.full((HEIGHT, WIDTH) if indexed else (HEIGHT, WIDTH, 3), raster_color(RASTER_PALETTE[0],indexed), np.uint8)
        for kind, bgr in (("road", RASTER_PALETTE[1]), ("walk", RASTER_PALETTE[2]), ("crossing", RASTER_PALETTE[3])):
            color=raster_color(bgr,indexed)
            for lane in self.lanes:
                if lane.kind != kind:
                    continue
                points = np.array([tuple(round(v) for v in self.pixel(*pt)) for pt in lane.points], np.int32)
                if lane.surface=="polygon":
                    # Zero-area terminal walking areas are not thickened into fictitious roads.
                    if cv2.contourArea(points)>0:
                        cv2.fillPoly(canvas,[points],color,lineType=cv2.LINE_8)
                else:
                    cv2.polylines(canvas, [points], False, color, max(1, round(lane.width_m * self.scale)), cv2.LINE_8)
        return canvas


class NativeProjection:
    """One immutable layout per generation; callers own native session lifecycle."""
    def __init__(self, layout: Projection, generation: int, *, provenance=PROVENANCE, slot_profiles=None):
        if provenance not in EVALUATION_ORIGINS:
            raise ValueError("Invalid isolated projection provenance")
        self.provenance = provenance
        self.layout = layout
        self.generation = generation
        self._slot_profiles = deepcopy(slot_profiles) if slot_profiles is not None else None
        # Scene-only runs do not allocate the full raster.
        self._background = None
        self._metadata_cache = None
        # Static geometry is projected once per generation and view. Public
        # scenes receive detached lane data, so consumers cannot mutate the cache.
        self._lanes_by_view = {
            sid: [{"id": lane.ident, "kind": lane.kind,
                   "points": [layout.pixel(*pt, sid) for pt in lane.points],
                   "width_px": lane.width_m * layout.scale,
                   **({"surface":"polygon"} if lane.surface=="polygon" else {})} for lane in layout.lanes]
            for sid in VIEW_FLIPS
        }
        manifest = {"schema":1,"width":WIDTH,"height":HEIGHT,"bounds":layout.bounds,
                    "scale":layout.scale,"offsets":[layout.offset_x,layout.offset_y],
                    "lanes":[(lane.ident,lane.kind,lane.points,lane.width_m) for lane in layout.lanes]}
        if any(lane.surface=="polygon" for lane in layout.lanes):
            manifest["walking_area_surfaces"]="native_boundary_polygon_v1"
        if self._slot_profiles is not None:
            # Rendering contract is qualified independently of density/seed.
            manifest["agent_anchor"]="native_front_center_footprints_v1"
        self.layout_id = hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(",",":")).encode()).hexdigest()

    def metadata(self, snapshot: ShadowSnapshot) -> dict:
        if snapshot.provenance != "synthetic_sumo_shadow":
            raise ValueError("Unexpected observation provenance")
        # The adapter owns immutable snapshots. Cache only the current object,
        # never a tick key that could alias another seed or retired observation.
        cached = self._metadata_cache
        if cached is not None and snapshot is cached[0]:
            return deepcopy(cached[1])
        rows = []
        for a in snapshot.agents:
            x, y = self.layout.pixel(a.x_m, a.y_m)
            row = {"id": a.id, "kind": a.kind, "road_id": a.road_id,
                   "x_m": a.x_m, "y_m": a.y_m, "speed_m_s": a.speed_m_s,
                   "x": x, "y": y}
            if self._slot_profiles is not None:
                slot,visit=a.engine_id.rsplit("_",1)
                profile=self._slot_profiles[slot]
                if profile["kind"]!=a.kind or not visit.isdigit():
                    raise ValueError("Invalid native slot projection")
                row.update(slot_id=slot,visit=int(visit))
                if a.kind=="vehicle":
                    row.update(vehicle_type=profile["vehicle_type"],length_m=profile["length_m"],
                               width_m=profile["width_m"],eastbound=profile["eastbound"])
            rows.append(row)
        meta = {"schema_version": 1, "provenance": self.provenance, "generation": self.generation,
                "coordinate_space": "native_projection_v1", "layout_id": self.layout_id,
                "seed": snapshot.seed, "tick": snapshot.tick, "time_s": snapshot.time_s,
                "paused": snapshot.paused, "width": WIDTH, "height": HEIGHT,
                "bounds_m": self.layout.bounds, "pixels_per_m": self.layout.scale, "agents": rows}
        # Publish snapshot and metadata together: shadow scene-only reads can
        # overlap encoder reads. Never expose a mismatched pair.
        self._metadata_cache = (snapshot,meta)
        return deepcopy(meta)

    def scene(self, snapshot: ShadowSnapshot, source_id: str = "simulation_camera", *, include_lanes=True) -> dict:
        if source_id not in VIEW_FLIPS:
            raise ValueError("Unknown native view")
        meta = self.metadata(snapshot)
        flip = VIEW_FLIPS[source_id]
        if flip is not None:
            for row in meta["agents"]:
                if flip in (1, -1):
                    row["x"] = WIDTH - 1 - row["x"]
                if flip in (0, -1):
                    row["y"] = HEIGHT - 1 - row["y"]
        return {**meta, **({"lanes": deepcopy(self._lanes_by_view[source_id])} if include_lanes else {})}

    def render_pixels(self, snapshot: ShadowSnapshot, *, indexed=False) -> tuple[dict, np.ndarray]:
        """One canonical image; callers may encode individual mirrored views."""
        meta = self.metadata(snapshot)
        if self._background is None or self._background.ndim!=(2 if indexed else 3):
            self._background = self.layout.geometry_canvas(indexed=indexed)
        image = self._background.copy()
        for row in meta["agents"]:
            # Native vehicle position is its front centre. Draw a physically
            # dimensioned footprint behind that anchor, not a detector box.
            if "length_m" in row:
                x,y=row["x"],row["y"]
                tail=x+(-1 if row["eastbound"] else 1)*row["length_m"]*self.layout.scale
                half=row["width_m"]*self.layout.scale/2
                left,right=sorted((round(x),round(tail)))
                top,bottom=round(y-half),round(y+half)
                cv2.rectangle(image,(left,top),(right,bottom),raster_color(RASTER_PALETTE[4],indexed),-1)
                cv2.line(image,(round(x),top),(round(x),bottom),raster_color(RASTER_PALETTE[5],indexed),1)
            else:
                radius=max(1,round(.25*self.layout.scale)) if self._slot_profiles is not None else (4 if row["kind"]=="vehicle" else 3)
                cv2.circle(image,(round(row["x"]),round(row["y"])),radius,
                           raster_color(RASTER_PALETTE[4 if row["kind"]=="vehicle" else 6],indexed),-1)
        return meta, image

    def render(self, snapshot: ShadowSnapshot) -> tuple[dict, dict[str, bytes]]:
        meta, image = self.render_pixels(snapshot)
        views = {}
        for sid, flip in VIEW_FLIPS.items():
            view = image if flip is None else cv2.flip(image, flip)
            ok, encoded = cv2.imencode(".png", view)
            if not ok:
                raise RuntimeError("Native projection PNG encoding failed")
            views[sid] = encoded.tobytes()
        return meta, views


def export_csv(meta: dict) -> str:
    if meta.get("provenance") not in EVALUATION_ORIGINS:
        raise ValueError("Not an isolated evaluation projection export")
    output = io.StringIO(newline="")
    fields = ("provenance", "generation", "seed", "tick", "time_s", "id", "kind", "road_id",
              "x_m", "y_m", "speed_m_s", "x", "y")
    if meta.get("demand_model")=="native_cyclic_slots_v1":
        fields += ("slot_id","visit","vehicle_type","length_m","width_m","eastbound")
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for agent in meta["agents"]:
        writer.writerow({**{key: meta[key] for key in fields[:5]}, **agent})
    return output.getvalue()
