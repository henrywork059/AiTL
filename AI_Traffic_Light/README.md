# AI Traffic Light

Prototype traffic-light project with a FastAPI backend and React/Vite PC Studio frontend.

## Current candidate

- `0_2_5` — ranked signal scenarios and simulation telemetry candidate.
- Previous version/candidate: `0_2_4`.
- Owner-confirmed passed baseline: `0_2_4`.
- V024 was explicitly accepted/promoted by the owner. V025 remains the current candidate and is not yet part of the passed baseline.

## Implemented prototype functions

- receive or simulate camera frames;
- run a stateful signal-aware synthetic junction where vehicles queue at stop lines and pedestrians wait for WALK before using the zebra crossing;
- choose Light / Normal / Busy simulation density and pause/resume an inspection frame;
- configure normal simulated phase min/base/max timings for vehicle green, yellow, both all-red clearances, pedestrian WALK, and pedestrian CLEAR;
- run Fixed, Adaptive, or Test signal-policy modes with named profiles;
- define editable ranked signal scenarios from controller metrics or detected class counts inside configured zones;
- combine scenario conditions with ALL/ANY matching, persistence, cooldowns, explicit rank, bounded phase actions, and optional pedestrian/vehicle service requests;
- arbitrate multiple triggered scenarios so only the highest-ranked eligible scenario executes each evaluation while protected timing/order remains enforced;
- inspect winner/suppressed/inactive/unavailable scenarios with the observed condition values that caused each state;
- preview scenario evaluation without mutating the running controller and use explicit simulation-only accessibility/fall Test-mode inputs;
- run isolated seeded Fixed-vs-Adaptive simulation experiments without resetting the currently running camera simulation;
- compare average/median/p95/maximum waits, queue pressure and queue-seconds, queue-active time, throughput, combined service rate, vehicle-green efficiency, phase utilization, clearance time, adaptive scenario applications, timing extensions/reductions, and a simulation conflict-overlap diagnostic;
- persist experiment results under `outputs/simulation_experiments/`, reopen them from Simulation Lab, export aligned Fixed/Adaptive timeline samples as CSV, and explicitly delete stored runs;
- capture/delete/review/manual-label dataset images and build a managed YOLO dataset;
- run local Ultralytics YOLO training with convergence monitoring and patience-based early stopping;
- discover, choose, default, load, and delete trained models;
- run live trained-model inference with confidence/visibility controls and prototype cross-frame track IDs;
- create persistent camera-aligned traffic regions and two-point counting lines;
- keep sampled occupancy analytics separate from track-derived passage/region flow events;
- persist occupancy history, flow events, runtime settings, and inspect backend logs.

## V025 ranked signal scenarios

Traffic Logic now treats adaptive behavior as user-defined scenarios rather than a fixed list of hard-coded cases. Each scenario has a stable id/name, enabled state, numeric rank, ALL/ANY condition matching, persistence/cooldown guards, and one bounded signal response.

A condition can use either:

- a controller metric such as pedestrians waiting, vehicles queued, maximum wait duration, crossing dwell, or explicit Test-mode flags; or
- a **zone/class count**, for example `car > 5 in vehicle_queue_a` or `person >= 3 in pedestrian_waiting_west`. `*` can represent all detected classes in the selected polygon zone.

Rank `1` is highest and saved ranks are unique within each profile. Multiple scenarios may be true at the same time, but only the highest-ranked **eligible** scenario executes in a controller evaluation. A higher-ranked scenario that is disabled, stale/unavailable, in cooldown, or not permitted in the current protected phase does not block the next eligible scenario. The page shows the winner and explains the state of every scenario.

Existing V023 default adaptive rules are migrated into editable scenario definitions so inherited behavior remains available after update. The controller still enforces phase minimums, maximums, maximum-cycle bounds, protected transitions, and stale-observation fallback. Zone/class counts are per-frame detector observations, not throughput measurements.

## V025 Simulation Lab

