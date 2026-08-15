# Roadmap

## 0_2_2 — Cross-frame tracking and flow analytics candidate

Status: V022 candidate, explicitly requested after V021. Previous candidate is `0_2_1`; owner-confirmed passed baseline remains `0_1_7` until explicit owner acceptance.

Current candidate capabilities include:

- receiver/signal-aware simulation camera workflow;
- persistent capture/review/manual-label lifecycle and managed YOLO dataset build;
- local YOLO training with convergence monitoring and early stopping;
- trained-model registry/loading/live inference;
- camera-aligned persistent traffic zones and Live AI overlays;
- V021 sampled whole-frame/region occupancy history and Traffic Analytics;
- V022 frame-deduplicated cross-frame prototype track IDs;
- analytics-only two-point `counting_line` geometry;
- one directional passage event per track/counting-line pair;
- tracked polygon-region entry/exit and completed dwell duration;
- pedestrian waiting-zone dwell summary;
- bounded persistent flow-event history, filters, minute buckets, CSV export, and explicit clearing;
- signal-aware synthetic agents and simulation-only traffic recommendations;
- persistent runtime settings/logs and hardened patch/version workflow.

## Next useful prototype directions after an accepted baseline

- improve tracking robustness with optional motion prediction / stronger assignment and track confidence diagnostics;
- add model evaluation/validation reporting, per-class precision/recall/mAP, confusion matrix, and model comparison;
- add a configurable simulation scenario lab with arrival rates, signal timings, random seeds, and repeatable comparisons;
- richer event/session annotations and experiment reports;
- device-camera workflow completion;
- model export/runtime packaging.

## Explicitly outside scope

Physical public-road traffic signal control remains outside the project. Detection, tracking, flow analytics, and phase outputs are prototype/simulation information only.
