# Roadmap

This roadmap defines dependency order and evidence goals. Root `VERSION` defines the active candidate; `PROJECT_SCOPE.md` defines capability-status wording.

## Current foundation

The current V025 work combines:

- ranked simulated signal scenarios and deterministic one-winner arbitration;
- isolated Fixed-vs-Adaptive Simulation Lab telemetry;
- camera-aligned zones, occupancy, prototype tracking/flow;
- dataset/training/inference/model workflow;
- generic intersection/source identity and directed neighbour-link configuration;
- structured live decision/explanation context.

Configured topology is foundation only: cooperation/emergency priority remain inactive.

## Priority 1 — deterministic multi-intersection simulation

Goal: make intersection identity real in the simulator before adding cooperation.

Minimum scope:

- at least two simultaneous synthetic intersections;
- per-intersection zones/traffic state/controller runtime;
- deterministic links/travel time;
- explicit vehicle/demand transfer or arrival events A → B;
- per-intersection and network aggregate telemetry;
- seeded repeatability tests;
- no hard-coded assumption that the architecture can only ever contain two intersections.

Evidence gate: demonstrate that transferred arrivals at B correspond to departures/links from A under the same deterministic run.

## Priority 2 — bounded multi-intersection cooperation

Goal: neighbour-informed simulated timing while preserving each intersection's protected local controller.

Minimum scope:

- predicted incoming demand/arrival context from links;
- neighbour context as an explicit condition/input, not hidden global state;
- bounded cooperation scenario/action integrated with the ranked scenario engine;
- decision history records the neighbour evidence used;
- comparison modes: Fixed vs Independent Adaptive vs Cooperative Adaptive;
- network metrics such as total/percentile delay, queues, throughput/service, stops or transfer completion where semantics are valid.

Evidence gate: same seeded demand produces a deterministic decision difference attributable to neighbour context and measurable network-level outcome differences.

## Priority 3 — pedestrian service quality

Strengthen the existing pedestrian-aware controller with:

- explicit service request lifecycle;
- longest individual wait where tracking supports it;
- missed-service/starvation prevention;
- service frequency;
- crossing-clearance evidence;
- interaction with network cooperation;
- pedestrian-specific experiment summaries.

Do not call per-frame person counts unique throughput.

## Priority 4 — simulated emergency priority

Begin with explicit simulated/configured emergency events, not an unsupported perception claim.

Minimum scope:

- event ID/type/source/approach/time/provenance/lifecycle;
- bounded priority request through protected transitions;
- grant/deny reason;
- downstream preparation over configured path/link context;
- recovery to normal operation;
- event/decision timing metrics and structured explanation.

Only add real emergency perception later if a compatible detector/source is separately implemented and evaluated.

## Priority 5 — broader vehicle-class behavior

Build on existing class retention/zone-class scenarios:

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

- model/dataset quality metrics (precision, recall, mAP, class distribution, confusion/error review);
- scenario diagnostics (activation/winner/suppression/cooldown/unavailable counts);
- experiment/session reports with policy/config snapshots;
- stronger tracking/motion prediction diagnostics;
- scenario import/export/templates;
- exogenous arrival-rate demand generators;
- device-camera workflow completion where useful to the model demonstration.

## Explicitly outside scope

Physical/public-road traffic control, cabinet integration, safety-interlock bypass, and production autonomous signal authority remain outside AiTL. Simulation results are not public-road safety certification evidence.
