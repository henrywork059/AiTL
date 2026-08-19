# API Contracts (current highlights)

All JSON API responses use the standard success/error envelopes and `meta.request_id`. Binary/image/CSV responses preserve `X-Request-ID`.

## Camera

- `GET /api/camera/status`
- `GET /api/camera/frame`
- `POST /api/camera/simulation/start`
- `POST /api/camera/simulation/stop`
- `POST /api/camera/simulation/settings`

When simulation is active, camera status includes the active configurable signal phase/countdown, cycle length, vehicle/pedestrian go flags, signal mode/profile, and active ranked-scenario IDs. The values are simulation-only.

## Dataset / zones

Existing dataset capture/label/training-dataset endpoints are unchanged. Existing zone endpoints are unchanged. Supported zones remain `pedestrian_waiting`, `crossing`, `vehicle_queue`, `counting_region`, `counting_line`, and `ignore`; counting lines require two distinct points and remain analytics-only.

## Traffic state

- `GET /api/traffic/state`

Returns current occupancy/zone counts, V025 per-zone/per-class observations, and detection-driven recommendation data. In Simulation mode, `phase` reflects the exact simulated controller phase obeyed by synthetic agents; detection recommendation remains available under `recommended_*`. `signal_policy` exposes controller/scenario metadata when simulation mode is active.

Occupancy remains sampled per-frame data. Track-derived flow and V025 experiment telemetry remain separate.

## V025 simulation experiments

### `POST /api/traffic/experiments`

Runs one isolated Fixed-vs-Adaptive comparison. Request body:

```json
{
  "duration_seconds": 300,
  "density": "normal",
  "seed": 25025,
  "sample_interval_seconds": 1,
  "profile": "Normal",
  "label": "baseline comparison"
}
```

Supported duration is 30-1800 seconds. Density is `light | normal | busy`. The profile must identify an existing saved signal profile. Test-mode incident/accessibility inputs are not part of this benchmark.

The result contains `fixed`, `adaptive`, and `comparison` objects. Each mode records wait distributions, queues/queue-seconds/queue-active time, throughput/service rates, phase utilization, transitions/cycles, clearance time, scenario applications and timing adjustments, a simulator conflict-overlap diagnostic, and a sampled timeline. `comparison` provides Fixed/Adaptive values, absolute difference, percent change where defined, and whether Adaptive moved the metric in the preferred direction.

The benchmark uses an isolated controller/simulator instance, snapshots configured zones for synthetic zone/class conditions, and does not reset the live Camera Sources simulation or live signal-scenario runtime.

### Stored experiment runs

- `GET /api/traffic/experiments?limit=50` — list compact run summaries.
- `GET /api/traffic/experiments/{run_id}` — load one complete result.
- `DELETE /api/traffic/experiments/{run_id}` — delete one stored result.
- `GET /api/traffic/experiments/{run_id}/export.csv` — export aligned Fixed/Adaptive timeline samples; preserves `X-Request-ID`.

Runtime JSON is stored under `outputs/simulation_experiments/` and excluded from source patches. Retention is bounded to the newest 200 runs.

## V025 ranked signal-scenario configuration

### `GET /api/traffic/signal-rules`

Returns the persisted/effective signal configuration. Top-level fields remain:

- `schema_version` (currently `1`);
- `mode`: `fixed | adaptive | test`;
- `dry_run`;
- `active_profile`;
- `profiles`.

Each profile keeps six protected phase entries with `base_seconds`, `min_seconds`, and `max_seconds`; `max_cycle_seconds`, `stale_data_seconds`, and `demand_memory_seconds`; compatibility `rules`; and V025 `scenarios`.

A scenario has the following normalized shape:

```json
{
  "id": "busy_east_queue",
  "label": "Busy east queue",
  "enabled": true,
  "rank": 1,
  "match": "all",
  "conditions": [
    {
      "source": "zone_class_count",
      "zone_id": "queue_east",
      "class_name": "car",
      "operator": "gt",
      "threshold": 5
    }
  ],
  "persistence_seconds": 2,
  "cooldown_seconds": 10,
  "action": {
    "type": "extend_current_phase",
    "adjustment_seconds": 5,
    "target_phases": ["vehicle_green"],
    "request_service": "vehicle"
  }
}
```

Supported condition sources:

- `metric` — one of the validated controller metrics;
- `zone_class_count` — one class (or `*` for all classes) inside one configured polygon zone.

