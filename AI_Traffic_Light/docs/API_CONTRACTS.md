# API Contracts (current highlights)

All JSON API responses use the standard success/error envelopes and `meta.request_id`. Binary/image/CSV responses preserve `X-Request-ID`.

## Camera

- `GET /api/camera/status`
- `GET /api/camera/frame`
- `POST /api/camera/simulation/start`
- `POST /api/camera/simulation/stop`
- `POST /api/camera/simulation/settings`

When simulation is active, camera status includes the active configurable signal phase/countdown, cycle length, vehicle/pedestrian go flags, signal mode/profile, and active adaptive-rule IDs. The values are simulation-only.

## Dataset / zones

Existing dataset capture/label/training-dataset endpoints are unchanged. Existing zone endpoints are unchanged. Supported zones remain `pedestrian_waiting`, `crossing`, `vehicle_queue`, `counting_region`, `counting_line`, and `ignore`; counting lines require two distinct points and remain analytics-only.

## Traffic state

- `GET /api/traffic/state`

Returns current occupancy/zone counts and detection-driven recommendation data. In Simulation mode, `phase` reflects the exact simulated controller phase obeyed by synthetic agents; detection recommendation remains available under `recommended_*`. V023 additionally exposes `signal_policy` controller metadata when simulation mode is active.

Occupancy remains sampled per-frame data. Track-derived flow remains separate.

## V023 signal-rule configuration

### `GET /api/traffic/signal-rules`

Returns the persisted/effective signal-rule configuration. Top-level fields include:

- `schema_version` (currently `1`)
- `mode`: `fixed | adaptive | test`
- `dry_run`: boolean
- `active_profile`
- `profiles`

Each profile contains six protected phase entries with `base_seconds`, `min_seconds`, and `max_seconds`; controller limits such as `max_cycle_seconds`, `stale_data_seconds`, and `demand_memory_seconds`; and structured rules.

Rules contain `enabled`, `trigger`, `threshold`, `persistence_seconds`, `action`, `adjustment_seconds`, `target_phases`, `priority`, and `cooldown_seconds`.

### `PUT /api/traffic/signal-rules`

Body:

```json
{"config": {"schema_version": 1, "mode": "adaptive", "dry_run": false, "active_profile": "Normal", "profiles": {}}}
```

The complete configuration is validated before atomic persistence. Protected phase minimums, min/base/max ordering, supported triggers/actions, cycle bounds, and profile/rule limits are enforced. Invalid policy data uses the central traffic-rule error path.

Saving while a simulation is running preserves the current protected phase and restarts its timing window at the current simulation clock; it does not replay elapsed time from zero.

### `POST /api/traffic/signal-rules/reset`

Restores source-defined defaults. This changes saved policy configuration only; it does not delete traffic datasets/history/models.

### `POST /api/traffic/signal-rules/runtime/reset`

Clears transient demand memory, cooldown/application state, pending requests, and incident state without deleting saved configuration. When simulation is active, reset is anchored to the current simulation clock.

### `POST /api/traffic/signal-rules/test-inputs`

Body fields are optional:

```json
{
  "pedestrians_waiting": 6,
  "pedestrians_crossing": 1,
  "vehicles_waiting": 8,
  "mobility_assistance": false,
  "incident_person_fallen": false
}
```

These are explicit manual **Test-mode** inputs, not claims about live AI perception.

### `POST /api/traffic/signal-rules/incident/clear`

Clears the manual incident input/hold. Recovery resumes from the protected current phase with a fresh timing window rather than catching up through elapsed phases.

### `POST /api/traffic/signal-rules/preview`

Evaluates one scenario without mutating active simulator state. Supports `phase_key`, pedestrian/vehicle counts, optional wait/crossing duration values, mobility assistance, and incident input. Returns base/effective duration, per-rule statuses, and whether Test mode would enter incident hold.

### `GET /api/traffic/signal-status`

Returns controller state including:

- active `phase` / `phase_key`
- base/effective/elapsed/remaining seconds
- next phase
- Fixed/Adaptive/Test mode and dry-run flag
- active profile
- base/max cycle duration
- freshness/fallback reason
- pending request
- incident hold flag
- active rules and priority-ordered rule statuses
- observations/test inputs
- `prototype_only: true`

When Simulation mode is off, this endpoint is a policy preview/status surface and does not represent physical signal output.

### Signal decision history

- `GET /api/traffic/signal-rules/history?limit=200`
- `DELETE /api/traffic/signal-rules/history`

Runtime audit data is stored under `outputs/signal_rules/decision_history.jsonl`. Clearing it does not clear occupancy history, flow history, zones, captures, labels, models, training output, settings, or saved signal rules.

## Traffic occupancy / flow

Existing V021/V022 endpoints remain:

- `GET /api/traffic/history`
- `GET /api/traffic/history/export.csv`
- `DELETE /api/traffic/history`
- `GET /api/traffic/tracks`
- `GET /api/traffic/flow`
- `GET /api/traffic/flow/export.csv`
- `DELETE /api/traffic/flow`

Occupancy is sampled occupancy. Unique passages are only recorded track/counting-line crossing events. The lightweight tracker may lose/swap IDs under occlusion/crowding.

## Training / inference / models / settings / logs

Existing endpoints remain unchanged, including training status/start, inference model load/unload/detections, model registry/default/delete, runtime settings, and recent logs.

## Safety boundary

No API in V023 sends commands to physical/public-road traffic infrastructure. Signal rules affect the local simulator and simulation/recommendation displays only.
