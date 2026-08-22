# Roadmap

Root `VERSION` defines the active candidate. This roadmap records dependency order, not acceptance state.

## Current V027 capability

V027 provides the first bounded **simulation-only multi-intersection cooperation** evidence:

- deterministic two-intersection source→destination network experiment;
- separate controller runtime per intersection;
- explicit synthetic transfer pipeline and configured travel time;
- Fixed, Independent Adaptive, and Cooperative Adaptive modes on the same seeded demand;
- downstream predicted-arrival lookahead;
- bounded green extension and protected progression requests;
- pedestrian-service guard during WALK/CLEAR when local pedestrians are waiting;
- structured coordination events and network telemetry;
- pairwise network comparisons and persistent CSV/JSON results.

This is not yet a general live N-intersection cooperative controller. The generic topology schema remains N-intersection capable, while the V027 experiment deliberately selects one directed pair for controlled evidence.

## Priority 1 — strengthen pedestrian-aware control

Build on existing waiting/crossing zones, protected phases, dwell/wait metrics, ranked scenarios, and V027 cooperation:

- explicit service-request lifecycle;
- longest individual waiting evidence where tracking quality supports it;
- missed-service/starvation prevention;
- service frequency and clearance evidence;
- interaction with cooperation without silently sacrificing pedestrian service.

## Priority 2 — simulated emergency priority

Add an explicit simulated/configured emergency event lifecycle:

- event/vehicle ID, type, source intersection, approach/direction, timestamp and provenance;
- priority request, grant/deny explanation, protected transition path and recovery;
- downstream preparation over configured links;
- emergency-specific delay/recovery telemetry;
- no claim of live emergency recognition unless a compatible detector is added.

## Priority 3 — broaden vehicle-class behavior

Build on retained detector class names and synthetic car/bus network transfer:

- explicit class taxonomy including `unknown/other`;
- additional synthetic classes where useful;
- optional configured class weighting/priority with clear rationale;
- class-aware metrics and provenance.

## Cross-cutting — explainable decisions

Every adaptive/cooperative/emergency feature should improve the same explanation model:

- decision/event ID;
- intersection ID;
- trigger category;
- local observations;
- neighbour/predicted-arrival context;
- pedestrian/emergency context;
- action and timing before/after;
- provenance and readable explanation.

## Later network work

After the two-intersection evidence is stable:

- generalize experiment orchestration to more than one directed link;
- compare corridor/network objectives against local objectives;
- add richer arrival prediction and travel-time uncertainty;
- expose network experiments in a compact PC Studio page without creating a long dashboard;
- investigate live multi-source retention/tracking only as a separate prototype step.

## Explicitly outside scope

Physical/public-road signal control, traffic-cabinet integration, bypassing safety systems, production autonomous authority, and safety certification remain outside this project.
