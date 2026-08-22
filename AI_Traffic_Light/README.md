# AI Traffic Light

Prototype traffic-light project with a FastAPI backend and React/Vite PC Studio frontend.

## Current candidate

- `0_2_5` — ranked signal scenarios, simulation telemetry, and network-foundation candidate.
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
- inspect winner/suppressed/inactive/unavailable scenarios with observed condition values;
- preview scenario evaluation without mutating the running controller and use explicit simulation-only accessibility/fall Test-mode inputs;
- run isolated seeded Fixed-vs-Adaptive simulation experiments without resetting the current camera simulation;
- compare wait, queue, throughput, phase-use, scenario-application, timing-adjustment, clearance, and conflict-overlap telemetry;
- persist/reopen/export/delete Simulation Lab runs;
- capture/delete/review/manual-label dataset images and build a managed YOLO dataset;
- run local Ultralytics YOLO training with convergence monitoring and patience-based early stopping;
- discover, choose, default, load, and delete trained models;
- run live trained-model inference with confidence/visibility controls and prototype cross-frame track IDs;
- create persistent camera-aligned traffic regions and two-point counting lines;
- keep sampled occupancy analytics separate from track-derived passage/region flow events;
- persist occupancy history, flow events, runtime settings, and inspect backend logs;
- configure generic prototype intersections and directed neighbour links without assuming exactly two intersections;
- resolve a camera/source id to an intersection identity while preserving the current single-junction runtime;
- expose explicit observation provenance and structured live decision context for judge/developer inspection.

## V025 ranked signal scenarios

Traffic Logic treats adaptive behavior as user-defined scenarios rather than a fixed list of hard-coded cases. Each scenario has a stable id/name, enabled state, numeric rank, ALL/ANY condition matching, persistence/cooldown guards, and one bounded signal response.

A condition can use either:

- a controller metric such as pedestrians waiting, vehicles queued, maximum wait duration, crossing dwell, or explicit Test-mode flags; or
- a **zone/class count**, for example `car > 5 in vehicle_queue_a` or `person >= 3 in pedestrian_waiting_west`. `*` can represent all detected classes in the selected polygon zone.

Rank `1` is highest and saved ranks are unique within each profile. Multiple scenarios may be true at the same time, but only the highest-ranked **eligible** scenario executes in a controller evaluation. A higher-ranked scenario that is disabled, stale/unavailable, in cooldown, or not permitted in the current protected phase does not block the next eligible scenario.

Existing V023 default adaptive rules are migrated into editable scenario definitions so inherited behavior remains available after update. The controller still enforces phase minimums, maximums, maximum-cycle bounds, protected transitions, and stale-observation fallback. Zone/class counts are per-frame detector observations, not throughput measurements.

## V025 Simulation Lab

Simulation Lab runs two isolated copies of the selected saved signal profile: one in Fixed mode and one in Adaptive mode. Both start from the same requested density and random seed. The benchmark uses its own controller and numeric-agent state, so it does not reset the live Camera Sources simulation or overwrite the live signal-scenario runtime state. It snapshots configured zones and supplies synthetic per-zone/per-class counts so zone-based scenarios can participate in Adaptive tests.

Experiment data is local prototype runtime output. Results describe only the selected seeded simulation and do not establish general traffic performance or public-road safety.

## Same-candidate intersection/network foundation

This V025 update adds `IntersectionNetworkService` without promoting V025 or starting V026.

Runtime configuration is stored at `config/intersections.json` and ignored by Git. The normalized schema contains:

- `active_intersection_id`;
- generic `intersections[]` with id, label, enabled state, source ids, optional zone ids, and signal-profile name;
- generic directed `links[]` with source/destination intersection, local/remote approach names, enabled state, and prototype travel-time estimate.

New traffic APIs:

- `GET /api/traffic/network`;
- `PUT /api/traffic/network`;
- `POST /api/traffic/network/reset`;
- `GET /api/traffic/network/context?intersection_id=...`.

The current live camera/tracker/controller runtime is still single-junction. Network configuration therefore provides identity/topology/context only. It does **not** yet coordinate timings, transfer simulated vehicles between intersections, predict arrivals, or run emergency pre-emption.

## Structured live decision context

`GET /api/traffic/state` retains all existing V025 fields and now also returns:

- `intersection_id`;
- `observation_provenance`: `ai_detection`, `simulation`, `manual_test`, or `unavailable`;
- `network_context` with configured neighbour links;
- `decision_context` with a deterministic decision id, trigger category, winning scenario/conditions when available, requested service, timing, pedestrian/vehicle context, neighbour context, explicit emergency-placeholder state, and a human-readable explanation.

This context is an explanation projection only. Existing `outputs/signal_rules/decision_history.jsonl` remains the persisted controller-event history. Emergency recognition/pre-emption is not implemented, and the decision context explicitly reports that state instead of implying it exists.

## Signal-policy semantics

The V025 controller starts from user-configured normal phase durations. Adaptive/Test modes evaluate the active profile's ranked scenarios against fresh observations. Only one eligible scenario wins each evaluation. Its response may extend/reduce/hold the current simulated phase, request protected service sooner, or enter the explicit Test-mode incident hold, always within validated phase/cycle limits. Yellow/all-red transition ordering remains protected; scenario logic cannot jump directly between conflicting movement phases.

`mobility_assistance` and `incident_person_fallen` remain explicit Test-mode inputs. The current detector is **not** claimed to identify wheelchairs, mobility aids, falls, or emergency vehicles unless a future compatible perception source is added.

## Analytics semantics

- **Occupancy** — sampled counts showing detections currently present in a frame/region. Runtime data is under `outputs/traffic_history/`.
- **Flow** — track-derived events. A unique passage is counted only when one stable prototype track crosses one configured `counting_line`; region entry/exit/dwell are separate event types under `outputs/traffic_flow/`.
- **Simulation experiments** — isolated synthetic A/B telemetry derived from the numeric simulator/controller, not from stored occupancy or tracking histories. Runtime data is under `outputs/simulation_experiments/`.
- **Network links** — configured topology metadata only; they are not measured vehicle transfers or cooperative-control outputs.

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
- `docs/ARCHITECTURE.md`

Repository helpers:

```powershell
python .\scripts\check_structure.py
python .\scripts\validate_patch_zip.py <patch.zip>
```

## Safety scope

AiTL is a local/student-scale prototype for simulation, classroom work, computer-vision experiments, and supervised testing. Signal rules, recommendations, detections, tracking, analytics, topology links, decision context, experiment results, and GUI signal states are not connected to real public-road traffic infrastructure and must not be described as production-road control.
