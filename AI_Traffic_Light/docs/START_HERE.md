# Start Here — current V027 candidate

Read root `VERSION` first. V027 / `0_2_7` is the current unaccepted candidate by explicit owner request. V026 / `0_2_6` is the previous version. V024 / `0_2_4` remains the owner-confirmed passed baseline until the owner explicitly accepts a later candidate.

## What V027 adds

### Bounded cooperative two-intersection simulation

V027 extends the V026 deterministic two-intersection experiment from two modes to three:

1. **Fixed** — configured normal timing only.
2. **Independent Adaptive** — each intersection uses its own ranked local scenario controller with no neighbour timing influence.
3. **Cooperative Adaptive** — both intersections retain independent controller state, while downstream B may consume predicted synthetic A→B arrivals from the configured-link transfer pipeline.

All three modes receive the same seeded exogenous demand and the same configured source/destination/link snapshot.

### Cooperation behavior

For Cooperative Adaptive only:

- B examines synthetic transfers already discharged from A and scheduled to arrive within a configurable lookahead;
- when B is already in vehicle green, cooperation may extend that green only inside the saved phase maximum and maximum-cycle cap;
- when B is in another protected phase, cooperation may request earlier protected progression by reducing only the current phase toward its configured minimum;
- active local pedestrian demand prevents cooperation from shortening pedestrian WALK/CLEAR phases;
- phase order is never changed or skipped;
- cooperation decisions are recorded as structured events with incoming count, ETA, action, reason, and timing delta;
- coordination telemetry records evaluations, triggers, applied advisories, green extensions, progression requests, pedestrian-service protections, and timing seconds added/reduced.

This is **simulation-only cooperation**. It is not live multi-camera cooperation and is not public-road control.

## Comparison evidence

Each `netexp_*` result now contains:

- `fixed`;
- `adaptive`;
- `cooperative`;
- backward-compatible `comparison` for Adaptive vs Fixed;
- `comparisons.adaptive_vs_fixed`;
- `comparisons.cooperative_vs_fixed`;
- `comparisons.cooperative_vs_adaptive`.

The same seeded arrival-plan fingerprint remains available so the three modes can be audited against identical exogenous demand.

## Inherited capability

V027 retains V026 two-intersection transfer/persistence/CSV, V025 ranked scenarios, protected signal timing, single-junction Simulation Lab, intersection/topology identity, decision context/provenance, V024 persistence/polling hardening, V022 flow tracking, V021 occupancy, and the existing dataset/training/inference/model workflow.

## Important interpretation rules

- Cooperation is driven by **synthetic predicted arrivals** from the experiment transfer pipeline, not live camera tracking across intersections.
- Configured link travel time is a simulation input, not a learned or measured road travel time.
- Cooperative mode may improve or worsen a metric depending on the selected simulated demand/configuration; no universal superiority claim is valid.
- Emergency priority remains inactive.
- Existing PC Studio Simulation Lab remains the single-junction GUI; V027 network/cooperation experiments remain backend/API/test-first.

## Recommended next step

After V027 acceptance, the next logical feature is stronger **pedestrian-aware service evidence** or simulated **emergency priority** built on the same network/explanation architecture. Do not create a separate controller.

## Safety boundary

AiTL remains a supervised local simulation/computer-vision prototype. V027 cooperation, transfers, queues, timings, and comparison metrics are synthetic experiment evidence only and are not connected to physical/public-road signal infrastructure.
