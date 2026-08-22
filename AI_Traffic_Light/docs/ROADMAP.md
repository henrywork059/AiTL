# Roadmap

Root `VERSION` defines the active candidate. This roadmap records dependency order, not acceptance state.

## 0_2_9 — simulated emergency-priority cooperative network candidate

V029 adds the first simulation-only emergency-priority evidence layer on top of V028:

- explicit configured emergency event/vehicle identity and type;
- matched no-priority emergency baseline and emergency-priority mode;
- activation → source departure → downstream arrival → clear/recovery lifecycle;
- bounded source priority, downstream preparation and destination priority;
- protected grant/deny/defer explanations;
- active pedestrian crossing denial guard;
- emergency wait/travel and timing telemetry;
- matched Emergency-priority-vs-Emergency-baseline comparison;
- no claim of live emergency recognition.

## Priority 1 — broader vehicle-class behavior

Build on retained detector class names, synthetic car/bus demand, and the explicit V029 emergency class:

- explicit supported class taxonomy with `unknown/other` fallback;
- additional synthetic motorcycle/bicycle/truck/bus classes where useful;
- configurable class weighting/priority with a clear rationale and bounded action;
- class-specific demand and service metrics;
- explicit provenance so synthetic class generation is never presented as AI detection;
- tests showing class-aware behavior changes only when configured.

## Priority 2 — persistent explainability/evidence

Consolidate scenario, cooperation, pedestrian and emergency evidence into a stable persistent decision/event record that can reconstruct:

- decision/event ID;
- intersection ID;
- trigger category;
- local observations;
- neighbour/predicted-arrival context;
- pedestrian/emergency/class context;
- action and timing before/after;
- grant/deny/suppression reason;
- provenance and concise explanation.

## Priority 3 — generalize network orchestration

After the selected two-intersection evidence is stable:

- support multiple simultaneous directed links/intersections;
- richer arrival prediction and travel-time uncertainty;
- network/corridor objectives alongside local objectives;
- multi-link emergency route context;
- compact PC Studio network experiment UI;
- live multi-source retention/tracking only as a separate prototype step.

## Later live-evidence work

Only after a compatible perception source exists should the project explore live emergency recognition or more reliable class/pedestrian identity. Any such source must expose explicit provenance/confidence and be evaluated separately from the deterministic simulation evidence.

## Explicitly outside scope

Physical/public-road signal control, traffic-cabinet/pre-emption integration, bypassing safety systems, production autonomous authority, and safety certification remain outside this project.
