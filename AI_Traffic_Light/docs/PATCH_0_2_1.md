# Patch 0_2_1 — Traffic occupancy analytics and counting regions

## Release state

- Current candidate: V021 / `0_2_1`.
- Previous candidate: V020 / `0_2_0`.
- Owner-confirmed passed baseline: V017 / `0_1_7`.
- The owner explicitly requested V021 as the next patch even though V020 was not separately promoted. This patch does not change `passed_baseline`.

## Requested functions

### Pedestrian and vehicle occupancy over time

- Records detection-backed whole-frame pedestrian and vehicle occupancy with timestamps, source timestamps, frame numbers, simulation phase, and decision context.
- Uses a bounded JSONL history under `outputs/traffic_history/history.jsonl`; this is runtime data and is never packaged in source patches.
- Samples are deduplicated and only written when a valid detection frame exists, so camera/model downtime does not create misleading manufactured zero samples.
- Default target sampling interval is 1 second and default retention is 21,600 samples (approximately six hours at continuous one-second sampling). Environment overrides are supported.

### Counting inside defined regions

- Adds `counting_region` to the existing persistent camera-aligned zone system.
- Multiple counting regions can coexist and overlap.
- Each region reports pedestrians, vehicles, and combined total.
- `counting_region` is analytics-only and does not participate in the simulation traffic-phase rules.
- Existing waiting/crossing/queue zones also expose analytics counts. Ignore zones take priority and exclude detections from analytics.

## Three additional functions selected for V021

1. **CSV export** for the selected time window and whole-frame/region scope.
2. **Explicit history reset** that clears only traffic analytics history and preserves captures, labels, zones, settings, models, and training outputs.
3. **Analytics summaries** with current/average/peak pedestrian and vehicle occupancy, peak timestamps, busiest-region context, and simulation phase-change context.

## Frontend

- Adds a Traffic Analytics page under Traffic setup & analytics.
- Supports 1 minute, 5 minutes, 15 minutes, 1 hour, 6 hours, and all-retained windows.
- Supports Whole frame or one configured region as the active scope.
- The SVG chart uses real recorded timestamps on the x-axis so gaps in recording remain visible.

## API additions

- `GET /api/traffic/history?minutes=...&limit=...&region_id=...`
- `GET /api/traffic/history/export.csv?minutes=...&limit=...&region_id=...`
- `DELETE /api/traffic/history`
- `GET /api/traffic/state` additionally returns `pedestrians_total`, `vehicles_total`, `evaluated_at_ms`, `source_timestamp_ms`, and `region_counts`.

Stable traffic-history errors:

- `ATL-TRAFFIC-004` — traffic history read failed
- `ATL-TRAFFIC-005` — traffic history write/compaction failed
- `ATL-TRAFFIC-006` — traffic history clear failed

## Important counting limitation

These values are **sampled occupancy**, not unique passage/throughput counts. A vehicle visible in ten samples contributes one occupied vehicle to each of those ten samples; it is not counted as ten unique vehicles. Reliable unique passage counts require cross-frame tracking with stable track IDs and are intentionally not claimed by this patch.

## Signal-aware simulation refinement

- Replaces the previous position-from-clock animation with persistent synthetic vehicle and pedestrian agents.
- Vehicles stay in horizontal road lanes, approach the crossing, queue behind direction-specific stop lines during yellow/all-red/pedestrian phases, and resume only on vehicle green. Vehicles already committed past a stop line are allowed to clear the crossing rather than stopping inside it.
- Pedestrians approach the curb from both sides, wait outside the road until `pedestrian_green` (WALK), then traverse the zebra crossing. `pedestrian_flashing` is a CLEAR interval: pedestrians already crossing continue, but new crossings do not begin.
- Uses a deterministic 34-second cycle: 12 s vehicle green, 3 s vehicle yellow, 3 s all-red, 8 s pedestrian WALK, 6 s pedestrian CLEAR, 2 s all-red.
- The simulated camera frame visibly renders stop lines, vehicle/pedestrian signal heads, phase, and seconds remaining.
- Camera status exposes `simulation_signal_phase`, `simulation_signal_seconds_remaining`, `simulation_signal_cycle_seconds`, `simulation_signal_vehicle_go`, and `simulation_signal_pedestrian_walk`.
- In simulation mode the traffic-state `phase` is aligned to the active simulation signal so Live AI signal graphics cannot contradict agent motion. Detection-driven output remains available as `recommended_phase`, `recommended_decision`, and `recommended_decision_reason`.
- This remains a local visualization/simulation model only; it is not traffic engineering timing logic and is not connected to physical signals.

## Compatibility and safety

V020 capture deletion, camera-aligned zone editing, Live AI zone overlays, Show zones control, and compact simulated traffic signal remain in scope. V017 training convergence/early stopping, settings/logs, model management, capture/label/build/training, and inference behavior remain regression requirements.

Traffic decisions remain supervised simulation/recommendation/display outputs only and are not connected to physical public-road traffic infrastructure.

## Validation focus

Run Python compilation, `scripts/test_zone_traffic_services.py`, `scripts/test_traffic_history_service.py`, existing backend regressions, live `scripts/test_backend_smoke.py`, `scripts/check_structure.py`, frontend `npm run typecheck`, frontend `npm run build`, full-repository `git diff --check`, and final ZIP validation. Automated checks do not mark V021 passed; owner acceptance is required.
