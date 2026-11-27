"""Isolated synthetic projection onto ordered legacy region coordinates.

Match the production frontend regionCounts.ts *assignment* convention:
bottom centre, 1280x720 scaling, ray crossing and first matching region.
The piecewise semantic map is not a calibrated camera transform. Do not
publish these rows to the detector, region registry or signal controller.
"""
from __future__ import annotations
import math
from app.services.native_evaluation_geometry import legacy_rectangle_preview, region_counts
from app.services.observation_identity import simulation_view_point, SIMULATION_VIEW_FLIPS
from app.services.legacy_world import CROSSING_LEFT,CROSSING_RIGHT,ROAD_TOP,ROAD_BOTTOM
from app.services.sumo_projection import WIDTH,HEIGHT


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
    for i in range(len(source)-1):
        if source[i]<=value<=source[i+1]:
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
        polygon=region_counts({"agents":[]},item["polygon"])["polygon"]
        if any(not (0<=x<=WIDTH-1 and 0<=y<=HEIGHT-1) for x,y in polygon):
            raise ValueError("Region vertices outside legacy pixel-centre plane")
        seen.add(ident)
        rows.append({"id":ident,"polygon":polygon})
    return rows


def legacy_region_projection(scene,view_id,regions,boxes):
    """Inverse-map per-view detection bottom centres, not the four corners.

    Counting in the original legacy polygon preserves slanted edges through
    the piecewise scale changes. Edges of mapped quadrilaterals can bend, so
    an outline is split at every crossed landmark. No saved region is edited.
    As with the production UI, bottom centre is expressed in box edge
    coordinates; no half-pixel correction or mirror-count equivalence claim.
    """
    if view_id not in SIMULATION_VIEW_FLIPS:
        raise ValueError("Unknown legacy preview view")
    regions=_region_rows(regions)
    rectangle=[[CROSSING_LEFT,ROAD_TOP],[CROSSING_RIGHT,ROAD_TOP],
               [CROSSING_RIGHT,ROAD_BOTTOM],[CROSSING_LEFT,ROAD_BOTTOM]]
    landmarks=legacy_rectangle_preview(scene,rectangle,"simulation_camera")["landmarks"]
    sx,sy,tx,ty=(landmarks[k] for k in ("legacy_x","legacy_y","native_x","native_y"))
    mapped=[]
    for region in regions:
        canonical=[simulation_view_point(x,y,WIDTH,HEIGHT,view_id) for x,y in region["polygon"]]
        outline=[]
        for (x,y),(u,v) in zip(canonical,canonical[1:]+canonical[:1]):
            times={0.}
            for a,b,knots in ((x,u,sx),(y,v,sy)):
                if b!=a:
                    times.update(f for k in knots[1:-1] if 0<(f:=(k-a)/(b-a))<1)
            for f in sorted(times):
                a=_interpolate(x+(u-x)*f,sx,tx)
                b=_interpolate(y+(v-y)*f,sy,ty)
                outline.append(list(simulation_view_point(a,b,WIDTH,HEIGHT,view_id)))
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
        x,y=simulation_view_point(*native,WIDTH,HEIGHT,view_id)
        a,b=_interpolate(x,tx,sx),_interpolate(y,ty,sy)
        legacy=None if a is None or b is None else list(simulation_view_point(a,b,WIDTH,HEIGHT,view_id))
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
            "native_layout_id":scene["layout_id"],"regions":mapped,"class_counts":counts,
            "kind_counts":kind_counts,"assignments":assignments,"outside_semantic_domain":outside,
            "calibrated":False,"persisted":False,"detector_observation":False,
            "detector_input_eligible":False,"production_coordinate_parity":False,"physical_output_allowed":False}
