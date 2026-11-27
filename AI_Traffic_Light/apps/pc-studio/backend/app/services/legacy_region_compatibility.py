"""Isolated synthetic projection onto ordered legacy editor edge coordinates.

Match the production frontend regionCounts.ts assignment convention. The
piecewise semantic map is not calibrated; no detector, registry or control write.
"""
from __future__ import annotations
import math
from app.services.native_evaluation_geometry import legacy_rectangle_preview
from app.services.observation_identity import SIMULATION_VIEW_FLIPS
from app.services.legacy_world import CROSSING_LEFT,CROSSING_RIGHT,ROAD_TOP,ROAD_BOTTOM
from app.services.sumo_projection import WIDTH,HEIGHT


COORDINATE_MAPPING_CONTRACT = "semantic_midblock_image_edges_v2"


def edge_view_point(x,y,view_id):
    """Continuous image-edge coordinates, unlike raster pixel centres."""
    flip=SIMULATION_VIEW_FLIPS[view_id]
    return (WIDTH-x if flip in (1,-1) else x,
            HEIGHT-y if flip in (0,-1) else y)


def point_in_region(point,polygon):
    """Same strict ray-crossing comparison and boundary semantics as UI."""
    x,y=point
    inside=False
    j=len(polygon)-1
    for i,(xi,yi) in enumerate(polygon):
        xj,yj=polygon[j]
        if (yi>y)!=(yj>y) and x<(xj-xi)*(y-yi)/(yj-yi)+xi:
            inside=not inside
        j=i
    return inside


def _interpolate(value,source,target):
    # Endpoint arithmetic can differ by a few ulps after mirroring. Snap only
    # roundoff at knots, never clip a genuinely out-of-domain point.
    for a,b in zip(source,target):
        if math.isclose(value,a,rel_tol=0.,abs_tol=1e-9):
            return b
    for i in range(len(source)-1):
        if source[i]<value<source[i+1]:
            return target[i]+(target[i+1]-target[i])*(value-source[i])/(source[i+1]-source[i])
    return None


def _region_rows(regions):
    if not isinstance(regions,list) or not 1<=len(regions)<=32:
        raise ValueError("Provide 1-32 ordered legacy regions")
    rows=[]
    seen=set()
    for item in regions:
        ident=item["id"]
        if not isinstance(ident,str) or not 1<=len(ident)<=128 or ident in seen:
            raise ValueError("Invalid or duplicate legacy region ID")
        polygon=item["polygon"]
        if len(polygon)!=4 or any(len(p)!=2 for p in polygon):
            raise ValueError("Exactly four vertices required")
        if any(not all(type(v) in (float,int) and math.isfinite(v) for v in p) or
               not (0<=p[0]<=WIDTH and 0<=p[1]<=HEIGHT) for p in polygon):
            raise ValueError("Region vertices outside legacy editor edge plane")
        points=[tuple(p) for p in polygon]
        def cross(a,b,c):
            return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
        turns=[cross(points[i],points[(i+1)%4],points[(i+2)%4]) for i in range(4)]
        if not (all(v>1e-6 for v in turns) or all(v< -1e-6 for v in turns)):
            raise ValueError("Vertices must form a convex ordered quadrilateral")
        seen.add(ident)
        rows.append({"id":ident,"polygon":points})
    return rows


def edge_landmarks(scene):
    rectangle=[[CROSSING_LEFT,ROAD_TOP],[CROSSING_RIGHT,ROAD_TOP],
               [CROSSING_RIGHT,ROAD_BOTTOM],[CROSSING_LEFT,ROAD_BOTTOM]]
    centres=legacy_rectangle_preview(scene,rectangle,"simulation_camera")["landmarks"]
    # Legacy editor knots retain their declared semantic road landmarks. Its
    # outer endpoints are the SVG edges; native raster centre landmarks move
    # by +0.5 to the continuous box-edge plane, not to the next pixel centre.
    return {"legacy_x":[0,CROSSING_LEFT,CROSSING_RIGHT,WIDTH],
            "legacy_y":[0,ROAD_TOP,ROAD_BOTTOM,HEIGHT],
            "native_x":[v+.5 for v in centres["native_x"]],
            "native_y":[v+.5 for v in centres["native_y"]]}


