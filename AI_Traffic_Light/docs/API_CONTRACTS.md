# API Contracts (current highlights)

All JSON API responses continue to use the standard envelope:

```json
{
  "ok": true,
  "data": {},
  "meta": { "request_id": "..." }
}
```

Binary image responses include `X-Request-ID`.

## Camera

- `GET /api/camera/status`
  - returns receiver/simulation state, latest-frame metadata, simulation density, and pause state.
- `GET /api/camera/frame`
  - returns the latest device or synthetic PNG/JPEG frame.
  - includes `X-Request-ID`, `X-Camera-Source`, and `X-Frame-Number` headers.
- `POST /api/camera/simulation/start`
- `POST /api/camera/simulation/stop`
- `POST /api/camera/simulation/settings`
  - optional body fields: `{ "density": "busy", "paused": true }`.

## Zones

- `GET /api/zones/active`
  - returns the validated active zone set, reference resolution, persistence source, and config path.
- `PUT /api/zones/active`
  - body: `{ "zones": [{ "id": "...", "type": "crossing", "label": "...", "polygon": [[x,y], ...] }] }`.
  - replaces the complete active zone set after validation and persists it to `config/zones.json`.
  - uses existing `ATL-ZONE-001` / `ATL-ZONE-003` errors for invalid or unsavable configurations.
- `POST /api/zones/reset`
  - restores and persists the simulation-aligned reference zones.

## Traffic simulation logic

- `GET /api/traffic/state`
  - obtains the current receiver/simulation frame and loaded model when available.
  - runs/reuses trained-model inference, scales detection-box centres into the zone reference frame, and returns zone counts.
  - returns a simulation-only phase recommendation, reason, source, evaluated frame number, and `prototype_only: true`.
  - this endpoint is not connected to physical traffic infrastructure.

## Training

- `GET /api/training/status`
  - returns run progress plus `history`, `completed_epochs`, and `early_stopping`.
  - each history point can include `epoch`, `fitness`, `best_fitness`, `map50_95`, `map50`, `train_loss`, and `val_loss`.
- `POST /api/training/start`
  - body fields: `dataset_yaml`, `base_model`, `epochs`, `image_size`, `batch`, `device`, and `patience`.
  - `patience` is 1-100 and is passed to Ultralytics automatic early stopping.
  - a run that finishes before the requested maximum epochs is reported as `early_stopped` and retains its best checkpoint metadata.

## Inference

- `GET /api/inference/status`
- `POST /api/inference/load`
- `POST /api/inference/load-latest`
- `POST /api/inference/unload`
- `GET /api/inference/detections?confidence=0.01..1.0`
- `GET /api/inference/frame?source_id=...&frame_number=...`

## Models

- `GET /api/models`
- `POST /api/models/default`
- `DELETE /api/models/{model_id}`

## Runtime settings

- `GET /api/settings/runtime`
- `PUT /api/settings/runtime`
  - body: `{ "default_confidence": 0.1, "live_poll_interval_ms": 500, "training_patience": 5, "log_level": "INFO" }`.
  - settings are persisted to `config/runtime_settings.json`.
  - the backend log level is applied immediately; frontend confidence and camera-status polling are applied by PC Studio when settings are loaded/saved.

## Logs

- `GET /api/logs/recent?limit=1..200`
  - returns actual recent backend log records from a bounded in-memory handler.
  - entries include timestamp, level, code, scope, message, and request ID when present.
