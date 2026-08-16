# Roadmap

## 0_2_4 — Maintenance hardening and polling optimization candidate

Status: V024 candidate. Previous candidate is V023 / `0_2_3`; owner-confirmed passed baseline remains V022 / `0_2_2` because V023 was not explicitly accepted.

V024 hardens the existing prototype without changing its user-facing signal semantics:

- shared atomic JSON replacement for runtime settings, zones, and model-registry metadata;
- synchronized zone writes and model-registry state transitions;
- reusable non-overlapping App-level camera/live-context polling;
- architecture/regression guards for those maintenance boundaries;
- preservation of the V023 design system and adaptive-signal behavior.

### Inherited V023 adaptive simulation layer

V023 introduced:

- editable normal signal phase timing with protected min/base/max values;
- Fixed / Adaptive / Test modes and simple policy profiles;
- bounded adaptive pedestrian/vehicle timing rules;
- starvation-oriented maximum-wait rules, rule persistence/hysteresis, cooldowns, demand memory, stale-data fallback, and maximum-cycle bounds;
- protected transition order/minimum service;
- explicit manual accessibility/incident test inputs and all-red incident hold/recovery;
- dry scenario preview, live rule arbitration explanation, and runtime decision history;
- persistent user rule configuration excluded from source patches.

## Next useful prototype directions after V024 acceptance

- continue consolidating page-specific periodic polling where serial scheduling provides measurable benefit;
- pin/automate frontend dependency updates instead of indefinitely relying on broad `latest` declarations;
- model evaluation / dataset quality: validation precision, recall, mAP50, mAP50-95, per-class metrics, confusion matrix, false-positive/false-negative review, dataset class distribution and quality warnings;
- fixed-vs-adaptive repeatable A/B simulation using identical random seeds and wait/queue/service metrics;
- signal-policy import/export and richer experiment/session reports;
- stronger tracking/motion prediction and track-quality diagnostics;
- optional compatible accessibility/incident perception research, clearly separated from manual Test inputs;
- device-camera workflow completion and model export/runtime packaging.

## Explicitly outside scope

Physical public-road traffic signal control remains outside the project. Detection, tracking, analytics, rule evaluation, timing changes, and phase outputs are prototype/simulation information only.
