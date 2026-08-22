# Patch 0_3_0 — vehicle-class-aware cooperative network simulation

## Release state

- version: `0_3_0` / V030
- previous version: `0_2_9` / V029
- owner-confirmed passed baseline remains: `0_2_4` / V024
- status: candidate

The owner explicitly requested V030 before separately accepting V029. Automated validation does not promote the passed baseline.

## Purpose

V029 established a matched synthetic emergency-priority comparison on top of cooperation and pedestrian-aware control. V030 adds the next planned invention capability: explicit regular vehicle classes, class-rich deterministic demand, class-specific evidence, and one bounded class-aware cooperative policy layer.

## Implemented

### Explicit taxonomy and provenance

Regular synthetic vehicle classes are now:

- `car`;
- `bus`;
- `truck`;
- `motorcycle`;
- `bicycle`;
- `other`.

`emergency` remains a separate special V029 simulator class. Unknown/unmapped regular labels normalize to `other`.

All generated regular class labels use `synthetic_vehicle_class_demand` provenance. They are not presented as camera/model classifications.

### Deterministic class profiles

`vehicle_class_profile` selects one deterministic mix:

- `legacy` — V029-compatible car/bus mix;
- `mixed_urban` — car/bus/truck/motorcycle/bicycle/other;
- `freight_heavy` — higher synthetic truck share.

Every comparison mode in one run receives the same seeded exogenous class-rich arrival plan and fingerprint.

### Seventh comparison mode

The network experiment now contains:

1. Fixed;
2. Independent Adaptive;
3. Cooperative Adaptive;
4. Pedestrian-aware Cooperative;
5. Class-aware Cooperative;
6. Emergency Baseline Cooperative;
7. Emergency-priority Cooperative.

Class-aware Cooperative inherits cooperation and pedestrian-awareness behavior and adds only the configured regular-class advisory. This isolates class-aware effects from the V028 pedestrian-aware baseline.

### Bounded class-aware timing

The class-aware layer is explicitly configurable:

- enable/disable;
- selected regular class;
- priority weight;
- minimum waiting count;
- maximum vehicle-green extension.

A weight of `1.0` is neutral and does not alter timing. A weight above `1.0` may:

- extend current vehicle green inside the saved phase maximum, maximum-cycle cap, and class-extension cap;
- request earlier protected vehicle service by shortening only the current protected phase toward its configured minimum.

It never skips phase order. Active pedestrian WALK/CLEAR with local waiting/crossing demand is protected from class-priority shortening.

### Class-specific telemetry

Each intersection and the network aggregate now record per-class:

- external arrivals;
- transfer arrivals;
- vehicles served;
- wait distribution;
- sampled queue average / p95 / peak.

Arrival-plan metadata records source/destination and transfer-candidate class counts.

### Explainability / comparison evidence

Class-priority events record:

- deterministic event ID;
- time and source/destination role;
- intersection;
- configured class;
- waiting count and oldest wait;
- priority weight and weighted waiting;
- phase before advisory;
- action / applied flag / timing delta;
- reason;
- `synthetic_vehicle_class_demand` provenance.

`comparisons.class_aware_cooperative_vs_pedestrian_aware_cooperative` isolates the V030 policy layer and includes a `selected_class` subcomparison for served count, average/p95 wait, and queue average.

### CSV

The network CSV now includes all seven modes and class-priority source/destination action, class, waiting count, weighted waiting, and applied fields.

## API request additions

`POST /api/traffic/network-experiments` adds:

- `vehicle_class_profile` — `legacy | mixed_urban | freight_heavy`;
- `vehicle_class_priority_enabled` — default `true`;
- `vehicle_class_priority_class` — `car | bus | truck | motorcycle | bicycle | other`, default `bus`;
- `vehicle_class_priority_weight` — default `2.0`, range `1.0–5.0`;
- `vehicle_class_priority_min_waiting` — default `1`, range `1–20`;
- `vehicle_class_priority_max_extension_seconds` — default `4.0`, range `0–20`.

No new stable error code is required; existing traffic-rule validation is reused.

## Preserved behavior

- V029 matched simulated emergency-event baseline and emergency-priority lifecycle;
- V028 pedestrian request-age / crossing-clearance protection;
- V027 bounded neighbour-informed cooperation;
- V026 deterministic A→B transfer and separate per-intersection controllers;
- V025 ranked local scenario arbitration;
- existing persistence/list/get/delete/CSV conventions;
- live camera/controller runtime isolation.

## Deliberately not implemented

- live camera-based vehicle-class accuracy claims for these synthetic experiments;
- automatic priority for a class merely because a detector emitted that label;
- lane-specific public-transit signal priority;
- real freight/transit schedules;
- general N-intersection class-aware orchestration;
- physical/public-road signal control.

## Acceptance focus

The owner should confirm:

1. the seven modes share one seeded class-rich exogenous arrival fingerprint;
2. `mixed_urban`/`freight_heavy` produce only the documented regular taxonomy;
3. unknown labels normalize to `other` in the service helper;
4. class-specific demand/service/wait/queue metrics are present;
5. Class-aware Cooperative contains structured class-priority events with synthetic provenance;
6. configured weight `1.0` causes no class timing change;
7. disabling class priority leaves Class-aware network metrics equal to Pedestrian-aware Cooperative under the same run;
8. class priority stays inside protected timing bounds and protects active pedestrian WALK/CLEAR demand;
9. V027/V028/V029 focused regressions remain green;
10. no synthetic class evidence is described as live AI detection or public-road authority.
