# PC Studio Function List

This is a current capability catalog. Read root `VERSION` / `START_HERE.md` for candidate state and `PROJECT_SCOPE.md` for implemented/foundation/planned capability status.

## Camera / live simulation

- receive JPEG/PNG device frames;
- signal-aware synthetic single-junction scene with vehicle queues and pedestrian WALK behavior;
- Light / Normal / Busy density and pause/resume;
- configurable protected simulated signal timing consumed by synthetic agents.

## Signal scenarios / traffic simulation

- edit protected phase base/min/max durations;
- Fixed, Adaptive, and Test modes plus dry-run preview;
- named signal profiles;
- create/duplicate/delete/enable/disable/rank scenarios (`1` highest);
- 1–8 ALL/ANY conditions;
- controller metrics and zone/class counts (`*` supported for all classes in a selected polygon zone);
- bounded extend/reduce/hold/request-next-protected-service/Test incident actions;
- protected target-phase selection and optional pedestrian/vehicle request;
- one highest-ranked eligible winner per evaluation;
- winner/suppressed/inactive/unavailable explanations and observed values;
- persistence, cooldown, demand memory, stale fallback, phase/cycle bounds, incident recovery;
- persistent runtime signal-decision history.

## Single-junction Simulation Lab

- isolated Fixed-vs-Adaptive seeded comparisons without resetting live camera/controller state;
- configured zone snapshot and synthetic per-zone/per-class observations;
- wait distributions, queue pressure, throughput/service, vehicle-green efficiency;
- phase utilization, transitions/cycles, clearance, scenario applications, timing changes, conflict diagnostic;
- bounded persisted experiment history, reopen/delete, CSV export;
- grouped Summary / Waiting & queues / Throughput / Signal behavior / Raw samples presentation with bounded pagination.

## V027 two-intersection cooperative network experiment

- API/test-first isolated network benchmark using one enabled directed configured link;
- two simultaneously modeled intersections with separate signal-controller runtime;
- Fixed, Independent Adaptive, and Cooperative Adaptive modes receive the same deterministic exogenous demand plan;
- selected synthetic upstream vehicles enter an explicit transfer pipeline and arrive downstream after configured `travel_time_seconds`;
- Cooperative Adaptive consumes predicted transfer arrivals inside a configurable lookahead;
- bounded downstream vehicle-green extension respects saved phase maximum/cycle cap;
- earlier vehicle-service preparation may reduce only the current protected phase toward its minimum;
- active local pedestrian demand blocks cooperation-driven shortening of pedestrian WALK/CLEAR;
- structured cooperation events include predicted incoming count, ETA, action, reason, and timing delta;
- per-intersection wait/queue/throughput/signal/scenario telemetry plus network transfer/corridor/coordination telemetry;
- pairwise comparisons: Adaptive vs Fixed, Cooperative vs Fixed, Cooperative vs Adaptive;
- persistent `netexp_*` list/get/delete and aligned three-mode CSV export;
- emergency priority remains inactive.

The current PC Studio Simulation Lab UI remains single-junction; V027 network/cooperation experiments are backend/API/test-first.

## Network / explanation foundation

- configure generic intersection IDs, source IDs, labels, optional zone IDs/profile names;
- configure directed neighbour links and prototype travel-time metadata;
- resolve source ID to intersection;
- query per-intersection neighbour context;
- enrich live traffic state with intersection ID, observation provenance, network context, and structured decision context;
- explicit inactive flags for cooperative control and emergency priority.

Live configured links remain topology metadata. Synthetic transfer and bounded cooperation exist only inside the V027 isolated network experiment.

## Inference / zones / analytics

- local trained-model inference and prototype cross-frame track IDs;
- camera-aligned waiting/crossing/queue/counting/ignore regions and counting lines;
- sampled whole-frame/region occupancy history;
- counting-line directional passage events;
- region entry/exit/dwell and pedestrian waiting dwell;
- separate Occupancy and Flow/Tracks analytics with CSV export.

## Dataset / training / model management

- capture/delete/review/manual-label frames;
- managed YOLO train/validation dataset;
- local Ultralytics training with convergence monitoring and patience-based early stopping;
- model registry/load/default/delete.

## System / development integrity

- persistent runtime settings and recent logs;
- root `VERSION` release metadata;
- atomic JSON persistence for migrated runtime stores and intersection config;
- non-overlapping App-level polling helper;
- repository/version and patch-ZIP validation;
- documentation authority/scope guides.

## Planned capability families

See `PROJECT_SCOPE.md` / `ROADMAP.md`:

- bounded multi-intersection cooperation using neighbour/arrival context;
- emergency priority;
- stronger pedestrian-aware control;
- broader vehicle-class behavior;
- persistent structured explainability.

## Limitations

Experiment data is seeded synthetic evidence only. The tracker is lightweight. Zone/class counts are per-frame observations. Live configured network links are metadata; V027 transfer/predicted-arrival/coordination events are simulator-generated evidence, not measured vehicle movement. Wheelchair/mobility/fall/emergency recognition must not be claimed without a compatible perception source. Physical/public-road traffic control is outside scope.
