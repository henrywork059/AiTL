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
      "travel_time_seconds": 8.0
    }
  ]
}
```

A live/configured link is a directed topology/configuration relationship. It is **not** an observed vehicle-transfer record, measured travel time, or live cooperative-control action. V027 network experiments may explicitly generate synthetic transfer, predicted-arrival, and cooperation events over one selected link; those events remain simulator evidence.

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

## V027 network experiment transfer and cooperation format

Stored network experiments use `netexp_*.json` under ignored `outputs/simulation_experiments/`.

A representative synthetic transfer event remains:

```json
{
  "vehicle_id": "src_0007",
  "class_name": "car",
  "departed_at_s": 41.5,
  "scheduled_arrival_s": 49.0,
  "arrived_at_s": 49.0
}
```

For an arrived transfer, `arrived_at_s - departed_at_s` equals the configured link travel time in simulator time. This is not a measured road travel-time observation.

The scenario keeps the deterministic arrival-plan count summary and SHA-256 fingerprint. Fixed, Independent Adaptive, and Cooperative Adaptive receive the same seeded exogenous demand plan; policy-dependent upstream discharge may still change transfer departure/arrival timing.

A representative V027 cooperation event is:

```json
{
  "coordination_id": "coord_intersection_a_intersection_b_44000",
  "t": 44.0,
  "link_id": "a_to_b",
  "source_intersection_id": "intersection_a",
  "destination_intersection_id": "intersection_b",
  "provenance": "synthetic_predicted_arrivals",
  "destination_phase_before": "vehicle_green",
  "destination_phase_key_before": "vehicle_green",
  "incoming_vehicle_count": 2,
  "earliest_arrival_eta_seconds": 5.0,
  "action": "extend_vehicle_green",
  "applied": true,
  "reason": "extended downstream vehicle green for predicted upstream arrivals",
  "timing_delta_seconds": 3.0
}
```

Possible cooperation actions include:

- `extend_vehicle_green`;
- `vehicle_green_already_sufficient`;
- `request_protected_vehicle_progression`;
- `vehicle_progression_pending`;
- `protect_pedestrian_service`;
- `none`/`unsupported` where applicable.

A Cooperative result includes:

```json
{
  "cooperative_control_active": true,
  "coordination_provenance": "synthetic_predicted_arrivals",
  "network_metrics": {
    "coordination": {
      "evaluations": 600,
      "triggered": 42,
      "applied": 9,
      "green_extensions": 5,
      "protected_progression_requests": 4,
      "pedestrian_service_protections": 3,
      "timing_seconds_added": 13.0,
      "timing_seconds_reduced": 8.0,
      "lookahead_seconds": 12.0,
      "max_extension_seconds": 5.0,
      "min_incoming_vehicles": 1
    }
  },
  "coordination_events": []
}
```

The numbers above are format examples, not expected benchmark results.

`corridor_travel_time` remains end-to-end simulated corridor time from original upstream external arrival to downstream service and can include upstream wait + configured link travel + downstream wait.

The network timeline records both intersections, transfer pipeline counts, and Cooperative coordination snapshot where active. These are isolated synthetic experiment values, not live occupancy/flow events or AI-detected cross-intersection identity.

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
- **Network link** — configured directed metadata; V027 network experiments may generate explicit synthetic transfer and cooperation evidence over it, but live topology is still not observed flow.

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
