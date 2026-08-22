# Roadmap

This roadmap defines dependency order and evidence goals. Root `VERSION` defines the active candidate; `PROJECT_SCOPE.md` defines capability-status wording.

## Current V026 foundation

V026 combines:

- ranked simulated signal scenarios and deterministic one-winner arbitration;
- isolated single-junction Fixed-vs-Adaptive Simulation Lab telemetry;
- generic intersection/source identity and directed neighbour-link configuration;
- structured live decision/explanation context;
- deterministic **two-intersection** independent-control network experiments;
- separate controller runtime per simulated intersection;
- synthetic configured-link vehicle transfer A → B;
- per-transfer departure/scheduled-arrival/arrival evidence;
- per-intersection and network aggregate telemetry;
- persistent network experiment JSON and CSV export.

V026 still reports `cooperative_control_active: false`. It is the baseline against which later cooperation should be measured.

## Priority 1 — bounded multi-intersection cooperation

Goal: neighbour-informed simulated timing while preserving each intersection's protected local controller.

Minimum scope:

- expose predicted/scheduled incoming demand from the V026 transfer pipeline;
- make neighbour context an explicit controller/scenario condition/input, not hidden global state;
- integrate bounded cooperation with the ranked scenario engine;
- preserve protected phase order/min/max/cycle constraints;
- decision evidence records the neighbour values that affected arbitration;
- comparison modes: Fixed vs Independent Adaptive vs Cooperative Adaptive;
- network metrics such as total/percentile delay, queues, throughput/service, transfer completion and corridor travel where semantics are valid.

Evidence gate: same seeded demand must produce a deterministic decision difference attributable to neighbour context and a measurable network-level outcome difference.

## Priority 2 — pedestrian service quality

Strengthen the existing pedestrian-aware controller with:

- explicit service request lifecycle;
- longest individual wait where tracking supports it;
- missed-service/starvation prevention;
- service frequency;
- crossing-clearance evidence;
- interaction with network cooperation;
- pedestrian-specific experiment summaries.

Do not call per-frame person counts unique throughput.

## Priority 3 — simulated emergency priority

Begin with explicit simulated/configured emergency events, not an unsupported perception claim.

Minimum scope:

- event ID/type/source/approach/time/provenance/lifecycle;
- bounded priority request through protected transitions;
- grant/deny reason;
- downstream preparation over configured path/link context;
- recovery to normal operation;
- event/decision timing metrics and structured explanation.

Only add real emergency perception later if a compatible detector/source is separately implemented and evaluated.

## Priority 4 — broader vehicle-class behavior

Build on existing class retention/zone-class scenarios and V026 synthetic car/bus transfer evidence:

- explicit class taxonomy/fallback;
- additional synthetic classes where useful;
- class-aware scenario metrics/weighting only when clearly configured;
- class/provenance visibility in experiments/explanations;
- per-class evaluation where it helps demonstrate behavior.

## Cross-cutting — explainable decisions

Every future adaptive/cooperative/emergency feature should improve the same explanation model rather than add ad-hoc strings.

Target persistent decision evidence includes decision/intersection IDs, trigger category, winning scenario, observed values, neighbour/pedestrian/emergency context, resulting simulated phase/action, before/after timing, provenance, and readable explanation.

## Evidence/reporting improvements

After core behavior is stable:

- PC Studio network-experiment UI integrated into the existing grouped Simulation Lab presentation;
- model/dataset quality metrics (precision, recall, mAP, class distribution, confusion/error review);
- scenario diagnostics (activation/winner/suppression/cooldown/unavailable counts);
- experiment/session reports with policy/config/topology snapshots;
- stronger tracking/motion prediction diagnostics;
- scenario import/export/templates;
- richer exogenous arrival-rate demand generators;
- device-camera workflow completion where useful to the model demonstration.

## Explicitly outside scope

Physical/public-road traffic control, cabinet integration, safety-interlock bypass, and production autonomous signal authority remain outside AiTL. Simulation results are not public-road safety certification evidence.