Supported comparison operators are `gt`, `gte`, `lt`, `lte`, and `eq`. A scenario supports `match: all | any` and 1–8 conditions. Rank `1` is highest and saved ranks are unique within each profile.

If an older saved profile has `rules` but no `scenarios`, V025 migrates the legacy rules into editable scenario definitions during validation. An explicitly present empty `scenarios` list remains empty and disables adaptive scenario actions for that profile.

### `PUT /api/traffic/signal-rules`

Body remains:

```json
{"config": {"schema_version": 1, "mode": "adaptive", "dry_run": false, "active_profile": "Normal", "profiles": {}}}
```

The complete configuration is validated before atomic persistence. Validation covers protected phase timing, scenario ids/ranks, condition sources/operators/thresholds, match mode, persistence/cooldown, action type, requested service, phase targets, profile limits, and maximum-cycle bounds. Invalid scenario configuration uses `ATL-TRAFFIC-002`.

Saving while simulation is running re-anchors the current protected phase at the next simulation-clock evaluation; it does not replay elapsed time from zero.

### Ranked arbitration

In Adaptive/Test mode, every enabled scenario is evaluated against the current observation. Multiple scenarios may be triggered, but only the highest-ranked **eligible** scenario executes in one evaluation. A triggered scenario is not eligible when its observation is unavailable/stale, persistence is incomplete, current phase is not in its target list, or cooldown is active. The next eligible ranked scenario may then win.

Actions are bounded to `extend_current_phase`, `reduce_current_phase`, `hold_current_phase`, `request_next_phase`, or `incident_hold`. `request_next_phase` requests earlier progression through the existing protected sequence and does not directly jump conflicting movement phases.

### `POST /api/traffic/signal-rules/reset`

Restores source defaults, including default migrated/editable scenarios. Runtime datasets/models/analytics are unchanged.

### `POST /api/traffic/signal-rules/runtime/reset`

Clears transient condition-persistence, cooldown/application state, pending service, winner, and incident state without deleting saved configuration.

### `POST /api/traffic/signal-rules/test-inputs`

Optional body fields remain:

```json
{
  "pedestrians_waiting": 6,
  "pedestrians_crossing": 1,
  "vehicles_waiting": 8,
  "mobility_assistance": false,
  "incident_person_fallen": false
}
```

These are explicit manual **Test-mode** sources. They are not claims about live wheelchair/mobility/fall perception.

### `POST /api/traffic/signal-rules/incident/clear`

Clears the manual/scenario incident hold and resumes safely from a protected phase with a fresh timing window.

### `POST /api/traffic/signal-rules/preview`

Evaluates the current ranked scenarios without mutating runtime state. Existing metric fields remain accepted. V025 also accepts an optional `zone_class_counts` object when supplied by an internal/current-state caller. The result includes `winning_scenario_id`, scenario/rule status details, and effective phase duration.

### `GET /api/traffic/signal-status`

Returns existing phase/timing/mode/profile/freshness/pending/incident fields plus:

- `winning_scenario_id`;
- `winning_scenario_label`;
- `active_scenarios` (compatibility `active_rules` remains);
- `scenario_status` (compatibility `rule_status` remains).

Each scenario status includes rank, state/reason, action metadata, eligibility/match flags, and observed condition values. States include `winner`, `triggered`, `suppressed`, `inactive`, and `unavailable`.

### Traffic state observation extension

`GET /api/traffic/state` includes `zone_class_counts`:

```json
{
  "queue_east": {"car": 4, "bus": 1},
  "waiting_west": {"person": 3}
}
```

These are per-frame detector observations used by scenario conditions. They are not unique passage/throughput counts. Missing/deleted zones are distinguishable because existing countable zones are returned with an empty object when their current count is zero.

### Signal decision history

- `GET /api/traffic/signal-rules/history?limit=200`
- `DELETE /api/traffic/signal-rules/history`

Scenario adjustments retain the compatibility `rule_applied` event type for existing experiment/history readers and include `scenario_id`, scenario label, rank, action, protected phase, and previous/effective duration details. Runtime audit data remains under `outputs/signal_rules/decision_history.jsonl`.

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

No API in V025 sends commands to physical/public-road traffic infrastructure. Signal scenarios and experiments affect local simulation/recommendation/evaluation surfaces only.
