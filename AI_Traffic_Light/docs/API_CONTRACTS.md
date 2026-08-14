# API Contracts

The PC Studio backend should expose small, focused route groups. Each group should call service functions instead of storing logic inside route handlers.

## Response envelope

All new APIs should return this format:

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

## Placeholder route groups in 0_0_4

| Route prefix | Purpose |
|---|---|
| `/api/camera` | camera/video/ESP-CAM source management |
| `/api/inference` | model loading and detection results |
| `/api/zones` | traffic-zone setup and zone counting |
| `/api/traffic` | signal simulation and decision state |
| `/api/dataset` | data capture and review |
| `/api/training` | training progress and config |
| `/api/models` | model registry and export status |
| `/api/settings` | project settings |
| `/api/logs` | recent logs and error reports |
| `/api/template` | template metadata for GUI confirmation |

## Implementation rule

Do not put real logic directly in route files. Use this structure:

```text
routes/camera.py
→ services/camera_sources.py
→ core/error_codes.py
→ schema files / models
```

A route file should mainly:

```text
- parse request
- call service
- log request/result
- return API envelope
```

## Added in 0_1_0

### `GET /api/smoke/status`

Purpose: verify that the backend is locally test-ready without connecting to real camera, AI inference, training, or physical traffic-light control.

Response data includes:

```text
version
mode
ready_for
not_ready_for
checks
endpoints
summary
```

Use this endpoint first when checking whether the frontend and backend can communicate.

### `GET /api/smoke/error-demo`

Purpose: intentionally returns a controlled error envelope for testing error-code display and request handling.

Expected status:

```text
501
```

Expected error code:

```text
ATL-API-003
```

## Added in 0_1_1

### `POST /api/camera/frame?source_id=<camera_id>`

Accepts one raw `image/jpeg` or `image/png` request body (maximum 8 MiB). The latest valid upload is retained in PC memory and replaces the previous device frame.

### `GET /api/camera/frame`

Returns the latest device or simulation image as binary image content. Returns `ATL-CAMERA-001` with HTTP 404 until a frame exists.

### `GET /api/camera/status`

Returns the current mode, source ID, frame number, resolution, age, stale state, and display URL.

### `POST /api/camera/simulation/start` and `/stop`

Enables or disables a synthetic moving traffic scene. Simulation uses the same status and image endpoints as future hardware uploads.

## Added in 0_1_2

### `GET /api/dataset/status`

Returns persistent capture counts, session count, the relative dataset path, and the latest capture made during the current backend process.

### `POST /api/dataset/captures`

Saves the latest receiver or simulation frame with paired JSON metadata. The JSON request body is:

```json
{
  "session_id": "default",
  "quality_tag": "unreviewed",
  "note": "optional note"
}
```

`session_id` accepts 1–64 letters, numbers, dots, dashes, or underscores. `quality_tag` is `unreviewed`, `useful`, or `bad`. Images are written under `datasets/captures/<session_id>/images/`; paired records use `metadata/`. Generated dataset paths are relative and are never included in patch ZIPs.

### `GET /api/training/status`

Returns optional Ultralytics availability, current background-run state, progress, validated config, relative output paths, and any bounded failure message.

### `POST /api/training/start`

Validates and starts one real Ultralytics YOLO training job. The dataset YAML must be a relative path inside `datasets/` and define `train`, `val`, and `names` or `nc`.

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

Training requires the optional `requirements-training.txt` install and labeled YOLO images. Raw captures alone are not a trainable object-detection dataset. Only one run can be active; 0_1_2 does not implement cancel, model export, or automatic labeling.

### Validation envelopes

FastAPI/Pydantic request validation errors now use the normal failure envelope with `ATL-API-002` and the middleware request ID.
