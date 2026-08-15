# Roadmap

## 0_2_1 — Traffic analytics and counting regions candidate

Status: V021 candidate, explicitly requested after V020. Previous candidate is `0_2_0`; owner-confirmed passed baseline remains `0_1_7`.

Current candidate capabilities include:

- camera/simulation receiver and controllable synthetic scene;
- capture deletion with paired metadata/manual-label lifecycle;
- camera-aligned persistent zones and Live AI overlays;
- real local YOLO training, convergence monitoring, and early stopping;
- trained-model registry/loading/live inference;
- simulation-only zone-aware traffic recommendations;
- sampled whole-frame pedestrian/vehicle occupancy history;
- analytics-only user-defined `counting_region` polygons;
- Traffic Analytics trend plotting, average/peak/busiest-region summaries, CSV export, and history clearing;
- persistent runtime settings and real backend logs;
- hardened version/agent/patch-validation workflow.

## Next useful prototype directions after an accepted baseline

- add cross-frame object tracking if unique passage/throughput counts are required;
- optional directional line-crossing/event counting built on verified track IDs;
- richer analytics filtering/session annotations;
- model evaluation/validation reporting;
- device-camera workflow completion;
- model export/runtime packaging.

## Explicitly outside scope

Physical public-road traffic signal control remains outside the project. Detection and analytics outputs are prototype/simulation information only.
