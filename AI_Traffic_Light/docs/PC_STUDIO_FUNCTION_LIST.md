# PC Studio Function List (V025 candidate highlights)

## Camera / simulation
- receive JPEG/PNG device frames;
- signal-aware synthetic scene with vehicle stop-line queues and pedestrian curb/WALK behavior;
- Light / Normal / Busy density and pause/resume;
- V023+ configurable protected simulated signal timing consumed by synthetic agents.

## Signal scenarios / traffic simulation
- edit six protected normal-operation phase base/min/max durations;
- Fixed, Adaptive, and Test modes plus dry-run;
- Normal / Pedestrian Priority / Vehicle Priority / Accessibility profiles;
- create, duplicate, delete, enable/disable, and rank editable scenarios (`1` highest);
- define 1–8 conditions per scenario using ALL/ANY matching;
- use controller metrics or detected class counts inside a selected polygon zone (`*` = all detected classes);
- choose `>`, `>=`, `<`, `<=`, or `=` comparison and numeric threshold;
- define bounded response: extend/reduce/hold current phase, request protected next phase sooner, or Test-mode incident all-red hold;
- choose which protected phase keys may execute the response and optionally request pedestrian/vehicle service;
- execute only the highest-ranked eligible triggered scenario per arbitration evaluation;
- explain winner/suppressed/inactive/unavailable states and show observed condition values;
- persistence, cooldown, demand memory, stale fallback, protected minimums/max/cycle bounds, incident recovery, and runtime-state reset;
- migrate older V023/V024 rule configs into editable scenarios while retaining compatibility fields;
- persistent runtime signal-decision history with explicit clearing.

## V025 Simulation Lab / experiments
- isolated Fixed-vs-Adaptive runs using the same selected profile, density, duration, and random seed;
- no reset/mutation of the currently running camera simulation or live controller state; configured zones are snapshotted so synthetic zone/class scenarios can participate;
- vehicle/pedestrian wait count, average, median, p95, maximum, and total delay;
- queue average, p95, peak, queue-seconds, queue-active share, and simultaneous vehicle/pedestrian queue time;
- vehicle/pedestrian/combined throughput and vehicle passages per green minute;
- phase utilization, transitions, cycles, clearance time/share, adaptive scenario applications, and timing extension/reduction totals;
- simulator-only conflict-overlap diagnostic;
- bounded persisted experiment history under `outputs/simulation_experiments/`, reopen/delete, and aligned Fixed/Adaptive sample CSV export;
- one-page Simulation Lab grouped with setup/stored-run controls and Summary / Waiting & queues / Throughput / Signal behavior / Raw samples tabs;
- Fixed/Adaptive raw-sample toggle, page-size menu, and pagination rather than an unbounded table.

## Inference / zones / analytics
- trained-model inference and V022 cross-frame prototype IDs;
- camera-aligned waiting/crossing/queue/counting/ignore geometry;
- sampled whole-frame/region occupancy history;
- counting-line directional unique-passage events;
- region entry/exit/dwell and pedestrian waiting dwell;
- separate Occupancy and Flow / Tracks analytics with CSV exports.

## Dataset / training / model management
- capture/delete/review/manual-label frames;
- managed YOLO train/validation dataset;
- local Ultralytics training, convergence and early stopping;
- model registry/load/default/delete.

## System / development integrity
- persistent runtime settings and recent logs;
- canonical root `VERSION` metadata;
- runtime signal-scenario config/history, datasets, models, occupancy/flow/experiment history excluded from source patches;
- repository/version and patch-ZIP validation.

## V024 maintenance / reliability retained
- shared atomic JSON persistence for runtime settings, zones, and model-registry metadata;
- synchronized zone and model-registry state transitions;
- reusable non-overlapping App-level camera/live-context polling;
- architecture/regression guards for persistence and polling mechanics.

## Limitations / later

V025 experiment results remain supervised local synthetic simulation data. The benchmark is not a calibrated traffic microsimulator or public-road safety evaluation. Wheelchair/mobility and fall detection are not live perception capabilities unless a compatible future model/source supplies them. The tracker is lightweight and not certified measurement. Future directions include model evaluation/quality, richer exogenous demand generators, policy import/export, stronger tracking, and richer experiment reports. Physical public-road traffic control is explicitly outside scope.
