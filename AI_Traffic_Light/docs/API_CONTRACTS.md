# API Contracts (current highlights)

All API responses continue to use the standard envelope:

```json
{ "ok": true, "request_id": "...", "data": { ... } }
```

## Inference

- `GET /api/inference/status`
  - returns backend availability, active/default/latest model info, confidence limits, and discovered models.
- `POST /api/inference/load`
  - body: `{ "model_id": "train_..." }`
  - if `model_id` is omitted or null, the backend loads the default model or newest model.
- `POST /api/inference/load-latest`
  - backward-compatible latest-model load.
- `POST /api/inference/unload`
- `GET /api/inference/detections?confidence=0.01..1.0`
- `GET /api/inference/frame?source_id=...&frame_number=...`

## Models

- `GET /api/models`
  - returns discovered local trained models and default/active model IDs.
- `POST /api/models/default`
  - body: `{ "model_id": "train_..." }`
- `DELETE /api/models/{model_id}`
  - deletes the whole local training run directory.
