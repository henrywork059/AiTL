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

This same-candidate network-foundation update also adds:

- `intersection_id` — resolved from the current camera/source id or the configured active-intersection fallback;
- `observation_provenance` — `ai_detection | simulation | manual_test | unavailable`;
- `network_context` — the configured intersection plus inbound/outbound neighbour links;
- `decision_context` — deterministic decision id, category, source/intersection identity, winning scenario and observed conditions when available, requested service, timing, pedestrian/vehicle context, explicit emergency-placeholder state, neighbour context, and a readable explanation.

The decision context is a live explanation projection. Existing signal-rule history remains the persisted controller-event audit. Live/runtime `cooperative_control_active` remains false; V027 cooperation exists only inside isolated network experiments.

Occupancy remains sampled per-frame data. Track-derived flow and V025 experiment telemetry remain separate.

## V025 intersection/network foundation

### `GET /api/traffic/network`

Returns the normalized runtime network configuration plus `config_path`, `cooperative_control_active: false`, and `prototype_only: true`.

Default configuration:

```json
{
  "schema_version": 1,
  "active_intersection_id": "intersection_main",
  "intersections": [
    {
      "id": "intersection_main",
      "label": "Main prototype junction",
      "enabled": true,
      "source_ids": ["simulation_camera"],
      "zone_ids": [],
      "signal_profile": "Normal"
    }
  ],
  "links": []
}
```

`intersections` is generic and does not assume exactly two nodes. Current limits are 1-16 intersections, up to 16 source ids and 64 zone ids per intersection, and up to 64 directed links. A source id may belong to only one intersection.

A link contains:

```json
{
  "id": "a_to_b",
  "enabled": true,
  "source_intersection_id": "intersection_a",
  "destination_intersection_id": "intersection_b",
  "source_approach": "eastbound",
  "destination_approach": "westbound",
  "travel_time_seconds": 12.5
}
```

For live/runtime topology this travel-time field remains configured prototype metadata. V027 isolated network experiments consume it as deterministic synthetic link travel time and use it to schedule predicted synthetic arrivals; it is not a measured or learned road travel-time estimate.

### `PUT /api/traffic/network`

Body:

```json
{"config": {"schema_version": 1, "active_intersection_id": "intersection_a", "intersections": [], "links": []}}
```

The complete configuration is validated before atomic persistence to runtime `config/intersections.json`. Validation rejects duplicate intersection/link ids, source ids assigned to multiple intersections, missing link endpoints, self-links, malformed ids, excessive collection sizes, invalid profile/approach labels, and travel times outside 0.1-300 seconds.

Stable errors:

- `ATL-TRAFFIC-013` invalid network/intersection configuration;
- `ATL-TRAFFIC-014` network configuration read failure;
- `ATL-TRAFFIC-015` network configuration write failure.

### `POST /api/traffic/network/reset`

Restores the single default `intersection_main` topology. It does not reset signal rules, zones, datasets, models, analytics, or Simulation Lab results.

### `GET /api/traffic/network/context`

Optional query: `intersection_id`.

Returns the selected/active intersection and normalized inbound/outbound neighbour links. The response explicitly reports:

```json
{
  "cooperative_control_active": false,
  "emergency_priority_active": false,
  "prototype_only": true
}
```

No live/runtime network endpoint changes signal timing at another intersection or sends physical traffic commands. V027 neighbour-informed timing is confined to the isolated network experiment service.

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

The result contains `fixed`, `adaptive`, and `comparison` objects. Each mode records wait distributions, queues/queue-seconds/queue-active time, throughput/service rates, phase utilization, transitions/cycles, clearance time, scenario applications and timing adjustments, a simulator conflict-overlap diagnostic, and a sampled timeline.

The benchmark uses an isolated controller/simulator instance, snapshots configured zones for synthetic zone/class conditions, and does not reset the live Camera Sources simulation or live signal-scenario runtime. The same-candidate network foundation does not change this single-junction experiment model.

### Stored experiment runs

- `GET /api/traffic/experiments?limit=50` — list compact run summaries.
- `GET /api/traffic/experiments/{run_id}` — load one complete result.
- `DELETE /api/traffic/experiments/{run_id}` — delete one stored result.
- `GET /api/traffic/experiments/{run_id}/export.csv` — export aligned Fixed/Adaptive timeline samples; preserves `X-Request-ID`.

Runtime JSON is stored under `outputs/simulation_experiments/` and excluded from source patches. Retention is bounded to the newest 200 runs.

## V027 two-intersection cooperative network experiments

### `POST /api/traffic/network-experiments`

Runs one isolated three-mode comparison over one enabled directed network link:

```json
{
  "duration_seconds": 300,
  "density": "normal",
  "seed": 27027,
  "sample_interval_seconds": 1,
  "profile": null,
  "label": "A to B cooperation comparison",
  "link_id": "a_to_b",
  "transfer_share_percent": 70,
  "cooperation_lookahead_seconds": 12.0,
  "cooperation_max_extension_seconds": 5.0,
  "cooperation_min_incoming_vehicles": 1
}
```

Rules:

- duration: 30-1800 seconds;
- density: `light | normal | busy`;
- `transfer_share_percent`: 0-100;
- cooperation lookahead: 1-60 seconds;
- cooperation max extension: 0-20 seconds;
- minimum predicted incoming vehicles: 1-20;
- `link_id` is optional; when omitted the first enabled link by id is selected;
- the selected link must connect two enabled configured intersections;
- a supplied `profile` overrides both intersection profiles and must exist in the saved signal config.

