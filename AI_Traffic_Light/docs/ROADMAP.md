# Roadmap

## 0_2_5 — Ranked signal scenarios and simulation telemetry candidate

Status: V025 candidate. Previous version is V024 / `0_2_4`, which is the owner-confirmed passed baseline. V025 remains unaccepted until the owner explicitly promotes it.

V025 now combines the signal-policy and experiment layers:

- editable ranked scenarios with rank `1` highest;
- controller-metric and zone/class-count conditions;
- ALL/ANY multi-condition matching;
- one-winner eligible arbitration with explicit suppressed/unavailable reasons;
- bounded scenario actions with persistence, cooldown, protected phase targets and optional requested service;
- compatibility migration from older V023/V024 predefined rules into editable scenarios;
- live `zone_class_counts` observations separate from occupancy/flow semantics;
- isolated Fixed-vs-Adaptive Simulation Lab using the same selected profile, density, duration and seed;
- zone snapshot + synthetic zone/class counts in experiments so zone-based scenarios can be benchmarked;
- wait/queue/throughput/signal/scenario/diagnostic telemetry;
- bounded persisted experiment history and aligned CSV export;
- compact one-page Traffic Logic and Simulation Lab presentation using tabs, panels, dropdowns, toggles, pagination and internal scrolling.

## Inherited V024/V022/V021 layers

V024 provides atomic persistence hardening, synchronized zone/model-registry transitions, serial App-level polling, Windows update/test/run hardening, and the Material-derived PC Studio presentation system.

V022 provides cross-frame prototype tracking/counting-line flow. V021 provides sampled occupancy analytics. These remain distinct from V025 scenario observations and experiment telemetry.

## Next useful prototype directions after V025 acceptance

- **scenario import/export and reusable templates** so ranked scenario sets can be saved, shared, cloned and restored without editing JSON;
- **richer scenario condition sources** such as track-derived direction/entry/dwell events, only where semantics remain clear and deduplicated;
- **scenario diagnostics** showing activation frequency, time-as-winner, suppressed-by-higher-rank counts, cooldown suppression counts and zone-missing warnings across a session;
- model evaluation / dataset quality: validation precision, recall, mAP50, mAP50-95, per-class metrics, confusion matrix, false-positive/false-negative review, dataset class distribution and quality warnings;
- experiment/session reports with richer charts and scenario/policy snapshots;
- expand experiment demand generators beyond the current closed synthetic population, including explicit arrival-rate scenarios while preserving deterministic A/B inputs;
- stronger tracking/motion prediction and track-quality diagnostics;
- continue consolidating page-specific periodic polling where serial scheduling provides measurable benefit;
- pin/automate frontend dependency updates instead of indefinitely relying on broad `latest` declarations;
- optional compatible accessibility/incident perception research, clearly separated from manual Test inputs;
- device-camera workflow completion and model export/runtime packaging.

## Explicitly outside scope

Physical public-road traffic signal control remains outside the project. Detection, tracking, analytics, experiment results, scenario evaluation, timing changes, and phase outputs are prototype/simulation information only.
