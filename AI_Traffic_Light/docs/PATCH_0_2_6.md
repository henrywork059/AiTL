# Patch 0_2_6 — deterministic two-intersection network simulation

## Release state

- current candidate: V026 / `0_2_6`;
- previous version: V025 / `0_2_5`;
- owner-confirmed passed baseline: V024 / `0_2_4`;
- V026 exists because the owner explicitly requested the next patch before separately accepting V025;
- automated validation does not promote the passed baseline.

## Goal

Convert the V025 network/topology identity foundation into a real deterministic **two-intersection simulation baseline** before adding neighbour-informed cooperation.

The target evidence is deliberately narrower than cooperation:

1. two intersections exist simultaneously in one isolated experiment;
2. each owns a separate controller runtime;
3. an enabled directed link transfers synthetic vehicles from the upstream intersection to the downstream intersection after its configured travel time;
4. Fixed and Adaptive receive the same exogenous demand plan;
5. results expose per-intersection and network telemetry;
6. neighbour context does **not** yet alter signal timing.

## Backend changes

### `app/services/network_simulation_experiments.py`

Adds a new isolated network benchmark service. It does not touch live Camera Sources simulation or the live signal controller.

One enabled configured link selects:

- source/upstream intersection;
- destination/downstream intersection;
- configured prototype travel time.

The service creates separate controller instances for both intersections in each comparison mode.

### Deterministic arrival plan

Density + seed generate bounded exogenous arrival plans for:

- upstream vehicles;
- downstream external vehicles;
- upstream pedestrians;
- downstream pedestrians.

The same exogenous plan is reused by Fixed and Adaptive. A configured `transfer_share_percent` marks a deterministic subset of upstream vehicle arrivals as corridor-transfer candidates. The stored scenario records arrival counts and a SHA-256 fingerprint of the canonical seeded plan so repeatability can be audited without duplicating the full event list in the result metadata.

### Synthetic transfer pipeline

When a transfer candidate is discharged from the upstream queue:

1. its upstream service time is recorded;
2. it enters the link pipeline;
3. scheduled downstream arrival = departure + configured `travel_time_seconds`;
4. it is added to the destination queue at that simulated time;
5. if later served downstream, the run records end-to-end corridor completion/travel time.

Per-vehicle transfer evidence contains vehicle id/class plus departure, scheduled arrival, and actual simulated arrival timestamps.

### Per-intersection observations

Each controller receives its own observation with:

- vehicles waiting;
- pedestrians waiting;
- zero crossing occupancy in this queue abstraction;
- synthetic zone/class counts for configured intersection zones where zone type semantics are known;
- `data_source: network_simulation_experiment`.

Vehicle-queue zones receive queued vehicle class counts. Pedestrian-waiting/crossing zones receive synthetic person counts. Counting-region zones may receive combined queued class counts. Counting lines remain excluded from scenario observations.

### Metrics

Per intersection:

- vehicle/pedestrian waiting distributions;
- queue average/p95/max/queue-seconds/occupied share;
- vehicles/pedestrians served;
- external/transfer arrivals;
- phase time/share;
- transitions/cycles;
- scenario applications and timing extension/reduction parsed from that intersection's isolated controller history.

Network aggregate:

- transfers departed/arrived;
- configured link travel time;
- pipeline average/peak occupancy;
- corridor completions and completions/minute;
- end-to-end corridor travel distribution;
- total vehicle wait;
- total vehicle queue average/p95/peak;
- Fixed-vs-Adaptive deltas.

### Persistence/API

Network experiment JSON uses `netexp_*.json` under the existing ignored runtime folder:

```text
outputs/simulation_experiments/
```

New endpoints:

- `POST /api/traffic/network-experiments`
- `GET /api/traffic/network-experiments`
- `GET /api/traffic/network-experiments/{run_id}`
- `GET /api/traffic/network-experiments/{run_id}/export.csv`
- `DELETE /api/traffic/network-experiments/{run_id}`

Existing `ATL-TRAFFIC-010..012` experiment persistence errors and `ATL-TRAFFIC-013` network validation error are reused; no new stable error code is required.

## Request example

```json
{
  "duration_seconds": 300,
  "density": "normal",
  "seed": 26026,
  "sample_interval_seconds": 1,
  "profile": null,
  "label": "A to B independent baseline",
  "link_id": "a_to_b",
  "transfer_share_percent": 70
}
```

If `link_id` is omitted, the first enabled link by id is selected. Both linked intersections must be enabled.

If `profile` is null, each intersection uses its configured `signal_profile`. A supplied profile overrides both for the experiment and must exist in the current saved signal configuration.

## Deliberate non-changes / limitations

V026 does **not**:

- feed predicted incoming demand into the downstream controller;
- coordinate green timing between intersections;
- add a cooperative scenario/action;
- add emergency priority;
- claim live multi-camera simultaneous retention/tracking;
- claim the configured travel time is measured/predicted real traffic time;
- add a new PC Studio network-experiment UI panel;
- change the existing single-junction Simulation Lab endpoint/result format;
- connect any decision to physical/public-road traffic infrastructure.

The V026 network benchmark is an independent-control evidence baseline for the next cooperation patch.

## Focused validation implemented

`scripts/test_network_simulation_experiments.py` checks:

- deterministic same-seed arrival generation;
- exactly the configured A→B link pair is used;
- source/destination each exist as separate runtime results;
- cooperation/emergency flags remain false;
- transfers depart and arrive;
- per-transfer simulated arrival minus departure equals configured link travel time;
- same seed/config produces identical Fixed, Adaptive, comparison, and scenario data apart from run metadata;
- persistent list/get/delete works;
- CSV includes source/destination phase, queues, service/scenario, pipeline, transfer, and corridor fields;
- thin FastAPI route integration preserves the standard JSON envelope/request ID and CSV `X-Request-ID`;
- missing enabled link is rejected through `ATL-TRAFFIC-013`.

## Owner acceptance summary

Before accepting V026, run the complete commands in `LOCAL_TESTING.md`, then verify the network endpoints with at least two configured intersections and one enabled directed link. Confirm transfer evidence exists and that no response claims `cooperative_control_active: true`.
