# Data Format

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

Supported types are `pedestrian_waiting`, `crossing`, `vehicle_queue`, `counting_region`, `counting_line`, and `ignore`. Polygon types use 3-32 points. A `counting_line` uses exactly two distinct points in the same 1280×720 reference coordinate system. `counting_region` and `counting_line` are analytics-only and do not alter simulation decision rules.

Counting-line example:

```json
{
  "id": "eastbound_flow",
  "type": "counting_line",
  "label": "Eastbound flow line",
  "polygon": [[500, 180], [500, 620]]
}
```

## Traffic state occupancy fields

A detection-backed traffic state can include:

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
  }
}
```

## Traffic history sample

Runtime history uses JSON Lines under `outputs/traffic_history/history.jsonl`. Each line is one sampled detection frame:

```json
{"recorded_at_ms":1786780000000,"source_timestamp_ms":1786779999500,"source_frame_number":42,"phase":"vehicle_green","decision":"hold_vehicle_green","pedestrians":4,"vehicles":7,"region_counts":{"entrance_region":{"pedestrians":2,"vehicles":3,"total":5}}}
```

History files are runtime/user data and are not source-patch content.

## Flow event format

Track-derived runtime events are JSON Lines under `outputs/traffic_flow/events.jsonl`. Example unique passage:

```json
{"event_id":"trk_a1b2c3_00007:line:eastbound_flow","event_type":"line_crossing","timestamp_ms":1786780005000,"source_frame_number":52,"track_id":"trk_a1b2c3_00007","class_name":"car","line_id":"eastbound_flow","line_label":"Eastbound flow line","direction":"left_to_right","x":505.3,"y":402.1}
```

A completed region exit may additionally contain `region_id`, `region_label`, `region_type`, and `dwell_ms`.

## Counting semantics

- **Occupancy** remains a sampled observation: how many detections are present in a frame/region. Never sum occupancy samples and describe the result as throughput.
- **Unique passage** is a V022 track-derived event: one tracked object crossing one configured counting line. Each track is counted at most once per line in the current prototype session.
- **Region dwell** begins on a track's region entry (or first observation inside the region) and is finalized on region exit.

Track IDs are prototype IDs produced by lightweight centroid/IoU association; heavy occlusion or crowded motion can cause ID loss/swaps.

## Coordinate rule

Always keep these coordinate spaces separate:

```text
1. Original image coordinates
2. Model input coordinates
3. 1280×720 zone reference coordinates
4. GUI display/canvas coordinates
```

Detection centres are scaled into the zone reference space for region membership. Display scaling is presentation-only.
