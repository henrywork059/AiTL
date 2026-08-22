# Patch 0_2_7 — bounded cooperative two-intersection simulation

## Release state

- version: `0_2_7` / V027
- previous version: `0_2_6` / V026
- owner-confirmed passed baseline remains: `0_2_4` / V024
- status: candidate

The owner explicitly requested V027 before separately accepting V026. Automated validation does not promote the passed baseline.

## Purpose

V026 established a deterministic two-intersection **independent-control** benchmark with explicit synthetic A→B transfer. V027 adds the next dependency: bounded neighbour-informed cooperation while preserving separate per-intersection controllers and the protected local phase architecture.

## Implemented

### Three-mode network comparison

One `network-experiments` request now runs:

1. Fixed;
2. Independent Adaptive;
3. Cooperative Adaptive.

All three receive the same seeded exogenous demand and the same topology/policy/zone snapshot.

### Predicted-arrival cooperation

Cooperative mode uses only synthetic transfers already discharged from the upstream intersection and scheduled in the configured link pipeline. For transfers inside the configured lookahead, downstream B receives:

- predicted incoming vehicle count;
- earliest arrival ETA;
- source/destination/link identity;
- explicit simulation provenance.

### Bounded timing actions

The simulation-only coordinator may:

- extend downstream vehicle green so predicted arrivals can be served, but only within the saved phase maximum, maximum-cycle cap, and the configured cooperation extension cap;
- request earlier protected progression toward vehicle service by shortening only the current phase toward its configured minimum;
- preserve pedestrian WALK/CLEAR when local pedestrians are waiting rather than shortening that phase.

It never changes the protected phase sequence and does not create a second signal controller.

### Explainability / evidence

Cooperative results record structured coordination events containing:

- deterministic coordination ID;
- simulation time;
- link/source/destination intersection identity;
- provenance;
- destination phase before the advisory;
- predicted incoming count;
- earliest ETA;
- action;
- applied flag;
- reason;
- timing delta.

Network coordination telemetry includes evaluation/trigger/application counts, green extensions, protected progression requests, pedestrian-service protections, and timing seconds added/reduced.

### Pairwise comparison

The existing `comparison` field remains backward-compatible Adaptive-vs-Fixed data. V027 adds:

- `comparisons.adaptive_vs_fixed`;
- `comparisons.cooperative_vs_fixed`;
- `comparisons.cooperative_vs_adaptive`.

### CSV

Network CSV now aligns Fixed, Adaptive and Cooperative timeline columns and includes cooperation action/incoming/ETA/applied fields.

## API request additions

`POST /api/traffic/network-experiments` adds:

- `cooperation_lookahead_seconds` — default `12.0`, range 1-60;
- `cooperation_max_extension_seconds` — default `5.0`, range 0-20;
- `cooperation_min_incoming_vehicles` — default `1`, range 1-20.

No new stable error code is required; existing traffic-rule validation and network validation paths are reused.

## Preserved behavior

- V026 deterministic transfer/persistence/list/get/delete semantics;
- V025 ranked local scenario arbitration;
- protected phase min/max/cycle bounds;
- single-junction Simulation Lab and `exp_*` endpoints;
- live traffic/controller runtime isolation;
- V024 persistence/polling hardening;
- occupancy/flow separation;
- camera/dataset/training/inference/model workflows.

## Deliberately not implemented

- emergency priority/pre-emption;
- live cross-camera identity matching;
- measured/learned travel-time prediction;
- general N-intersection cooperative orchestration;
- dedicated network experiment frontend/dashboard;
- physical/public-road signal control.

## Acceptance focus

The owner should confirm:

1. three modes use one deterministic exogenous demand fingerprint;
2. Cooperative mode produces neighbour-informed advisory evidence;
3. cooperation changes timing only within protected bounds;
4. pedestrian WALK/CLEAR is not shortened when local pedestrian demand is active;
5. transfer travel time remains deterministic;
6. pairwise comparisons and three-mode CSV are correct;
7. repeatability/persistence/delete remain intact;
8. inherited regression passes;
9. no live/public-road control claim or connection is introduced.

See `LOCAL_TESTING.md` and `TEST_READY_CHECKLIST.md` for exact commands/checks.
