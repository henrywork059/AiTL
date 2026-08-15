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
      "box_xyxy": [120, 80, 260, 420]
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

Supported zone types are `pedestrian_waiting`, `crossing`, `vehicle_queue`, `counting_region`, and `ignore`. `counting_region` is analytics-only and does not alter the traffic simulation decision rules.

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

## Counting semantics

The current history records **occupancy observations**: how many detections are present in a sampled frame/region. It does not infer unique people/vehicles passing through over time because there is no stable cross-frame tracking ID yet. Do not sum occupancy samples and describe the result as throughput.

## Coordinate rule

Always keep these coordinate spaces separate:

```text
1. Original image coordinates
2. Model input coordinates
3. 1280×720 zone reference coordinates
4. GUI display/canvas coordinates
```

Detection centres are scaled into the zone reference space for region membership. Display scaling is presentation-only.
