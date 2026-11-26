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
