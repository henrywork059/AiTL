# Data Format

This document describes important data semantics and representative runtime/API shapes. Root `VERSION` defines the active candidate; API request/response envelopes belong in `API_CONTRACTS.md`.

## Detection result

Bounding boxes remain in original image coordinates, not display coordinates.

```json
{
  "frame_id": "cam01_000001",
  "source_id": "cam01",
  "image_width": 1280,
  "image_height": 720,
  "timestamp_ms": 0,
  "detections": [
    {
      "id": "det_001",
      "class_id": 0,
      "class_name": "person",
      "confidence": 0.92,
      "box_xyxy": [120, 80, 260, 420],
      "track_id": "trk_a1b2c3_00007",
      "track_age_frames": 12
    }
  ]
}
```

`class_name` should preserve the active detector/source label. Do not silently relabel synthetic/manual information as AI detection.

## Zone format

```json
{
  "zones": [
    {
      "id": "entrance_region",
      "type": "counting_region",
      "label": "Entrance analytics region",
      "polygon": [[60, 420], [360, 420], [360, 680], [60, 680]]
    }
  ]
}
```

Supported types are `pedestrian_waiting`, `crossing`, `vehicle_queue`, `counting_region`, `counting_line`, and `ignore`. Polygon types use 3–32 points. A `counting_line` uses exactly two distinct points in the same 1280×720 reference coordinate system. `counting_region` and `counting_line` are analytics-only unless a future patch explicitly changes their semantics.

Counting-line example:

```json
{
  "id": "eastbound_flow",
  "type": "counting_line",
  "label": "Eastbound flow line",
  "polygon": [[500, 180], [500, 620]]
}
```

## Traffic-state observation fields

A detection-backed traffic state may include sampled totals, per-region occupancy, and per-zone/per-class observations:

```json
{
  "phase": "vehicle_green",
  "pedestrians_total": 4,
  "vehicles_total": 7,
  "evaluated_at_ms": 1786780000000,
  "source_timestamp_ms": 1786779999500,
  "region_counts": {
    "entrance_region": {
      "pedestrians": 2,
      "vehicles": 3,
      "total": 5
    }
  },
  "zone_class_counts": {
    "vehicle_queue_east": {
      "car": 4,
      "bus": 1
    },
    "pedestrian_waiting_west": {
      "person": 3
    }
  }
}
```

`zone_class_counts` is a **per-frame observation** used by ranked scenario conditions. It is not unique passage/throughput.

## Observation provenance

V025 network/explanation enrichment attaches a provenance label to live traffic state:

```json
{
  "intersection_id": "intersection_main",
  "observation_provenance": "simulation"
}
```

Expected provenance values are:

- `ai_detection` — based on the active detection/inference path;
- `simulation` — synthetic simulator observations;
- `manual_test` — explicit Test-mode/manual input context where used;
- `unavailable` — no qualifying observation source.

Provenance is descriptive evidence metadata. It must not be used to make an unsupported detector-capability claim.

## Intersection/network configuration

Runtime topology is stored in ignored `config/intersections.json` and is configuration/user data, not patch content.

Representative normalized shape:

```json
{
  "active_intersection_id": "intersection_main",
  "intersections": [
    {
      "id": "intersection_main",
      "label": "Main model junction",
      "enabled": true,
      "source_ids": ["camera_main"],
      "zone_ids": [],
      "signal_profile": "normal"
    },
    {
      "id": "intersection_b",
      "label": "Downstream model junction",
      "enabled": true,
      "source_ids": ["camera_b"],
      "zone_ids": [],
      "signal_profile": "normal"
    }
  ],
  "links": [
    {
      "id": "main_to_b",
      "source_intersection_id": "intersection_main",
      "destination_intersection_id": "intersection_b",
      "source_approach": "eastbound",
      "destination_approach": "westbound",
      "enabled": true,
      "travel_time_ms": 8000
    }
  ]
}
```

A link is a directed topology/configuration relationship. In the current foundation it is **not** a vehicle-transfer record, measured travel time, arrival prediction, or cooperative-control action.

## Structured live decision context

`GET /api/traffic/state` may include a non-controlling explanation projection:

```json
{
  "decision_context": {
    "decision_id": "decision-...",
    "intersection_id": "intersection_main",
    "trigger_category": "ranked_scenario",
    "scenario": {
      "id": "heavy_vehicle_queue",
      "label": "Heavy vehicle queue",
      "rank": 1
    },
    "requested_service": "vehicle",
    "pedestrian_context": {},
    "vehicle_context": {},
    "neighbour_context": {},
    "emergency_context": {
      "active": false
    },
    "explanation": "..."
  }
}
```

Exact fields may be extended by the API model, but semantics remain:

- explanation context does not control the signal;
- neighbour context does not imply cooperation is active;
- emergency context must state inactive/not implemented until an emergency feature exists;
- the persisted signal-rule event history remains distinct from the live explanation projection.

## Traffic history sample

Runtime occupancy history uses JSON Lines under `outputs/traffic_history/history.jsonl`. Each line is one sampled detection-backed state:

```json
{"recorded_at_ms":1786780000000,"source_timestamp_ms":1786779999500,"source_frame_number":42,"phase":"vehicle_green","decision":"hold_vehicle_green","pedestrians":4,"vehicles":7,"region_counts":{"entrance_region":{"pedestrians":2,"vehicles":3,"total":5}}}
```

History files are runtime/user data and are not source-patch content.

## Flow event format

Track-derived runtime events are JSON Lines under `outputs/traffic_flow/events.jsonl`. Example passage:

```json
{"event_id":"trk_a1b2c3_00007:line:eastbound_flow","event_type":"line_crossing","timestamp_ms":1786780005000,"source_frame_number":52,"track_id":"trk_a1b2c3_00007","class_name":"car","line_id":"eastbound_flow","line_label":"Eastbound flow line","direction":"left_to_right","x":505.3,"y":402.1}
```

A completed region exit may additionally contain `region_id`, `region_label`, `region_type`, and `dwell_ms`.

## Counting/data semantics

- **Occupancy** — sampled detections currently present; never sum samples and call the result throughput.
- **Zone/class observation** — per-frame detector-class count inside one configured polygon.
- **Unique passage** — one prototype track crossing one configured counting line, deduplicated according to current tracker/session logic.
- **Region dwell** — starts on track entry/first observation inside and finalizes on exit.
- **Simulation telemetry** — generated by the isolated numeric simulator/controller and separate from live occupancy/flow history.
- **Network link** — configured directed metadata, not an observed transfer event.

Track IDs are lightweight centroid/IoU prototype identities; heavy occlusion/crowding can cause loss/swaps.

## Coordinate rule

Always keep these coordinate spaces separate:

```text
1. Original image coordinates
2. Model input coordinates
3. 1280×720 zone reference coordinates
4. GUI display/canvas coordinates
```

Detection centres are scaled into zone-reference space for membership. Display scaling is presentation-only.

## Runtime-data rule

Do not package runtime/user data such as `config/intersections.json`, zone/settings/signal config, histories, datasets, trained models, or experiment results in changed-files source patches.
