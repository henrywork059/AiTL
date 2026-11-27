"""Native draft regions; use existing native_projection_v1 and layout identity."""
from __future__ import annotations
import math
from app.services.sumo_projection import WIDTH, HEIGHT

def region_counts(scene,polygon):
    """Strict convex quadrilateral in the exact view. Boundary counts as inside."""
    if len(polygon)!=4 or any(len(pt)!=2 for pt in polygon):
        raise ValueError("Exactly four vertices required")
    points=[tuple(pt) for pt in polygon]
    if any(not all(type(v) in (float,int) and math.isfinite(v) for v in pt) or
           not (0<=pt[0]<WIDTH and 0<=pt[1]<HEIGHT) for pt in points):
        raise ValueError("Vertex outside native image")
    def cross(a,b,c):
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    turns=[cross(points[i],points[(i+1)%4],points[(i+2)%4]) for i in range(4)]
    if not (all(v>1e-6 for v in turns) or all(v< -1e-6 for v in turns)):
        raise ValueError("Vertices must form a convex ordered quadrilateral")
    counts={"vehicle":0,"pedestrian":0}
    ids=[]
    for agent in scene["agents"]:
        p=(agent["x"],agent["y"])
        edges=[cross(points[i],points[(i+1)%4],p) for i in range(4)]
        if all(v>=-1e-6 for v in edges) or all(v<=1e-6 for v in edges):
            counts[agent["kind"]]+=1
            ids.append(agent["id"])
    return {"counts":counts,"agent_ids":sorted(ids),"polygon":points}


def legacy_rectangle_preview(scene, polygon, view_id):
    """Semantic midblock preview only, not camera calibration.

    Map four rectangular legacy pixel vertices via ordered road/crossing
    landmarks in the actual generated native scene. The nonuniform transform
    changes scale between bands; arbitrary slanted polygons are deliberately
    rejected because their edges could bend at a band boundary.
    """
    from app.services.legacy_world import ROAD_TOP, ROAD_BOTTOM, CROSSING_LEFT, CROSSING_RIGHT
    from app.services.observation_identity import simulation_view_point
    from app.services.sumo_midblock_fixture import MIDBLOCK_GEOMETRIES
    if scene.get("geometry") not in MIDBLOCK_GEOMETRIES or scene.get("engine") != "native":
        raise ValueError("Legacy preview requires native midblock geometry")
    points=region_counts({"agents":[]},polygon)["polygon"]
    if any(not (0<=x<=WIDTH-1 and 0<=y<=HEIGHT-1) for x,y in points):
        raise ValueError("Legacy preview requires mirrorable pixel centres")
    canonical=[simulation_view_point(x,y,WIDTH,HEIGHT,view_id) for x,y in points]
    xs=sorted({x for x,y in canonical})
    ys=sorted({y for x,y in canonical})
    if len(xs)!=2 or len(ys)!=2 or set(canonical)!={(x,y) for x in xs for y in ys}:
        raise ValueError("Only axis-aligned rectangular legacy regions can be previewed")
    lanes={l["id"]:l for l in scene["lanes"]}
    crossings=[l for l in lanes.values() if l["kind"]=="crossing"]
    if len(crossings)!=1 or any(key not in lanes for key in ("WC_1","EC_1","NC_0","CS_0")):
        raise ValueError("Missing midblock preview landmarks")
    crossing=crossings[0]
    cp=crossing["points"]
    if len(cp)!=2 or abs(cp[0][0]-cp[1][0])>1e-6:
        raise ValueError("Unsupported crossing geometry")
    centre=cp[0][0]
    half=crossing["width_px"]/2
    road_x=[x for key in ("WC_1","EC_1") for x,y in lanes[key]["points"]]
    walk_y=[y for key in ("NC_0","CS_0") for x,y in lanes[key]["points"]]
    sx=(0,CROSSING_LEFT,CROSSING_RIGHT,WIDTH-1)
    sy=(0,ROAD_TOP,ROAD_BOTTOM,HEIGHT-1)
    tx=(min(road_x),centre-half,centre+half,max(road_x))
    ty=(min(walk_y),min(y for x,y in cp),max(y for x,y in cp),max(walk_y))
    for knots in (tx,ty):
        if not all(math.isfinite(v) for v in knots) or any(a>=b for a,b in zip(knots,knots[1:])):
            raise ValueError("Nonmonotonic midblock landmarks")
    if not (0<=tx[0]<tx[-1]<=WIDTH-1 and 0<=ty[0]<ty[-1]<=HEIGHT-1):
        raise ValueError("Midblock landmarks outside image")
    def interpolate(value,source,target):
        for i in range(3):
            if source[i]<=value<=source[i+1]:
                return target[i]+(target[i+1]-target[i])*(value-source[i])/(source[i+1]-source[i])
        raise ValueError("Point outside preview domain")
    mapped=[simulation_view_point(interpolate(x,sx,tx),interpolate(y,sy,ty),WIDTH,HEIGHT,view_id)
            for x,y in canonical]
    return {"polygon":[list(p) for p in mapped],"original_polygon":[list(p) for p in points],
            "mapping_contract":"semantic_midblock_rectangle_preview_v1",
            "landmarks":{"legacy_x":list(sx),"legacy_y":list(sy),"native_x":list(tx),"native_y":list(ty)},
            "calibrated":False,"legacy_editor_compatible":False,"persisted":False,
            "detector_input_eligible":False,"physical_output_allowed":False}
