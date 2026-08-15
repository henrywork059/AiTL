# Patch 0_2_2 — Cross-frame tracking and flow analytics

## Release state

- Candidate: V022 / `0_2_2`.
- Previous candidate: V021 / `0_2_1`.
- Owner-confirmed passed baseline: V017 / `0_1_7`.
- V022 was explicitly requested by the owner even though V021 was not separately promoted. Automated checks do not promote `passed_baseline`.

## Purpose

V021 added sampled pedestrian/vehicle occupancy over time. V022 adds a separate prototype flow layer so repeated detections can be associated across frames and turned into explicit passage, entry, exit, and dwell events instead of summing occupancy snapshots.

## Implemented

### Cross-frame prototype tracking

- Assigns stable session-local `track_id` values to supported person/vehicle detections.
- Uses class-aware centroid distance plus bounding-box IoU continuity.
- Deduplicates by source/frame/timestamp so repeated frontend, traffic, and recorder polling of the same detection frame cannot create duplicate tracking events.
- Expires temporarily missing tracks after a bounded missed-frame tolerance.
- Exposes active-track status through inference/traffic APIs and displays track IDs beside Live AI boxes.

### Directional counting lines

- Adds analytics-only `counting_line` geometry to the existing Zone Editor.
- Counting lines use exactly two distinct points in the existing 1280×720 reference coordinate system.
- A tracked object generates at most one passage event for each configured line during its track lifetime.
- Passage events distinguish vehicle/person class and one of `left_to_right`, `right_to_left`, `top_to_bottom`, or `bottom_to_top` based on dominant track movement.
- Counting lines do not alter the simulation signal or detection-driven recommendation rules.

### Region entry, exit, and dwell

- Existing non-ignore polygon zones generate track entry/exit events.
- Exit events include dwell time derived from the matched track's region-entry timestamp.
- Pedestrian dwell in `pedestrian_waiting` zones is summarized separately as prototype waiting time.
- `counting_region` remains analytics-only; decision-zone behavior is preserved.

### Persistent flow analytics

- Persists bounded flow events to `outputs/traffic_flow/events.jsonl`.
- Supports filters by time window, line, region, and class.
- Produces per-minute buckets for unique vehicle/person line passages plus region entries/exits.
- Summarizes unique passages, direction totals, line totals, region dwell, and pedestrian waiting-zone dwell.
- Adds CSV export and an explicit flow-history clear action that is separate from V021 occupancy-history clearing.

### Traffic Analytics UI

- Keeps V021 **Occupancy** mode unchanged in meaning.
- Adds **Flow / Tracks** mode for unique counting-line passages and region events.
- Adds line/region scope and class filters, flow charts, summary metrics, event table, CSV export, and separate Clear flow action.

## API additions

- `GET /api/traffic/tracks`
- `GET /api/traffic/flow`
- `GET /api/traffic/flow/export.csv`
- `DELETE /api/traffic/flow`

`GET /api/inference/detections` may include `track_id` and `track_age_frames`. `GET /api/inference/status` includes tracking status.

## Stable errors added

- `ATL-TRAFFIC-007` — flow event read failed.
- `ATL-TRAFFIC-008` — flow event write/compaction failed.
- `ATL-TRAFFIC-009` — flow history clear failed.

## Semantics and limitations

- **Occupancy** is still the number of detections present in a frame/region at one sampled time.
- **Unique passage** is counted only from a tracked object crossing a configured counting line.
- Region entry/exit/dwell events are separate from line-passage events.
- Active track identity is session-local and is not restored across backend restart; persisted events remain available.
- The tracker is a lightweight prototype. Heavy occlusion, abrupt movement, large detection gaps, and crowded same-class traffic can cause ID loss or swaps. Flow counts are therefore prototype analytics, not certified traffic measurements.
- No physical/public-road traffic control is implemented.

## Runtime data

The following remains local runtime data and must not be included in source patches:

```text
outputs/traffic_flow/
outputs/traffic_history/
outputs/training/
datasets/
*.pt
```

## Acceptance focus

1. Track IDs remain stable while clearly visible objects move through consecutive frames.
2. Re-fetching the same source frame does not add duplicate flow events.
3. One tracked object crossing one counting line creates one directional passage event.
4. Multiple counting lines can independently count the same track once per line.
5. Region entry/exit produces sensible dwell time; pedestrian waiting-zone exits contribute waiting-time summary.
6. Occupancy charts remain sampled occupancy and do not change to throughput semantics.
7. Flow CSV and Clear flow operate independently of occupancy history and other runtime data.
8. V021 signal-aware simulation, V021 occupancy analytics, V020 capture/zone features, and V017 training/inference/settings/model behavior show no regression.
9. Prototype safety boundary remains explicit.
