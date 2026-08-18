# AI Traffic Light

Prototype traffic-light project with a FastAPI backend and React/Vite PC Studio frontend.

## Current candidate

- `0_2_4` — maintenance hardening and polling optimization candidate, preserving V023 adaptive signal behavior.
- Previous version/candidate: `0_2_3`.
- Owner-confirmed passed baseline: `0_2_2`.
- V024 was explicitly requested before V023 was explicitly accepted, so V023 is not treated as a passed baseline.

## Implemented prototype functions

- receive or simulate camera frames;
- run a stateful signal-aware synthetic junction where vehicles queue at stop lines and pedestrians wait for WALK before using the zebra crossing;
- choose Light / Normal / Busy simulation density and pause/resume an inspection frame;
- configure normal simulated phase min/base/max timings for vehicle green, yellow, both all-red clearances, pedestrian WALK, and pedestrian CLEAR;
- run Fixed, Adaptive, or Test signal-policy modes with named profiles;
- apply bounded adaptive rules for crossing occupancy/slow crossing, heavy pedestrian demand, pedestrian maximum wait, low vehicle demand, heavy vehicle queues, vehicle maximum wait, and Test-mode mobility/incident conditions;
- use persistence, demand memory, cooldowns, priorities, per-phase caps, maximum-cycle limits, protected transitions, and stale-data fallback;
- inspect active/suppressed/unavailable rules, pending demand, effective phase duration, and decision history;
- preview rule scenarios without mutating the running controller and use explicit simulation-only accessibility/fall test inputs;
- capture/delete/review/manual-label dataset images and build a managed YOLO dataset;
- run local Ultralytics YOLO training with convergence monitoring and patience-based early stopping;
- discover, choose, default, load, and delete trained models;
- run live trained-model inference with confidence/visibility controls and prototype cross-frame track IDs;
- create persistent camera-aligned traffic regions and two-point counting lines;
- keep sampled occupancy analytics separate from track-derived passage/region flow events;
- persist occupancy history, flow events, runtime settings, and inspect backend logs.


## V024 maintenance integrity

- Shared `app/core/json_store.py` atomically replaces runtime-settings, zone, and model-registry JSON using unique same-directory temporary files.
- Zone writes and model-registry transitions are synchronized inside their services.
- Top-level camera-status and Live AI traffic/zone refreshes use reusable serial polling so one slow request cannot overlap the next scheduled poll from the same loop.
- API endpoints, stable error codes, signal-rule semantics, and dataset/model formats are unchanged.
- PC Studio presentation is refined with role-based primary/secondary/surface/on-color semantics and clearer current-task copy; this is a presentation-only change.

## Signal-policy semantics

The V023+ controller starts from user-configured normal phase durations. Adaptive rules can extend or reduce the current simulated phase only within validated min/max bounds and the configured cycle cap. Yellow/all-red transition ordering remains protected; adaptive logic cannot jump directly between conflicting movement phases.

If detection observations are stale/unavailable, Adaptive mode falls back to the saved normal timings. Short detection dropouts retain demand briefly, and rule persistence/cooldown prevents single-frame spikes or repeated per-poll extensions.

`mobility_assistance` and `incident_person_fallen` are supported as explicit Test-mode inputs. The current detector is **not** claimed to identify wheelchairs, mobility aids, or falls unless a future compatible perception source is added.

Signal-rule configuration is stored locally in `config/signal_rules.json`. Decision history is runtime data under `outputs/signal_rules/decision_history.jsonl`; both are excluded from source patch archives.

## Analytics semantics

- **Occupancy** — sampled counts showing detections currently present in a frame/region. Runtime data is under `outputs/traffic_history/`.
- **Flow** — track-derived events. A unique passage is counted only when one stable prototype track crosses one configured `counting_line`; region entry/exit/dwell are separate event types under `outputs/traffic_flow/`.

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
- `docs/PATCH_0_2_4.md`

Repository helpers:

```powershell
python .\scripts\check_structure.py
python .\scripts\validate_patch_zip.py <patch.zip>
```

## Safety scope

AiTL is a local/student-scale prototype for simulation, classroom work, computer-vision experiments, and supervised testing. Signal rules, recommendations, detections, tracking, analytics, and GUI signal states are not connected to real public-road traffic infrastructure and must not be described as production-road control.
