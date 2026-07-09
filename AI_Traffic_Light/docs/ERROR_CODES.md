# Error Codes

Patch: **0_0_3**

This project uses stable error codes to make debugging easier.

## 1. Format

Use this format:

```text
ATL-AREA-NNN
```

Examples:

```text
ATL-COMMON-000
ATL-API-001
ATL-CAMERA-001
ATL-DETECT-001
```

## 2. Area ranges

| Range | Area | Meaning |
|---|---|---|
| `ATL-COMMON-000` to `ATL-COMMON-099` | Common | Unknown or generic project errors |
| `ATL-API-001` to `ATL-API-099` | API | Request/response/server errors |
| `ATL-CONFIG-001` to `ATL-CONFIG-099` | Config | Missing or invalid configuration |
| `ATL-CAMERA-001` to `ATL-CAMERA-099` | Camera | Webcam, ESP-CAM, stream, image capture errors |
| `ATL-DETECT-001` to `ATL-DETECT-099` | AI detection | Model loading, inference, post-processing errors |
| `ATL-ZONE-001` to `ATL-ZONE-099` | Zones | Invalid zones, geometry, object-zone assignment |
| `ATL-TRAFFIC-001` to `ATL-TRAFFIC-099` | Traffic logic | Signal state and decision logic errors |
| `ATL-DATASET-001` to `ATL-DATASET-099` | Dataset | Capture, save, import, export errors |
| `ATL-FE-001` to `ATL-FE-099` | Frontend | Browser UI, API client, rendering errors |

## 3. Initial backend codes

| Code | Name | Meaning |
|---|---|---|
| `ATL-COMMON-000` | `UNKNOWN_ERROR` | Unexpected unhandled error |
| `ATL-API-001` | `API_REQUEST_FAILED` | API request failed |
| `ATL-API-002` | `INVALID_REQUEST` | Request body/query/path is invalid |
| `ATL-CONFIG-001` | `CONFIG_MISSING` | Required config file/value is missing |
| `ATL-CAMERA-001` | `CAMERA_NOT_CONNECTED` | Camera is not connected |
| `ATL-CAMERA-002` | `CAMERA_FRAME_READ_FAILED` | Failed to read a camera frame |
| `ATL-DETECT-001` | `MODEL_NOT_LOADED` | Detection model is not loaded |
| `ATL-DETECT-002` | `INFERENCE_FAILED` | Detection inference failed |
| `ATL-ZONE-001` | `ZONE_CONFIG_INVALID` | Zone configuration is invalid |
| `ATL-TRAFFIC-001` | `TRAFFIC_STATE_INVALID` | Traffic state is invalid |
| `ATL-DATASET-001` | `DATASET_WRITE_FAILED` | Failed to save dataset item |

## 4. Initial frontend codes

| Code | Name | Meaning |
|---|---|---|
| `ATL-FE-001` | `FRONTEND_UNKNOWN` | Unknown frontend error |
| `ATL-FE-API-001` | `API_FETCH_FAILED` | Frontend failed to fetch API data |
| `ATL-FE-API-002` | `API_RESPONSE_INVALID` | API response was not in expected shape |
| `ATL-FE-RENDER-001` | `RENDER_FAILED` | UI component render/update problem |

## 5. Rules for adding new codes

- Do not reuse a code for a different meaning.
- Do not delete old codes; mark them deprecated if needed.
- Use specific codes for expected failures.
- Use `ATL-COMMON-000` only for truly unexpected failures.
- Update this document and `app/core/error_codes.py` together.
