# Data Format

## Detection result

Bounding boxes should be stored in **original image coordinates**, not display coordinates.

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
      "id": "ped_waiting_left",
      "type": "pedestrian_waiting",
      "label": "Pedestrian Waiting Zone",
      "polygon": [[60, 420], [360, 420], [360, 680], [60, 680]]
    }
  ]
}
```

## Traffic state

```json
{
  "phase": "vehicle_green",
  "pedestrians_waiting": 4,
  "pedestrians_crossing": 1,
  "vehicles_waiting": 7,
  "decision": "extend_pedestrian_green",
  "decision_reason": "Pedestrian waiting count is high",
  "extension_seconds": 5
}
```

## Coordinate rule

Always keep three coordinate spaces separate:

```text
1. Original image coordinates
2. Model input coordinates
3. GUI display/canvas coordinates
```

Most detection GUI bugs come from mixing these spaces.
