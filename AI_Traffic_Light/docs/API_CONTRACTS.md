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