def legacy_region_projection(scene,view_id,regions,boxes):
    """Inverse-map each view's own bottom centre into the saved editor plane.

    A vertical flip changes which end of a box is its bottom; neither
    vertical mirror counts nor strict polygon boundary memberships are assumed
    invariant. Slanted outlines are split at every semantic landmark. Native
    pixel-centre profiles and existing rectangle preview remain separate.
    """
    if view_id not in SIMULATION_VIEW_FLIPS:
        raise ValueError("Unknown legacy preview view")
    regions=_region_rows(regions)
    landmarks=edge_landmarks(scene)
    sx,sy,tx,ty=(landmarks[k] for k in ("legacy_x","legacy_y","native_x","native_y"))
    mapped=[]
    for region in regions:
        canonical=[edge_view_point(x,y,view_id) for x,y in region["polygon"]]
        outline=[]
        for (x,y),(u,v) in zip(canonical,canonical[1:]+canonical[:1]):
            times={0.}
            for a,b,knots in ((x,u,sx),(y,v,sy)):
                if b!=a:
                    times.update(f for k in knots[1:-1] if 0<(f:=(k-a)/(b-a))<1)
            for f in sorted(times):
                a=_interpolate(x+(u-x)*f,sx,tx)
                b=_interpolate(y+(v-y)*f,sy,ty)
                outline.append(list(edge_view_point(a,b,view_id)))
        mapped.append({"id":region["id"],"original_polygon":[list(p) for p in region["polygon"]],
                       "native_outline":outline})
    counts={r["id"]:{} for r in regions}
    kind_counts={r["id"]:{"vehicle":0,"pedestrian":0} for r in regions}
    assignments=[]
    outside=0
    for index,box in enumerate(boxes):
        coords=box["box_xyxy"]
        if len(coords)!=4 or not all(type(v) in (int,float) and math.isfinite(v) for v in coords):
            raise ValueError("Invalid detection box")
        x1,y1,x2,y2=coords
        if not (0<=x1<x2<=WIDTH and 0<=y1<y2<=HEIGHT) or box["kind"] not in {"vehicle","pedestrian"}:
            raise ValueError("Invalid detection box bounds or kind")
        native=((x1+x2)*.5,y2)
        x,y=edge_view_point(*native,view_id)
        a,b=_interpolate(x,tx,sx),_interpolate(y,ty,sy)
        legacy=None if a is None or b is None else list(edge_view_point(a,b,view_id))
        ident=None
        if legacy is None:
            outside+=1
        else:
            ident=next((r["id"] for r in regions if point_in_region(legacy,r["polygon"])),None)
        if ident is not None:
            name=box.get("class_name",box["kind"])
            counts[ident][name]=counts[ident].get(name,0)+1
            kind_counts[ident][box["kind"]]+=1
        assignments.append({"index":index,"agent_id":box.get("agent_id"),"native_bottom_center":list(native),
                            "legacy_point":legacy,"region_id":ident})
    return {"contract":"legacy_ui_bottom_center_first_match_semantic_v1","source_id":view_id,
            "coordinate_mapping_contract":COORDINATE_MAPPING_CONTRACT,"landmarks":landmarks,
            "native_layout_id":scene["layout_id"],"regions":mapped,"class_counts":counts,
            "kind_counts":kind_counts,"assignments":assignments,"outside_semantic_domain":outside,
            "calibrated":False,"persisted":False,"detector_observation":False,
            "detector_input_eligible":False,"production_coordinate_parity":False,"physical_output_allowed":False}
