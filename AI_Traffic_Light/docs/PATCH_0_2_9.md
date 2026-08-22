# Patch 0_2_9 — simulated emergency-priority cooperative network benchmark

## Release state

- version: `0_2_9` / V029
- previous version: `0_2_8` / V028
- owner-confirmed passed baseline remains: `0_2_4` / V024
- status: candidate

The owner explicitly requested V029 before separately accepting V028. Automated validation does not promote the passed baseline.

## Purpose

V028 strengthened pedestrian-aware cooperative control in the deterministic two-intersection simulator. V029 adds the next planned invention capability: a **simulated/configured emergency-priority lifecycle** with a matched no-priority emergency baseline, protected grant/deny behavior, downstream preparation, recovery, and explicit evidence.

## Six-mode comparison

Each network experiment now runs:

1. Fixed;
2. Independent Adaptive;
3. Cooperative Adaptive;
4. Pedestrian-aware Cooperative;
5. Emergency Baseline Cooperative;
6. Emergency-priority Cooperative.

The first four preserve V028 behavior. The final two receive the same seeded exogenous demand and the same synthetic emergency event/vehicle. Only the sixth mode enables emergency timing priority. This isolates policy effect from the presence of the emergency vehicle itself.

## Emergency event model

The configured event includes:

- event ID;
- event type;
- emergency vehicle ID;
- vehicle type: ambulance / fire engine / police;
- generic simulator class `emergency`;
- activation time;
- source intersection/approach;
- destination intersection/approach;
- link ID;
- explicit `simulated_configured_emergency_event` provenance;
- `confidence: null`;
- `detector_claimed: false`.

Lifecycle records include activation, source departure, downstream arrival, clear, and recovery when the event completes within the run.

## Bounded priority behavior

The emergency-priority mode may:

- extend current vehicle green only within saved phase maximum, maximum-cycle cap, and `emergency_priority_max_extension_seconds`;
- request earlier vehicle service by reducing only the current phase toward its configured minimum;
- prepare the downstream controller when the in-transit emergency vehicle is within `emergency_priority_lookahead_seconds`.

It never skips the protected phase order. An active simulated pedestrian crossing explicitly denies an emergency timing adjustment until the crossing clears.

## Explainability and telemetry

Emergency priority events record:

- priority-event ID and emergency-event ID;
- simulation time;
- role: source priority / downstream preparation / destination priority;
- intersection and link;
- vehicle type;
- provenance;
- phase before advisory;
- ETA;
- grant / deny / defer decision;
- action;
- applied flag;
- reason;
- timing delta.

Network emergency metrics include:

- event status/completion;
- source wait;
- destination wait;
- end-to-end emergency travel time;
- priority evaluation/grant/denial counts;
- downstream preparation count;
- timing actions/seconds added or reduced.

`comparisons.emergency_priority_vs_emergency_baseline` provides the matched policy comparison and reports unavailable emergency-delay deltas if the event does not complete in both runs.

## API request additions

`POST /api/traffic/network-experiments` additionally accepts:

- `emergency_event_enabled` — default `true`;
- `emergency_event_at_seconds` — default `15`, must fall within the run;
- `emergency_vehicle_type` — `ambulance | fire_engine | police`;
- `emergency_priority_lookahead_seconds` — default `20`, range 1–120;
- `emergency_priority_max_extension_seconds` — default `8`, range 0–30.

Existing traffic-rule validation is reused; no new stable error code is required.

## CSV

The aligned network CSV now includes all six modes and adds emergency status, role, decision, action, ETA, and applied fields.

## Preserved behavior

- V028 pedestrian-aware request/clearance layer;
- V027 bounded cooperation;
- V026 deterministic transfer and independent per-intersection controllers;
- V025 ranked scenarios and single-junction Simulation Lab;
- protected phase order/minimums/maxima/cycle caps;
- persistence/list/get/delete and request-ID/API-envelope conventions;
- live camera/controller runtime isolation;
- data provenance and prototype-only scope.

## Deliberately not implemented

- AI/camera emergency recognition;
- confidence scoring from a detector;
- live cross-camera emergency identity matching;
- hardware traffic-signal pre-emption;
- public-road/cabinet integration;
- bypass of protected timing/safety interlocks;
- general N-intersection emergency route orchestration;
- safety certification.

## Acceptance focus

Confirm that:

1. `VERSION` reports V029 with V024 still the passed baseline;
2. all six modes exist and the first four retain V028 behavior;
3. the two emergency modes contain the identical configured emergency event;
4. the emergency baseline has no emergency timing priority;
5. the priority mode records grant/deny/defer evidence and downstream preparation;
6. active simulated pedestrian crossings deny emergency timing changes;
7. all applied changes remain inside phase/cycle bounds and phase order is unchanged;
8. lifecycle evidence records activation/departure/arrival/clear/recovery for a sufficiently long run;
9. the matched emergency comparison and six-mode CSV are present;
10. persistence, repeatability, inherited regressions and frontend/backend checks pass;
11. no live emergency-detection or public-road-control claim is introduced.
