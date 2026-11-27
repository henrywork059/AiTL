"""Read-only audit of S04 retained synthetic evidence, independent of simulator code."""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from statistics import mean
from zipfile import ZipFile

VIEWS = ("simulation_camera", "simulation_camera_b", "simulation_camera_c", "simulation_camera_d")
COUNTS = ("vehicle_queue", "pedestrian_queue", "vehicle_passages", "pedestrian_crossings")
FLAGS = ("detector_input_eligible", "detector_observation", "authoritative", "physical_output_allowed")


def check(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(read, name):
    return json.loads(read(name))


def verify_metric_rows(rows, run, step, horizon):
    """Use Decimal-like rounded sample times and integer queue counts, not wait claims."""
    check(rows and len(rows) == round(horizon / step), "Metric sample count")
    for i, row in enumerate(rows, 1):
        check(row["tick"] == i and math.isclose(row["t_seconds"], i * step, abs_tol=1e-8), "Metric clock")
        check(all(type(row[key]) is int and row[key] >= 0 for key in COUNTS), "Metric negative/fractional count")
        if i > 1:
            check(all(row[key] >= rows[i-2][key] for key in COUNTS[2:]), "Metric passage count reversed")
    summary = run["summary"]
    check(summary["samples"] == len(rows), "Metric summary sample count")
    for kind, passage in (("vehicle", "vehicle_passages"), ("pedestrian", "pedestrian_crossings")):
        queue = kind + "_queue"
        check(summary[passage] == rows[-1][passage], "Metric passage total")
        check(summary["peak_" + queue] == max(row[queue] for row in rows), "Metric peak queue")
        check(math.isclose(summary[kind + "_wait_agent_s"], sum(row[queue] for row in rows) * step, abs_tol=1e-8), "Metric queue integral")
    check(digest(json.dumps(rows, sort_keys=True).encode()) == run["digest"], "Metric raw timeline digest")
    return len(rows)


def csv_rows(read, name):
    return [{k: float(v) if k == "t_seconds" else v if k == "requested_phase" else int(v)
             for k, v in row.items()} for row in csv.DictReader(io.StringIO(read(name).decode("utf-8")))]


def audit_metrics(read):
    from verify_wait_trace import CONTRACT, qualify, comparison
    total = 0
    pairs = {}
    for group, engines in (("mesh-sumo-gate-metrics", ("legacy", "native")),
                           ("mesh-sumo-finite-fixture", ("native", "finite_reference"))):
        result = load(read, group + "/result.json")
        check(result["replacement_parity"] is False and result["default_migration_allowed"] is False, "Metric migration authority")
        check(len(result["runs"]) == 4, "Metric repeat count")
        has_trace = "wait_comparison" in result
        check(has_trace == any("wait_audit" in run for run in result["runs"]), "Wait evidence schema mismatch")
        for engine in engines:
            runs = [r for r in result["runs"] if r["engine"] == engine]
            check(len(runs) == 2, "Metric engine repeat count")
            for repeat, run in enumerate(runs):
                rows = csv_rows(read, f"{group}/{engine}-{repeat}.csv")
                total += verify_metric_rows(rows, run, result["step_s"], result["horizon_s"])
                if has_trace:
                    trace = load(read, f"{group}/{engine}-{repeat}-wait-trace.json")
                    check(trace["contract"] == CONTRACT and trace["step_s"] == result["step_s"], "Wait trace contract")
                    audit = qualify(trace["frames"], rows, run["summary"], trace["episodes"])
                    check(audit == trace["audit"] == run["wait_audit"], "Wait trace replay differs")
                if group.endswith("finite-fixture"):
                    check(load(read, f"{group}/{engine}-{repeat}-summary.json") == run, "Finite summary differs")
                    check(run["completion_ok"] and not run["route_mismatches"] and not run["unsupported_routes"] and not run["unknown_roads"], "Finite route qualification")
                else:
                    index = engines.index(engine)
                    raw = load(read, f"{group}/arm-{index}-{repeat}.json")
                    check(raw["timeline"] == rows and all(raw[k] == run[k] for k in run), "Metric raw JSON differs")
            check(runs[0]["digest"] == runs[1]["digest"], "Metric deterministic repeat differs")
            pairs[group + "/" + engine] = runs[0]["summary"]
        if has_trace:
            left = "finite_reference" if group.endswith("finite-fixture") else "legacy"
            check(result["wait_comparison"] == comparison(result["runs"], left, "native", left == "finite_reference"), "Wait comparison verdict differs")
    return total, pairs


def percentile95(values):
    ordered = sorted(values)
    position = .95 * (len(ordered) - 1)
    low = math.floor(position)
    return ordered[low] + (ordered[math.ceil(position)] - ordered[low]) * (position - low)


def audit_resources(read):
    root = "mesh-sumo-midblock/"
    encoding = load(read, root + "indexed-rgb-comparison.json")
    transport = load(read, root + "worker-memory-comparison.json")
    check(encoding["pixel_equivalent"] is True and transport["pixel_equivalent"] is True and encoding["indexed"] == transport["lean"], "Resource arm identity")
    groups = (("indexed_lean", encoding["indexed"], ("42-normal-fixed", "42-normal-fixed-repeat"), True, "lean_stdio"),
              ("rgb_lean", encoding["rgb"], ("42-normal-fixed-rgb-0", "42-normal-fixed-rgb-1"), False, "lean_stdio"),
              ("indexed_spawn", transport["spawn"], ("42-normal-fixed-spawn-0", "42-normal-fixed-spawn-1"), True, "spawn"))
    output, pixels = {}, set()
    for key, records, paths, indexed, worker in groups:
        check(len(records) == len(paths), "Resource repeat count")
        pooled = []
        for record, path in zip(records, paths):
            check(record["indexed_frames"] is indexed and record["worker_transport"] == worker and record["simulated_seconds"] == 40, "Resource arm settings")
            samples = load(read, root + path + "/latency-samples.json")
            for channel, count_key in (("scene_ms", "scene_reads"), ("frame_ms", "frame_reads")):
                values = samples[channel]
                stats = record["latency_ms"][channel]
                check(len(values) == record[count_key] == stats["count"] == 400 and all(math.isfinite(x) and x >= 0 for x in values), "Resource sample count")
                check(math.isclose(mean(values), stats["mean"], abs_tol=1e-8) and math.isclose(percentile95(values), stats["p95"], abs_tol=1e-8), "Resource latency statistic")
            pooled += samples["frame_ms"]
            before, after = record["before"], record["after"]
            check(set(before) == set(after) == {record["parent_pid"], record["child_pid"]}, "Resource process identity")
            check(sum(v["working_set_bytes"] for v in after.values()) == record["end_combined_working_set_bytes"], "Resource working-set sum")
            check(math.isclose(sum(after[k]["cpu_s"] - before[k]["cpu_s"] for k in before), record["cpu_delta_s"], abs_tol=1e-8), "Resource CPU delta")
            pixels.add(record["decoded_pixel_digest"])
        output[key] = {"frame_samples": len(pooled), "mean_ms": mean(pooled), "p95_ms_linear": percentile95(pooled),
                       "mean_final_combined_working_set_bytes": mean(r["end_combined_working_set_bytes"] for r in records)}
    check(len(pixels) == 1, "Resource decoded-pixel digest differs")
    return output


def audit_captures(read):
    report = load(read, "mesh-native-detector-batch.json")
    check(report["method"] == "exact_palette_components_not_trained_model" and report["model_sha256"] is None
          and report["production_detector_validated"] is False and report["physical_output_allowed"] is False, "Detector evidence authority")
    identities, views = set(), 0
    check(report["capture_count"] == len(report["records"]) > 0, "Detector capture count")
    for record in report["records"]:
        name = record["capture_name"]
        check(not Path(name).is_absolute() and ".." not in Path(name).parts and "\\" not in name, "Unsafe capture path")
        content = read("mesh-sumo-midblock/" + name)
        check(digest(content) == record["archive_sha256"], "Capture archive digest")
        with ZipFile(io.BytesIO(content)) as archive:
            check(len(archive.namelist()) == len(set(archive.namelist())), "Duplicate capture member")
            scene = load(archive.read, "scene.json")
            coordinate = load(archive.read, "coordinate_contract.json")
            detector = load(archive.read, "detector_contract.json")
            observations = load(archive.read, "observations.json")
            identity = tuple(scene[k] for k in ("epoch", "generation", "tick", "layout_id"))
            check(list(identity) == record["identity"] and identity not in identities, "Capture identity")
            identities.add(identity)
            check(all(coordinate[k] == scene[k] for k in ("epoch", "generation", "tick", "layout_id", "coordinate_space", "width", "height", "provenance"))
                  and coordinate["coordinate_space"] == "native_projection_v1" and coordinate["legacy_editor_compatible"] is False, "Capture coordinate provenance")
            check(detector["observations"] == observations and all(detector[k] is False for k in FLAGS), "Capture detector authority")
            hashes = load(archive.read, "capture_integrity.json")["sha256"]
            check(set(hashes) == {"scene.json", *(sid + ".png" for sid in VIEWS)} and hashes == record["integrity"]["sha256"], "Capture member manifest")
            check(all(digest(archive.read(member)) == expected for member, expected in hashes.items()), "Capture member digest")
            truth = load(archive.read, "synthetic_footprints.json")["views"]
            check(set(truth) == set(record["views"]) == set(VIEWS), "Capture view coverage")
            base = {a["agent_id"]: a for a in truth[VIEWS[0]]}
            for index, sid in enumerate(VIEWS):
                obs = observations[index]
                meta = load(archive.read, sid + ".json")
                check(obs["view_id"] == sid and all(obs[k] is False for k in FLAGS) and meta["detector_input_eligible"] is False, "Capture view authority")
                check(all(obs[k] == scene[k] for k in ("epoch", "generation", "tick", "layout_id", "coordinate_space", "width", "height", "provenance"))
                      and meta["source_id"] == obs["source_id"] and meta["source_frame_number"] == scene["tick"], "Capture view identity")
                check(meta.get("content_sha256", hashes[sid + ".png"]) == hashes[sid + ".png"], "Capture content digest")
                check(len(truth[sid]) == len(base) and {a["agent_id"] for a in truth[sid]} == set(base), "Capture mirrored truth IDs")
                for item in truth[sid]:
                    x1, y1, x2, y2 = base[item["agent_id"]]["box_xyxy"]
                    w, h = scene["width"], scene["height"]
                    if index in (2, 3): x1, x2 = w-x2, w-x1
                    if index in (1, 3): y1, y2 = h-y2, h-y1
                    check(item["box_xyxy"] == [x1, y1, x2, y2], "Capture mirrored half-open coordinates")
                views += 1
    return len(identities), views


def audit_legacy_region_edges(read):
    """Independently verify saved-fixture edge mapping and region assignments."""
    import bisect
    report = load(read, "mesh-native-detector-batch.json")
    captures = views = assignments = outlines = 0
    for record in report["records"]:
        root = "mesh-sumo-midblock/" + str(Path(record["capture_name"]).parent).replace("\\", "/") + "/"
        preview = load(read, root + "legacy-ui-region-comparison.json")
        if preview[VIEWS[0]]["truth"].get("coordinate_mapping_contract") != "semantic_midblock_image_edges_v2":
            continue  # Retained earlier evidence, not qualified against this contract.
        fixture_bytes = read(root + "coordinate-fixture-crosswalks.json")
        integrity = load(read, root + "coordinate-fixture-integrity.json")
        check(integrity == {"schema":"saved_legacy_regions_edge_v2","sha256":digest(fixture_bytes),
                            "unchanged_after_preview":True,"synthetic_fixture":True,"physical_output_allowed":False},
              "Saved coordinate fixture digest")
        fixture = json.loads(fixture_bytes)
        check(fixture["schema_version"] == 1, "Saved coordinate fixture schema")
        with ZipFile(io.BytesIO(read("mesh-sumo-midblock/" + record["capture_name"]))) as capture:
            scene = load(capture.read, "scene.json")
            truth = load(capture.read, "synthetic_footprints.json")["views"]
        lanes = {l["id"]:l for l in scene["lanes"]}
        crossing = next(l for l in lanes.values() if l["kind"] == "crossing")
        x = crossing["points"][0][0]
        half = crossing["width_px"] / 2
        road_x = [p[0] for k in ("WC_1","EC_1") for p in lanes[k]["points"]]
        walk_y = [p[1] for k in ("NC_0","CS_0") for p in lanes[k]["points"]]
        sx,sy = [0,520,760,1280],[0,179,625,720]
        tx = [v+.5 for v in (min(road_x),x-half,x+half,max(road_x))]
        ty = [v+.5 for v in (min(walk_y),min(p[1] for p in crossing["points"]),max(p[1] for p in crossing["points"]),max(walk_y))]
        def transform(v, src, dst):
            if v < src[0]-1e-9 or v > src[-1]+1e-9:
                return None
            i = min(max(bisect.bisect_right(src,v)-1,0),len(src)-2)
            v = min(max(v,src[0]),src[-1])
            return dst[i]+(v-src[i])*(dst[i+1]-dst[i])/(src[i+1]-src[i])
        def same(p,q):
            return len(p)==len(q) and all(math.isclose(a,b,rel_tol=0.,abs_tol=1e-8) for a,b in zip(p,q))
        def contains(point,polygon):
            x,y = point
            hits = sum(x < a[0]+(y-a[1])*(b[0]-a[0])/(b[1]-a[1])
                       for a,b in zip(polygon,polygon[1:]+polygon[:1])
                       if min(a[1],b[1]) <= y < max(a[1],b[1]))
            return hits%2 == 1
        for i,sid in enumerate(VIEWS):
            def mirror(x,y):
                return (1280-x if i in (2,3) else x,720-y if i in (1,3) else y)
            saved = next(c for c in fixture["crosswalks"] if sid in (c["camera_side_a_id"],c["camera_side_b_id"]))
            side = "a" if sid == saved["camera_side_a_id"] else "b"
            regions = [(r["id"],r.get("vertices_by_side",{}).get(side,r["vertices"]))
                       for r in saved["regions"] if r.get("camera_side") in (None,side)]
            result = preview[sid]["truth"]
            check(result["coordinate_mapping_contract"] == "semantic_midblock_image_edges_v2"
                  and result["landmarks"] == {"legacy_x":sx,"legacy_y":sy,"native_x":tx,"native_y":ty}
                  and result["source_id"] == sid and result["native_layout_id"] == scene["layout_id"]
                  and all(result[k] is False for k in ("calibrated","persisted","detector_observation","detector_input_eligible","production_coordinate_parity","physical_output_allowed")),
                  "Legacy edge coordinate provenance")
            check([(r["id"],r["original_polygon"]) for r in result["regions"]] == regions, "Saved region side/order changed")
            for (ident,polygon),mapped in zip(regions,result["regions"]):
                expected = []
                canonical = [mirror(*p) for p in polygon]
                for a,b in zip(canonical,canonical[1:]+canonical[:1]):
                    cuts={0.}
                    for k,knots in enumerate((sx,sy)):
                        if a[k]!=b[k]:
                            cuts.update((knot-a[k])/(b[k]-a[k]) for knot in knots[1:-1]
                                        if min(a[k],b[k])<knot<max(a[k],b[k]))
                    for u in sorted(cuts):
                        expected.append(mirror(transform(a[0]+(b[0]-a[0])*u,sx,tx),
                                               transform(a[1]+(b[1]-a[1])*u,sy,ty)))
                check(len(expected)==len(mapped["native_outline"]) and all(same(p,q) for p,q in zip(expected,mapped["native_outline"])), "Mapped edge outline differs")
                outlines += 1
            check(len(result["assignments"]) == len(truth[sid]), "Region assignment coverage")
            counts={k:{"vehicle":0,"pedestrian":0} for k,_ in regions}
            classes={k:{} for k,_ in regions}
            outside=0
            for n,(row,box) in enumerate(zip(result["assignments"],truth[sid])):
                x1,y1,x2,y2 = box["box_xyxy"]
                bottom=((x1+x2)/2,y2)
                x,y=mirror(*bottom)
                a,b=transform(x,tx,sx),transform(y,ty,sy)
                legacy=None if a is None or b is None else mirror(a,b)
                ident=None if legacy is None else next((k for k,p in regions if contains(legacy,p)),None)
                check(row["index"]==n and row["agent_id"]==box["agent_id"] and same(row["native_bottom_center"],bottom)
                      and (row["legacy_point"] is None if legacy is None else row["legacy_point"] is not None and same(row["legacy_point"],legacy))
                      and row["region_id"]==ident, "Region bottom-centre assignment differs")
                if legacy is None: outside+=1
                if ident is not None:
                    kind=box["kind"]
                    counts[ident][kind]+=1
                    name=box.get("class_name",kind)
                    classes[ident][name]=classes[ident].get(name,0)+1
                assignments+=1
            check(counts==result["kind_counts"] and classes==result["class_counts"] and outside==result["outside_semantic_domain"], "Region count reconciliation")
            views+=1
        captures+=1
    check(captures in (0,len(report["records"])), "Mixed edge-coordinate evidence")
    return {"captures":captures,"views":views,"assignments":assignments,"outlines":outlines,
            "saved_fixture_verified":captures>0,"production_calibrated":False}


def audit(read):
    samples, metrics = audit_metrics(read)
    captures, views = audit_captures(read)
    return {"normalized_samples": samples, "metrics": metrics, "resource_arms": audit_resources(read),
            "capture_count": captures, "coordinate_views": views, "legacy_edge_regions": audit_legacy_region_edges(read), "migration_allowed": False,
            "limitations": "Synthetic evidence consistency only; no calibrated production coordinates, trained holdout, owner resource budget or migration acceptance."}


def tamper_checks(read):
    cases = ((audit_metrics, "mesh-sumo-gate-metrics/result.json", lambda d: d["runs"][0]["summary"].__setitem__("vehicle_wait_agent_s", -1), "Metric queue integral"),
             (audit_resources, "mesh-sumo-midblock/indexed-rgb-comparison.json", lambda d: d["rgb"][0]["latency_ms"]["frame_ms"].__setitem__("mean", -1), "Resource latency statistic"),
             (audit_captures, "mesh-native-detector-batch.json", lambda d: d["records"][0].__setitem__("archive_sha256", "0" * 64), "Capture archive digest"))
    for function, name, alter, expected in cases:
        changed = load(read, name)
        alter(changed)
        def modified(member):
            return json.dumps(changed).encode() if member == name else read(member)
        try:
            function(modified)
        except ValueError as exc:
            check(expected in str(exc), "Unexpected tamper rejection: " + str(exc))
        else:
            raise ValueError("Tampered evidence accepted: " + name)
    return len(cases)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Retained evidence directory or ZIP")
    parser.add_argument("--sha256", help="Independently retained expected archive SHA-256")
    parser.add_argument("--tamper-check", action="store_true", help="Run non-mutating negative controls on retained evidence")
    args = parser.parse_args()
    if args.input.is_dir():
        check(not args.sha256, "Archive digest requires ZIP input")
        read = lambda name: (args.input / name).read_bytes()
        result = audit(read)
        if args.tamper_check:
            result["tamper_rejections"] = tamper_checks(read)
    else:
        if args.sha256:
            check(digest(args.input.read_bytes()) == args.sha256, "Outer archive digest")
        with ZipFile(args.input) as archive:
            check(len(archive.namelist()) == len(set(archive.namelist())), "Duplicate evidence member")
            result = audit(archive.read)
            if args.tamper_check:
                result["tamper_rejections"] = tamper_checks(archive.read)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
