# API Contracts

The PC Studio backend exposes small, focused route groups. Route handlers parse requests, call services, log results, and return the project response envelope; business logic stays in services.

## Response envelope

All JSON APIs should return:

```json
{
  "ok": true,
  "data": {},
  "meta": {
    "request_id": "..."
  }
}
```

Errors should return:

```json
{
  "ok": false,
  "error": {
    "code": "ATL-AREA-001",
    "message": "Human readable message",
    "details": {}
  },
  "meta": {
    "request_id": "..."
  }
}
```

Binary image endpoints return image bytes rather than the JSON envelope and include `X-Request-ID`.

## Route groups

| Route prefix | Purpose |
|---|---|
| `/api/camera` | camera/video/ESP-CAM source management |
| `/api/inference` | model loading and detection results |
| `/api/zones` | traffic-zone setup and zone counting |
| `/api/traffic` | signal simulation and decision state |
| `/api/dataset` | capture, manual review/labeling, and managed dataset generation |
| `/api/training` | training progress and config |
| `/api/models` | model registry and export status |
| `/api/settings` | project settings |
| `/api/logs` | recent logs and error reports |
| `/api/template` | template metadata for GUI confirmation |

## 0_1_0 smoke API

### `GET /api/smoke/status`

Returns version, mode, ready/not-ready lists, checks, endpoints, and summary values.

### `GET /api/smoke/error-demo`

Returns the controlled `ATL-API-003` error for envelope testing.

## 0_1_1 camera APIs

### `POST /api/camera/frame?source_id=<camera_id>`

Accepts one raw `image/jpeg` or `image/png` request body, maximum 8 MiB.

### `GET /api/camera/frame`

Returns the latest device or simulation image.

### `GET /api/camera/status`

Returns current source/mode/frame metadata.

### `POST /api/camera/simulation/start` and `/stop`

Enables/disables the synthetic traffic-scene frame source.

## 0_1_2 capture and training APIs

### `GET /api/dataset/status`

Returns persistent capture/session counts and the latest capture made in the current backend process.

### `POST /api/dataset/captures`

Saves the latest receiver or simulation frame and paired metadata:

```json
{
  "session_id": "default",
  "quality_tag": "unreviewed",
  "note": "optional note"
}
```

`quality_tag` is `unreviewed`, `useful`, or `bad`.

### `GET /api/training/status`

Returns optional Ultralytics availability and current background-run state.

### `POST /api/training/start`

Starts one validated Ultralytics YOLO training job. `dataset_yaml` must remain inside `datasets/` and define train/val plus names or nc.

```json
{
  "dataset_yaml": "yolo/data.yaml",
  "base_model": "yolo26n.pt",
  "epochs": 10,
  "image_size": 640,
  "batch": 8,
  "device": "cpu"
}
```

## Added in 0_1_3

### `GET /api/dataset/captures?limit=500&session_id=<optional>`

Returns saved capture records for review plus:

```text
labeled
label_count
image_url
```

The response also includes the shared class list. Class IDs come from `packages/schema/classes.default.json` and currently map 0–5 to person, car, bus, truck, motorcycle, and bicycle.

### `GET /api/dataset/captures/{capture_id}/image`

Returns one persisted capture image for the local review UI. The response includes `X-Request-ID` and `Cache-Control: no-store`.

### `GET /api/dataset/captures/{capture_id}/labels`

Returns the saved manual label document. If the capture has never been reviewed, the endpoint returns `reviewed: false` with an empty label list.

Example:

```json
{
  "capture_id": "...",
  "session_id": "default",
  "image_path": "captures/default/images/...png",
  "width": 1280,
  "height": 720,
  "reviewed": true,
  "updated_at_ms": 1780000000000,
  "labels": [
    {
      "class_id": 0,
      "class_name": "person",
      "box_xyxy": [100.0, 120.0, 240.0, 560.0]
    }
  ]
}
```

A reviewed document may intentionally contain zero boxes. This represents a human-reviewed negative example and is different from an unreviewed capture.

### `PUT /api/dataset/captures/{capture_id}/labels`

Replaces the current manual boxes for one capture:

