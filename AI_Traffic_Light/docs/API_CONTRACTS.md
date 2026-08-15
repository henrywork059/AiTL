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

## Zones, counting regions, and counting lines

- `GET /api/zones/active`
  - returns the active zone set in the 1280×720 reference coordinate system.
- `PUT /api/zones/active`
  - replaces the complete active zone set after validation.
  - supported types: `pedestrian_waiting`, `crossing`, `vehicle_queue`, `counting_region`, `counting_line`, `ignore`.
- `POST /api/zones/reset`

`counting_region` and `counting_line` are analytics-only and do not alter the simulation phase recommendation. Polygon types use 3-32 points; `counting_line` uses exactly two distinct points. Existing non-ignore polygon zones expose pedestrian/vehicle region occupancy and track entry/exit/dwell analytics.

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

Whole-frame and region counts remain per-frame occupancy observations. V022 separately assigns prototype track IDs and generates unique-passage events only when a track crosses a configured `counting_line`; do not sum occupancy samples and call them throughput.

## Traffic history and analytics

- `GET /api/traffic/history?minutes=15&limit=2000&region_id=<optional>`
  - `minutes`: `0..360`; `0` means all retained samples.
  - `limit`: `1..10000`.
  - optional `region_id` selects one configured non-ignore polygon region; counting lines are excluded from occupancy scopes; omitted means whole frame.
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

## Cross-frame tracking and flow analytics

`GET /api/inference/detections` now enriches supported traffic classes (`person`, `car`, `bus`, `truck`, `motorcycle`, `bicycle`) with optional `track_id` and `track_age_frames`. Repeated processing of the same source frame is idempotent and cannot generate duplicate flow events.

- `GET /api/traffic/tracks`
  - returns current in-memory tracking status, active tracks, class counts, tracker session ID, and latest processed source frame.
- `GET /api/traffic/flow?minutes=15&limit=10000&line_id=<optional>&region_id=<optional>&class_name=<optional>`
  - `minutes`: `0..360`; `0` means all retained events.
  - optional `line_id` filters a configured `counting_line`.
  - optional `region_id` filters a configured polygon region.
  - optional `class_name` filters one detected class.
  - returns raw ordered events, per-minute buckets, configured lines/regions, persistence status, and summary metrics.
  - `line_crossing` events include one of `left_to_right`, `right_to_left`, `top_to_bottom`, or `bottom_to_top`.
  - each track is counted at most once per counting line in the current prototype session to suppress jitter double-counting.
  - `region_entry`/`region_exit` events represent outside/inside transitions; completed exits include `dwell_ms`. Pedestrian exits from `pedestrian_waiting` regions contribute to average pedestrian-wait duration.
- `GET /api/traffic/flow/export.csv?...`
  - exports selected flow events as UTF-8 CSV with `X-Request-ID`.
- `DELETE /api/traffic/flow`
  - clears only persisted flow-event history. It does not clear V021 occupancy history, zones, captures, labels, settings, models, or training runs.

Flow events are stored under `outputs/traffic_flow/events.jsonl`, are runtime/user data, and are excluded from source patches. Default capacity is 50,000 events. Environment overrides: `AITL_TRAFFIC_FLOW_PATH` and `AITL_TRAFFIC_FLOW_MAX_EVENTS`.

The V022 tracker is lightweight class-aware centroid/IoU matching. Heavy occlusion, abrupt motion, long detection gaps, or crowded same-class crossings can still lose/swap IDs; flow remains prototype analytics, not certified traffic measurement.

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
