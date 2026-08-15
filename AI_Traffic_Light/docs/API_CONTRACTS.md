# API Contracts (current highlights)

All JSON API responses use the standard envelope:

```json
{
  "ok": true,
  "data": {},
  "meta": { "request_id": "..." }
}
```

Errors use the documented `error` envelope. Binary/image and CSV responses include `X-Request-ID`.

## Camera

- `GET /api/camera/status`
- `GET /api/camera/frame`
- `POST /api/camera/simulation/start`
- `POST /api/camera/simulation/stop`
- `POST /api/camera/simulation/settings`

## Dataset capture lifecycle

- `GET /api/dataset/status`
- `POST /api/dataset/captures`
- `GET /api/dataset/captures`
- `DELETE /api/dataset/captures/{capture_id}`
- `GET /api/dataset/captures/{capture_id}/image`
- `GET|PUT /api/dataset/captures/{capture_id}/labels`
- `GET /api/dataset/training-dataset/status`
- `POST /api/dataset/training-dataset`

## Zones and counting regions

- `GET /api/zones/active`
  - returns the active zone set in the 1280×720 reference coordinate system.
- `PUT /api/zones/active`
  - replaces the complete active zone set after validation.
  - supported types: `pedestrian_waiting`, `crossing`, `vehicle_queue`, `counting_region`, `ignore`.
- `POST /api/zones/reset`

`counting_region` is analytics-only. It can overlap other regions and does not alter the simulation phase recommendation. Existing non-ignore traffic zones also expose pedestrian/vehicle region occupancy for analytics.

### Signal-aware simulation status fields

When simulation mode is active, camera status/start/settings responses also include:

- `simulation_signal_phase`: active phase obeyed by synthetic agents (`vehicle_green`, `vehicle_yellow`, `all_red`, `pedestrian_green`, or `pedestrian_flashing`);
- `simulation_signal_seconds_remaining`: approximate seconds remaining in the active phase;
- `simulation_signal_cycle_seconds`: total deterministic cycle length (`34.0`);
- `simulation_signal_vehicle_go`: true only during vehicle green;
- `simulation_signal_pedestrian_walk`: true only during pedestrian WALK.

When receiver mode is active, phase/countdown/cycle fields are `null` and the boolean go/walk flags are false.

## Traffic simulation state

In simulation mode, `phase` is the active simulator signal that synthetic agents obey. The detection-driven phase/decision are retained as optional `recommended_phase`, `recommended_decision`, and `recommended_decision_reason` fields so the UI can compare the active safe simulation cycle with the CV recommendation without creating a circular dependency.


- `GET /api/traffic/state`
  - obtains/reuses the current trained-model detection frame when available;
  - in receiver mode, returns the detection-driven simulation-only phase recommendation;
  - in simulation mode, returns the exact active simulator signal as `phase` and preserves detection-driven output under `recommended_*`;
  - returns whole-frame sampled occupancy as `pedestrians_total` and `vehicles_total`;
  - returns `evaluated_at_ms`, source frame/timestamp metadata, `zone_counts`, and per-zone `region_counts`;
  - `region_counts[zone_id]` has `{ "pedestrians": n, "vehicles": n, "total": n }`;
  - no response is connected to physical public-road traffic infrastructure.

The whole-frame and region counts are per-frame occupancy observations. They are not unique passage/throughput counts because the current inference path does not maintain stable object track IDs across frames.

## Traffic history and analytics

- `GET /api/traffic/history?minutes=15&limit=2000&region_id=<optional>`
  - `minutes`: `0..360`; `0` means all retained samples.
  - `limit`: `1..10000`.
  - optional `region_id` selects one configured non-ignore zone; omitted means whole frame.
  - returns recording configuration, selected scope, available regions, ordered points, and summary statistics.
  - each point includes recorded/source timestamps, source frame number, pedestrian occupancy, vehicle occupancy, phase, and decision.
  - summary includes averages, peaks with timestamps, phase-change count/latest phase change, and busiest configured region.
- `GET /api/traffic/history/export.csv?minutes=...&limit=...&region_id=...`
  - exports the selected history scope as UTF-8 CSV.
  - includes `X-Request-ID` and download filename headers.
- `DELETE /api/traffic/history`
  - clears only persisted traffic-analytics history runtime data.
  - does not delete captures, labels, zones, settings, trained models, or training runs.

History is stored locally under `outputs/traffic_history/history.jsonl`, is runtime data, and is excluded from source patches. Default target sampling interval is 1000 ms and default retained capacity is 21,600 samples. Environment overrides are `AITL_TRAFFIC_HISTORY_INTERVAL_MS`, `AITL_TRAFFIC_HISTORY_MAX_SAMPLES`, and `AITL_TRAFFIC_HISTORY_PATH`.

## Training

- `GET /api/training/status`
- `POST /api/training/start`

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

## Logs

- `GET /api/logs/recent?limit=1..200`
