# Roadmap

## 0_2_3 — Configurable adaptive signal rules candidate

Status: V023 candidate. Previous version and owner-confirmed passed baseline are V022 / `0_2_2`.

V023 adds a configurable adaptive signal simulation layer on top of the accepted V022 camera/dataset/training/inference/tracking/occupancy/flow baseline:

- editable normal signal phase timing with protected min/base/max values;
- Fixed / Adaptive / Test modes and simple policy profiles;
- bounded adaptive pedestrian/vehicle timing rules;
- starvation-oriented maximum-wait rules, rule persistence/hysteresis, cooldowns, demand memory, stale-data fallback, and maximum-cycle bounds;
- protected transition order/minimum service;
- explicit manual accessibility/incident test inputs and all-red incident hold/recovery;
- dry scenario preview, live rule arbitration explanation, and runtime decision history;
- persistent user rule configuration excluded from source patches.

## Next useful prototype directions after V023 acceptance

- model evaluation / dataset quality: validation precision, recall, mAP50, mAP50-95, per-class metrics, confusion matrix, false-positive/false-negative review, dataset class distribution and quality warnings;
- fixed-vs-adaptive repeatable A/B simulation using identical random seeds and wait/queue/service metrics;
- signal-policy import/export and richer experiment/session reports;
- stronger tracking/motion prediction and track-quality diagnostics;
- optional compatible accessibility/incident perception research, clearly separated from manual Test inputs;
- device-camera workflow completion and model export/runtime packaging.

## Explicitly outside scope

Physical public-road traffic signal control remains outside the project. Detection, tracking, analytics, rule evaluation, timing changes, and phase outputs are prototype/simulation information only.
