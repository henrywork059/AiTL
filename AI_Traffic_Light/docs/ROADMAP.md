# Roadmap

Root `VERSION` defines the active candidate. This roadmap records dependency order, not acceptance state.

## 0_2_8 — Pedestrian-aware cooperative network candidate

V028 adds explicit pedestrian-service evidence to the bounded two-intersection cooperation benchmark:

- request age and request start/fulfillment lifecycle;
- service-session and fulfillment-time evidence;
- maximum-wait starvation prevention;
- synthetic crossing occupancy after service;
- bounded WALK/CLEAR clearance reserve;
- interaction guard so neighbour cooperation cannot shorten pedestrian WALK/CLEAR during waiting or crossing demand;
- Pedestrian-aware Cooperative vs Cooperative comparison under the same seeded exogenous demand.

The patch also repairs the V027 GitHub-main mismatch by carrying the complete intended cooperative service forward.

## Priority 1 — simulated emergency priority

Add a simulation/configured emergency event lifecycle on the existing network/explanation architecture:

- event/vehicle ID and type;
- source intersection and approach/direction;
- timestamp and explicit provenance;
- active/cleared lifecycle;
- protected priority request, grant/deny explanation and recovery;
- downstream preparation over configured links;
- emergency delay/recovery telemetry;
- no claim of live emergency recognition unless a compatible detector/source actually exists.

## Priority 2 — broader vehicle-class behavior

Build on retained detector class names and synthetic car/bus transfer:

- explicit class taxonomy with `unknown/other` fallback;
- additional synthetic classes where useful;
- optional configured class weighting/priority with clear rationale;
- class-aware metrics and provenance;
- no conflation of synthetic class generation with AI detections.

## Priority 3 — generalize network orchestration

After the two-intersection evidence is stable:

- support multiple simultaneous directed links/intersections;
- richer arrival prediction and travel-time uncertainty;
- network/corridor objectives alongside local objectives;
- compact PC Studio network experiment UI;
- live multi-source retention/tracking only as a separate prototype step.

## Cross-cutting — explainability

Every adaptive/cooperative/pedestrian/emergency feature should improve the same evidence model:

- decision/event ID;
- intersection ID;
- trigger category;
- local observations;
- neighbour/predicted-arrival context;
- pedestrian/emergency context;
- action and timing before/after;
- provenance and concise explanation.

## Explicitly outside scope

Physical/public-road signal control, traffic-cabinet integration, bypassing safety systems, production autonomous authority, and safety certification remain outside this project.