The result preserves V026 compatibility and adds a third mode:

- `fixed`;
- `adaptive` = Independent Adaptive;
- `cooperative` = Cooperative Adaptive;
- `comparison` = backward-compatible Adaptive-vs-Fixed comparison;
- `comparisons.adaptive_vs_fixed`;
- `comparisons.cooperative_vs_fixed`;
- `comparisons.cooperative_vs_adaptive`.

`scenario.arrival_plan` contains deterministic exogenous-demand counts plus a SHA-256 fingerprint. All three modes receive the same external arrival plan. `scenario.cooperation` snapshots lookahead/max-extension/min-incoming settings.

Each mode contains per-intersection waiting/queue/throughput/signal metrics, network transfer/corridor telemetry, a bounded timeline, and synthetic transfer evidence. Cooperative mode additionally contains:

- `cooperative_control_active: true`;
- `coordination_provenance: synthetic_predicted_arrivals`;
- `coordination_events` with deterministic coordination ID, link/source/destination identity, provenance, time, destination phase before advisory, incoming count, earliest ETA, action, applied flag, reason, and timing delta;
- `network_metrics.coordination` with evaluation/trigger/application counts, green extensions, protected progression requests, pedestrian-service protections, timing seconds added/reduced, and cooperation settings.

Fixed and Independent Adaptive report `cooperative_control_active: false`.

The coordinator uses transfers already discharged from the upstream intersection and scheduled inside the lookahead. During downstream vehicle green it may extend only within the saved phase maximum and maximum-cycle cap. During other phases it may request earlier protected progression by reducing only the current phase toward its configured minimum. It does not shorten pedestrian WALK/CLEAR while local pedestrian demand is active. Protected phase order is never skipped.

Network transfer, predicted arrivals, and cooperation are synthetic simulator evidence. Configured travel time is an experiment input, not measured/learned road travel time. Cooperative results may be better or worse for a selected synthetic scenario; the API makes no universal performance claim.

### Stored network experiment runs

- `GET /api/traffic/network-experiments?limit=50` — list compact `netexp_*` summaries.
- `GET /api/traffic/network-experiments/{run_id}` — load one complete result.
- `DELETE /api/traffic/network-experiments/{run_id}` — delete one stored network result.
- `GET /api/traffic/network-experiments/{run_id}/export.csv` — export aligned Fixed / Adaptive / Cooperative source/destination queue/service/signal fields plus transfer and cooperation timeline fields; preserves `X-Request-ID`.

Network experiment JSON remains under ignored runtime `outputs/simulation_experiments/`. Existing experiment storage errors `ATL-TRAFFIC-010..012` and network validation error `ATL-TRAFFIC-013` are reused.

## V025 ranked signal-scenario configuration

### `GET /api/traffic/signal-rules`

Returns the persisted/effective signal configuration. Top-level fields remain:

- `schema_version` (currently `1`);
- `mode`: `fixed | adaptive | test`;
- `dry_run`;
- `active_profile`;
- `profiles`.

Each profile keeps six protected phase entries with `base_seconds`, `min_seconds`, and `max_seconds`; `max_cycle_seconds`, `stale_data_seconds`, and `demand_memory_seconds`; compatibility `rules`; and V025 `scenarios`.

A scenario has the normalized shape:

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

Supported condition sources are `metric` and `zone_class_count`; supported comparison operators are `gt`, `gte`, `lt`, `lte`, and `eq`. A scenario supports `match: all | any` and 1-8 conditions. Rank `1` is highest and saved ranks are unique within each profile.

If an older saved profile has `rules` but no `scenarios`, V025 migrates the legacy rules into editable scenario definitions during validation. An explicitly present empty `scenarios` list remains empty and disables adaptive scenario actions for that profile.

### `PUT /api/traffic/signal-rules`

Body remains:

```json
{"config": {"schema_version": 1, "mode": "adaptive", "dry_run": false, "active_profile": "Normal", "profiles": {}}}
```

The complete configuration is validated before atomic persistence. Invalid scenario configuration uses `ATL-TRAFFIC-002`.

Saving while simulation is running re-anchors the current protected phase at the next simulation-clock evaluation; it does not replay elapsed time from zero.

### Ranked arbitration

In Adaptive/Test mode, every enabled scenario is evaluated against the current observation. Multiple scenarios may be triggered, but only the highest-ranked **eligible** scenario executes in one evaluation. A triggered scenario is not eligible when its observation is unavailable/stale, persistence is incomplete, current phase is not in its target list, or cooldown is active. The next eligible ranked scenario may then win.

Actions are bounded to `extend_current_phase`, `reduce_current_phase`, `hold_current_phase`, `request_next_phase`, or `incident_hold`. `request_next_phase` requests earlier progression through the existing protected sequence and does not directly jump conflicting movement phases.

### Other signal endpoints

- `POST /api/traffic/signal-rules/reset`
- `POST /api/traffic/signal-rules/runtime/reset`
- `POST /api/traffic/signal-rules/test-inputs`
- `POST /api/traffic/signal-rules/incident/clear`
- `POST /api/traffic/signal-rules/preview`
- `GET /api/traffic/signal-status`
- `GET /api/traffic/signal-rules/history?limit=200`
- `DELETE /api/traffic/signal-rules/history`

Manual `mobility_assistance` / `incident_person_fallen` values remain explicit Test-mode sources. They are not claims about live perception.

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

No API in V027 sends commands to physical/public-road traffic infrastructure. Signal scenarios, network topology, decision context, and experiments affect local simulation/recommendation/evaluation surfaces only.
