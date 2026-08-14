# API Contracts (current highlights)

All API responses continue to use the standard envelope:

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
  - returns receiver/simulation state and latest-frame metadata.
  - V016 also returns `simulation_density` (`light`, `normal`, or `busy`) and `simulation_paused`.
- `GET /api/camera/frame`
  - returns the latest device or synthetic PNG/JPEG frame.
  - includes `X-Request-ID`, `X-Camera-Source`, and `X-Frame-Number` headers.
- `POST /api/camera/simulation/start`
- `POST /api/camera/simulation/stop`
- `POST /api/camera/simulation/settings`
  - body fields are optional: `{ "density": "busy", "paused": true }`.
  - density may be changed before or during simulation.
  - pause/resume requires simulation mode to be active.
  - invalid request values use the existing stable API/camera error codes.

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