Simulation Lab runs two isolated copies of the current saved signal profile: one in Fixed mode and one in Adaptive mode. Both start from the same requested density and random seed. The benchmark uses its own controller and numeric agent state, so it does not reset the live Camera Sources simulation or overwrite the live signal-scenario runtime state. It snapshots the currently configured zones and supplies synthetic per-zone/per-class counts to the isolated controller, allowing zone-based scenarios to participate in Fixed-vs-Adaptive tests.

The page is intentionally clamped into one working surface. Setup and stored-run controls remain visible at the top; Summary, Waiting & queues, Throughput, Signal behavior, and Raw samples are grouped behind tabs. Raw one-second telemetry is paginated and can be switched between Fixed and Adaptive rather than expanding into a long dashboard.

Experiment data is prototype runtime output. Results describe only the selected seeded simulation and do not establish general traffic performance or public-road safety.

## V024 maintenance integrity

- Shared `app/core/json_store.py` atomically replaces runtime-settings, zone, and model-registry JSON using unique same-directory temporary files.
- Zone writes and model-registry transitions are synchronized inside their services.
- Top-level camera-status and Live AI traffic/zone refreshes use reusable serial polling so one slow request cannot overlap the next scheduled poll from the same loop.
- PC Studio presentation uses role-based primary/secondary/surface/on-color semantics and current-task copy.

## Signal-policy semantics

The V025 controller starts from user-configured normal phase durations. Adaptive/Test modes evaluate the active profile's ranked scenarios against fresh observations. Only one eligible scenario wins each evaluation. Its response may extend/reduce/hold the current simulated phase, request protected service sooner, or enter the explicit Test-mode incident hold, always within validated phase/cycle limits. Yellow/all-red transition ordering remains protected; scenario logic cannot jump directly between conflicting movement phases.

Zone/class conditions use per-frame detector class counts for configured polygon zones. Missing/deleted zones are reported as unavailable instead of silently treated as a zero count. Controller-metric conditions retain bounded demand memory; scenario persistence/cooldown prevents single-frame spikes or repeated accumulation. If observations are stale/unavailable, Adaptive mode falls back to the saved normal timings.

`mobility_assistance` and `incident_person_fallen` remain explicit Test-mode inputs. The current detector is **not** claimed to identify wheelchairs, mobility aids, or falls unless a future compatible perception source is added.

Signal scenario/timing configuration is stored locally in `config/signal_rules.json`. Decision history is runtime data under `outputs/signal_rules/decision_history.jsonl`; both are excluded from source patch archives.

## Analytics semantics

- **Occupancy** — sampled counts showing detections currently present in a frame/region. Runtime data is under `outputs/traffic_history/`.
- **Flow** — track-derived events. A unique passage is counted only when one stable prototype track crosses one configured `counting_line`; region entry/exit/dwell are separate event types under `outputs/traffic_flow/`.
- **Simulation experiments** — isolated synthetic A/B telemetry derived from the numeric simulator/controller, not from the stored occupancy or tracking histories. Runtime data is under `outputs/simulation_experiments/`.

The tracker remains a lightweight class-aware centroid/IoU prototype and may lose/swap IDs under occlusion, abrupt movement, or crowded same-class scenes.

## Development integrity

The root `VERSION` file is authoritative. Backend release metadata is loaded through `apps/pc-studio/backend/app/core/project_version.py`; frontend release fallback/navigation uses `apps/pc-studio/frontend/src/constants/projectVersion.ts` and is checked by repository validation.

Useful entry points:

- `AGENTS.md`
- `docs/AI_AGENT_GUIDE.md`
- `docs/AI_AGENT_CHECKLIST.md`
- `docs/LOCAL_TESTING.md`
- `docs/TEST_READY_CHECKLIST.md`
- `docs/API_CONTRACTS.md`
- `docs/PATCH_0_2_5.md`

Repository helpers:

```powershell
python .\scripts\check_structure.py
python .\scripts\validate_patch_zip.py <patch.zip>
```

## Safety scope

AiTL is a local/student-scale prototype for simulation, classroom work, computer-vision experiments, and supervised testing. Signal rules, recommendations, detections, tracking, analytics, experiment results, and GUI signal states are not connected to real public-road traffic infrastructure and must not be described as production-road control.