```json
{
  "labels": [
    {
      "class_id": 1,
      "box_xyxy": [200, 300, 600, 620]
    }
  ]
}
```

The backend derives `class_name` from the shared schema. Boxes must have positive area and remain within the recorded image dimensions. Maximum 500 boxes per frame.

Labels are written to:

```text
datasets/captures/<session_id>/labels/<capture_id>.json
```

### `GET /api/dataset/training-dataset/status`

Returns the managed dataset state:

```text
ready
stale
dataset_yaml
labeled_frame_count
eligible_frame_count
excluded_bad_count
label_box_count
train_count
val_count
generated_at_ms
classes
message
```

`ready` is false if fewer than two non-bad reviewed frames exist, if the managed dataset has never been built, or if saved labels/quality state changed after the last build.

### `POST /api/dataset/training-dataset`

Builds the managed YOLO dataset used by the default training configuration:

```json
{
  "validation_fraction": 0.2
}
```

Requirements:

```text
- at least two reviewed captures not tagged bad
- each reviewed capture may have zero or more manual boxes
- validation_fraction > 0 and < 0.5
```

Generated runtime files:

```text
datasets/yolo/images/train/
datasets/yolo/images/val/
datasets/yolo/labels/train/
datasets/yolo/labels/val/
datasets/yolo/data.yaml
datasets/yolo/manifest.json
```

The split is deterministic by capture ID. At least one image is placed in train and one in validation. YOLO labels use normalized `class x_center y_center width height` values. Captures tagged `bad` are excluded even if label files exist.

If manual labels change after the build, status becomes stale and the managed dataset should be rebuilt before training with `yolo/data.yaml`.

## Added in 0_1_4

### `GET /api/inference/status`

Returns trained-model discovery and live inference state without loading weights. The service scans the configured training output root for:

```text
outputs/training/<run_id>/weights/best.pt
```

Response data includes:

```text
model_loaded
active_model_id
active_model_path
backend
backend_available
available_model_count
latest_model_path
active_is_latest
confidence_floor
last_latency_ms
last_frame_number
models
```

Only relative display paths are returned; model weight bytes remain local runtime data.

### `POST /api/inference/load-latest`

Loads the newest discovered `best.pt` by file modification time. Ultralytics must be installed through `requirements-training.txt`. If no trained run exists, the endpoint returns `ATL-MODEL-003`. If Ultralytics is unavailable it returns `ATL-DETECT-001`; model-load failures use `ATL-DETECT-002`.

### `POST /api/inference/unload`

Releases the active model reference and clears cached live detections/source-frame state.

### `GET /api/inference/detections`

Runs the loaded model against the newest receiver or simulation frame, or returns the cached result if that same source/frame number has already been inferred. The minimum backend confidence floor is `0.10`; the frontend can apply a higher display threshold without rerunning inference.

The response uses the existing `DetectionFrame` shape:

```json
{
  "frame_id": "camera-simulation-42",
  "source_id": "simulation",
  "image_width": 1280,
  "image_height": 720,
  "timestamp_ms": 1780000000000,
  "source_frame_number": 42,
  "detections": [
    {
      "id": "live-42-0",
      "class_id": 1,
      "class_name": "car",
      "confidence": 0.87,
      "box_xyxy": [120, 300, 410, 520]
    }
  ]
}
```

`box_xyxy` coordinates refer to the original camera image dimensions. No zone or traffic decision is made by this endpoint.

### `GET /api/inference/frame?source_id=<id>&frame_number=<n>`

Returns the exact recent image bytes used by the matching successful inference result. The service keeps a small in-memory cache of recent inferred frames. Supplying only one of `source_id` or `frame_number` is invalid; omitting both returns the newest inferred frame for diagnostics. This binary endpoint includes `X-Request-ID`, `X-Frame-Number`, `X-Source-ID`, and `Cache-Control: no-store`. The frontend requests the specific source/frame number returned in `DetectionFrame`, preventing a moving simulation from advancing one frame ahead of its boxes.

## Validation envelopes

FastAPI/Pydantic request validation failures use the normal error envelope with `ATL-API-002` and the middleware request ID. Project-specific labeling/build validation uses the stable `ATL-DATASET-*` codes documented in `ERROR_CODES.md`.
