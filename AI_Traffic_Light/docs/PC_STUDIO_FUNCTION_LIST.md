# PC Studio Function List (V024 candidate highlights)

## Camera / simulation
- receive JPEG/PNG device frames;
- signal-aware synthetic scene with vehicle stop-line queues and pedestrian curb/WALK behavior;
- Light / Normal / Busy density and pause/resume;
- V023+ configurable protected simulated signal timing consumed by synthetic agents.

## Signal rules / traffic simulation
- edit six normal-operation phase base/min/max durations;
- Fixed, Adaptive, and Test operating modes plus dry-run;
- Normal / Pedestrian Priority / Vehicle Priority / Accessibility profiles;
- adaptive rules for crossing occupancy, slow crossing, pedestrian demand/max wait, low vehicle demand, vehicle queue/max wait;
- explicit Test-mode mobility/accessibility and fallen-person incident inputs without claiming unsupported live detection;
- protected transition order and protected minimum service;
- maximum phase/cycle limits, rule priorities, cooldown/retrigger protection, persistence/hysteresis, demand memory, and stale-data fallback;
- incident simulated all-red hold, explicit clear, safe recovery, and runtime-state reset;
- preview scenarios and live active/suppressed/inactive/unavailable rule explanations;
- persistent runtime signal-decision history with explicit clearing.

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
- runtime rule config/history, datasets, models, occupancy/flow history excluded from source patches;
- repository/version and patch-ZIP validation.


## V024 maintenance / reliability
- shared atomic JSON persistence for runtime settings, zones, and model-registry metadata;
- synchronized zone and model-registry state transitions;
- reusable non-overlapping App-level camera/live-context polling;
- architecture/regression guards for persistence and polling mechanics.

## Limitations / later

V023+ signal behavior remains a supervised local simulation. Wheelchair/mobility and fall detection are not live perception capabilities unless a compatible future model/source supplies them. The tracker is lightweight and not certified measurement. Future directions include model evaluation/quality, policy A/B simulation benchmarking, rule import/export, stronger tracking, and richer experiment reports. Physical public-road traffic control is explicitly outside scope.
