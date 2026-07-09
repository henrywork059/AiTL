# API Contracts

Patch: **0_0_3**

This document defines how the PC Studio backend API should be written.

## 1. API style

The backend should use small, predictable endpoints.

Route files should be thin wrappers over service functions.

```text
HTTP request
→ route function
→ service function
→ response helper
```

## 2. Success response envelope

New endpoints should return this shape:

```json
{
  "ok": true,
  "data": {},
  "meta": {
    "request_id": "req_..."
  }
}
```

## 3. Error response envelope

Expected errors should return this shape:

```json
{
  "ok": false,
  "error": {
    "code": "ATL-AREA-NNN",
    "message": "Human-readable error message",
    "details": {}
  },
  "meta": {
    "request_id": "req_..."
  }
}
```

The frontend API client should support both:

```text
new envelope responses
old raw placeholder responses
```

This keeps early placeholder code from breaking while the API standard is introduced.

## 4. Endpoint groups

Recommended endpoint groups:

```text
GET  /health
GET  /api/mock/frame
GET  /api/mock/zones
GET  /api/traffic/state

Future:
GET  /api/cameras
POST /api/cameras/connect
POST /api/cameras/disconnect
POST /api/detect/image
POST /api/detect/frame
POST /api/datasets/capture
GET  /api/datasets
POST /api/train/start
GET  /api/train/status
POST /api/models/export
```

## 5. Naming rules

Use clear nouns and actions:

```text
/api/cameras
/api/datasets
/api/models
/api/traffic/state
```

Avoid vague endpoints:

```text
/api/do
/api/run
/api/process
/api/data
```

## 6. Route implementation rule

Routes should look like this:

```python
@router.get('/state')
def traffic_state(request: Request) -> dict:
    state = get_mock_traffic_state()
    return ok(state, request_id=request.state.request_id)
```

Do not put large business logic in route functions.

## 7. Request ID rule

Every request should have a request ID.

Use it in:

```text
backend logs
API meta responses
frontend error logs
bug reports
```

## 8. Backward compatibility rule

When changing an endpoint shape, update:

```text
frontend API client
docs/API_CONTRACTS.md
docs/PATCH_<version>.md
CHANGELOG.md
```
