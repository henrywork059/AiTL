# Error Codes

The project uses stable error codes so humans and AI agents can debug quickly.

## Rules

- Never raise a generic error when a project-specific code exists.
- Include the code in backend logs and API error responses.
- Add new codes here when adding a new failure type.
- Keep `apps/pc-studio/backend/app/core/error_codes.py` aligned with this file.

## Code ranges

| Range | Area |
|---|---|
| `ATL-COMMON-*` | Shared/general errors |
| `ATL-API-*` | HTTP/API/request/response errors |
| `ATL-CONFIG-*` | Config/settings errors |
| `ATL-CAMERA-*` | Camera/video source errors |
| `ATL-DETECT-*` | AI inference/model detection errors |
| `ATL-ZONE-*` | Traffic-zone configuration/counting errors |
| `ATL-TRAFFIC-*` | Traffic-light simulation decision errors |
| `ATL-DATASET-*` | Dataset capture/review/labeling/storage/build errors |
| `ATL-TRAIN-*` | Training pipeline errors |
| `ATL-MODEL-*` | Model registry/export errors |
| `ATL-LOG-*` | Log reading/reporting errors |

## Current backend codes

| Code | Meaning |
|---|---|
| `ATL-COMMON-000` | Unexpected backend error. |
| `ATL-API-001` | API request failed. |
| `ATL-API-002` | Invalid request, including Pydantic field validation. |
| `ATL-API-003` | Template route is not implemented yet. |
| `ATL-CONFIG-001` | Required configuration is missing. |
| `ATL-CONFIG-002` | Failed to read settings. |
| `ATL-CONFIG-003` | Failed to write settings. |
| `ATL-CAMERA-001` | Camera is not connected. |
| `ATL-CAMERA-002` | Failed to read a camera frame. |
| `ATL-CAMERA-003` | Camera source is invalid. |
| `ATL-CAMERA-004` | Camera stream has not been started. |
| `ATL-CAMERA-005` | Camera frame exceeds the 8 MiB limit. |
| `ATL-CAMERA-006` | Camera frame content type is unsupported. |
| `ATL-CAMERA-007` | Camera frame bytes are invalid. |
| `ATL-DETECT-001` | No inference model is loaded, or Ultralytics is unavailable when loading a trained model. |
| `ATL-DETECT-002` | Trained-model load or live-frame inference failed. |
| `ATL-DETECT-003` | No camera frame/exact inferred source frame is available, or the current frame cannot be decoded. |
| `ATL-DETECT-004` | The inference backend returned an unsupported or invalid result structure. |
| `ATL-ZONE-001` | Zone configuration is invalid. |
| `ATL-ZONE-002` | Zone was not found. |
| `ATL-ZONE-003` | Failed to save zone configuration. |
| `ATL-TRAFFIC-001` | Traffic state is invalid. |
| `ATL-TRAFFIC-002` | Traffic rule is invalid. |
| `ATL-TRAFFIC-003` | Traffic decision failed. |
| `ATL-DATASET-001` | Failed to atomically write a captured image, metadata, or label document. |
| `ATL-DATASET-002` | Failed to read dataset metadata, class schema, labels, or another dataset item. |
| `ATL-DATASET-003` | Dataset capture/image item was not found. |
| `ATL-DATASET-004` | Manual label class/coordinates/count are invalid. |
| `ATL-DATASET-005` | Managed training build is not ready, including fewer than two eligible reviewed frames. |
| `ATL-DATASET-006` | Failed to build or replace the managed YOLO training dataset. |
| `ATL-TRAIN-001` | Training prerequisites are unavailable or another run is active. |
| `ATL-TRAIN-002` | Training config, dataset path, or dataset YAML is invalid. |
| `ATL-TRAIN-003` | Training run failed. |
| `ATL-MODEL-001` | Failed to read model registry. |
| `ATL-MODEL-002` | Failed to export model package. |
| `ATL-MODEL-003` | Requested/discovered model version was not found; V014 also uses this when no trained `best.pt` exists. |
| `ATL-LOG-001` | Failed to read logs. |
