# Patch 0_2_8 — pedestrian-aware cooperative two-intersection simulation

## Release state

- version: `0_2_8` / V028
- previous version: `0_2_7` / V027
- owner-confirmed passed baseline: `0_2_4` / V024
- status: candidate

## Preflight correction carried by this patch

Current GitHub `main` reported V027 and contained V027 models/tests/docs, but `app/services/network_simulation_experiments.py` was still the V026 independent-controller implementation. V028 therefore includes the complete intended V027 cooperative service as its base and then layers the V028 pedestrian-aware behavior on top. This avoids building on a documentation-only cooperation state.

## Implemented

### Four-mode deterministic network comparison

One network experiment now runs Fixed, Independent Adaptive, Cooperative Adaptive, and Pedestrian-aware Cooperative using the same seeded exogenous demand/topology/policy snapshot. The backward-compatible `comparison` remains Adaptive-vs-Fixed. New pairwise evidence isolates Pedestrian-aware Cooperative vs Cooperative.

### Pedestrian request/service lifecycle

Each simulated intersection tracks request start/fulfillment, request fulfillment time, service sessions, oldest/max observed wait, waiting queue pressure and crossing occupancy.

### Maximum-wait starvation prevention

When oldest waiting time reaches `pedestrian_max_wait_seconds`, the pedestrian-aware mode queues pedestrian service and may shorten only the current protected phase toward its configured minimum. It never skips protected phases or bypasses controller bounds.

### Synthetic crossing-clearance protection

Served pedestrians remain in synthetic crossing occupancy for `pedestrian_crossing_clearance_seconds`. While crossing occupancy is active during WALK/CLEAR, the guard may extend the current pedestrian phase to retain `pedestrian_clearance_reserve_seconds`, bounded by saved phase maximum and maximum-cycle limits.

### Cooperation interaction

V027 predicted-arrival cooperation remains active. V028 strengthens its pedestrian guard so either waiting demand or active synthetic crossing occupancy prevents cooperation from shortening WALK/CLEAR.

### Explainability / telemetry

Pedestrian-awareness events include ID/time/intersection/provenance, waiting count, oldest wait, crossing count, phase before action, action/reason, applied flag and timing delta. Network metrics summarize evaluations/applied actions, starvation prevention, clearance extensions, pedestrian wait/queue/max-wait and request/service evidence.

## Request additions

- `pedestrian_max_wait_seconds`: default 30, range 5–180;
- `pedestrian_crossing_clearance_seconds`: default 6, range 2–30;
- `pedestrian_clearance_reserve_seconds`: default 3, range 1–15.

No new stable error code is needed; existing traffic-rule validation is reused.

## Deliberately not implemented

- emergency-priority lifecycle/pre-emption;
- live cross-camera pedestrian identity;
- live wheelchair/mobility/fall recognition;
- calibrated pedestrian walking-speed/clearance model;
- general N-intersection orchestration;
- physical/public-road traffic control.

## Acceptance focus

Confirm the V027 cooperation behavior is present after applying V028, four modes share one demand fingerprint, maximum-wait service requests and crossing-clearance protection stay inside protected timing bounds, pedestrian-aware-vs-cooperative metrics/CSV are correct, and all inherited regressions still pass.
