# Project Scope and Capability Status

This document records what AiTL is intended to demonstrate and how capability claims should be worded. It is a scope/evidence guide, not a release-state source; read root `VERSION` for the active candidate.

## 1. Scope vocabulary

Use these labels consistently:

- **Implemented** — an active code path exists and is testable.
- **Foundation** — supporting identity/schema/service/context exists, but the target behavior is not active.
- **Simulation-only** — implemented only in local synthetic/test behavior.
- **Planned** — intended invention capability, not yet implemented sufficiently to claim operation.
- **Out of scope** — deliberately excluded from this project.

Do not upgrade a label because a UI field, config schema, or placeholder exists.

## 2. Current implemented capability families

AiTL currently includes local prototype capability in these families:

- camera-frame receiver and signal-aware synthetic scene;
- local trained-model inference;
- camera-aligned polygon zones and counting lines;
- sampled occupancy and lightweight track-derived flow analytics;
- dataset capture/review/manual labeling and managed YOLO training workflow;
- configurable protected simulated signal timing;
- ranked adaptive signal scenarios with deterministic one-winner arbitration;
- isolated seeded Fixed-vs-Adaptive Simulation Lab telemetry;
- persistent experiment/config/history tooling;
- generic intersection/topology foundation and source-to-intersection identity;
- deterministic two-intersection network simulation with synthetic configured-link vehicle transfer and bounded cooperation;
- simulation-only pedestrian request/clearance protection;
- simulation-only matched emergency-event baseline and bounded emergency priority with downstream preparation/recovery evidence;
- simulation-only explicit regular vehicle-class taxonomy, class-rich demand, per-class telemetry, and bounded configured class-aware cooperative timing;
- structured live decision/explanation **foundation**.

Exact candidate details belong in `START_HERE.md` and the current patch document.

## 3. Planned invention capability: multi-intersection cooperation

**Status: bounded two-intersection cooperation implemented in isolated simulation; broader/live cooperation remains planned.**

V027 now satisfies the minimum evidence for a simulation-only cooperation claim:

- two intersections are modeled simultaneously;
- each has separate controller/runtime state;
- explicit synthetic A→B transfers create predicted downstream arrival context;
- Cooperative Adaptive timing can change because of neighbour arrival context;
- timing changes remain bounded by protected phase minimum/maximum/cycle rules;
- active pedestrian service is protected from cooperation-driven shortening;
- coordination events record incoming count, ETA, action, reason and timing delta;
- the same seeded demand is compared across Fixed, Independent Adaptive and Cooperative Adaptive modes.

The claim must remain qualified as **isolated synthetic two-intersection cooperation**. It does not establish live multi-camera cooperation, measured road travel-time prediction, general N-intersection coordination, public-road performance, or safety.

Future strengthening includes multiple simultaneous links/intersections, richer arrival prediction, uncertainty handling, network objectives, and a compact PC Studio network experiment surface.

## 4. Planned invention capability: emergency priority

**Status: implemented in matched synthetic network experiment / planned live-evidence enhancement.**

V029 implements the initial evidence-gated form that this scope required: an explicit simulated/configured emergency vehicle event, not inferred perception. Two matched emergency modes receive the same event so priority behavior can be compared against a no-priority baseline.

Current V029 event/evidence includes:

- deterministic emergency event and vehicle IDs;
- ambulance / fire-engine / police configured type;
- source/destination intersection and approach plus selected link;
- activation time and explicit simulation provenance;
- `confidence: null` and `detector_claimed: false`;
- activation, source-departure, downstream-arrival, clear and recovery lifecycle events;
- protected grant/deny/defer decisions and reasons;
- downstream preparation while the emergency vehicle is in the synthetic transfer pipeline;
- emergency source/destination wait and end-to-end travel evidence.

Priority may extend vehicle green or request earlier protected progression only inside existing phase minimum/maximum/cycle bounds. Active simulated pedestrian crossings block emergency timing changes until clearance.

The claim must remain **simulation-only emergency priority**. V029 does not establish emergency recognition from a camera/model, live cross-camera emergency identity, hardware pre-emption, general emergency route orchestration, public-road performance, or safety. A detector class name or manual flag alone remains insufficient to claim live emergency priority.

Future strengthening should focus on compatible perception provenance, confidence/uncertainty when an actual detector exists, multi-link route context, and compact evidence presentation—not on relabeling the current configured event as AI recognition.

## 5. Planned invention capability: pedestrian-aware control

**Status: implemented in synthetic network experiment / planned live-evidence enhancement.**

Existing foundations include pedestrian waiting/crossing zones, counts, dwell/wait-related metrics, pedestrian-priority scenarios/profiles, protected WALK/CLEAR phases, and pedestrian simulation telemetry.

V028 adds synthetic network evidence for oldest-wait tracking, request start/fulfillment lifecycle, service sessions, maximum-wait starvation prevention, simulated crossing occupancy, and bounded crossing-clearance reserve. These are simulation inputs/evidence; they are not live unique-pedestrian measurements.

Future strengthening should focus on live-evidence quality rather than re-implementing the V028 simulator layer:

- longest individual live waiting time only where tracking quality supports it;
- robust live service-request reconstruction across camera/source changes;
- calibrated crossing-clearance evidence rather than a fixed synthetic duration;
- interaction with the V029 simulated emergency-priority lifecycle and any later live-evidence source;
- compact frontend presentation of pedestrian-specific evidence.

Per-frame person counts must not be described as unique pedestrian throughput.

## 6. Planned invention capability: different vehicle classes

**Status: implemented in synthetic network experiment / planned live-evidence enhancement.**

V030 adds the first explicit class-aware evidence layer required by this capability. Regular simulator taxonomy is `car`, `bus`, `truck`, `motorcycle`, `bicycle`, `other`; V029 `emergency` remains a separate special simulator class. Unknown/unmapped regular labels fall back to `other`.

Current V030 evidence includes:

- deterministic `legacy`, `mixed_urban`, and `freight_heavy` synthetic class profiles;
- identical seeded class-rich exogenous demand for every comparison mode in a run;
- per-intersection and network class arrivals, transfers, served counts, wait distributions, and sampled queue metrics;
- one optional Class-aware Cooperative policy layer with configured class, weight, minimum waiting count, and extension cap;
- neutral weight `1.0` produces no class timing action;
- configured weight above `1.0` may reserve bounded vehicle service without changing phase order;
- active pedestrian WALK/CLEAR demand prevents class-priority shortening;
- structured class-priority events and `synthetic_vehicle_class_demand` provenance;
- matched `class_aware_cooperative` vs `pedestrian_aware_cooperative` comparison, including selected-class served/wait/queue evidence.

The claim must remain **simulation-only class-aware control/evidence**. V030 does not establish camera class accuracy, unique vehicle identity across cameras, public-transit signal priority, freight schedule integration, lane-level authority, or public-road benefit. A detector class label alone is not permission to invoke the synthetic priority policy.

Future strengthening should focus on compatible live class provenance/confidence, calibrated class-specific service objectives, multiple links/intersections, and evidence that any class weighting is justified rather than arbitrary.

## 7. Planned invention capability: explainable decisions

**Status: partial implementation / foundation.**

Current scenario status/history already exposes winner/suppression reasons and observed values, and the network-foundation update adds structured live decision context.

Target structured explanation should support:

- decision ID and timestamp;
- intersection ID;
- trigger category;
- winning scenario/rule;
- relevant observed values;
- neighbour context;
- pedestrian context;
- emergency context;
- resulting simulated phase/action;
- timing before/after;
- concise human-readable explanation;
- provenance sufficient to distinguish AI, simulation, and manual inputs.

Before claiming persistent explainability/evidence, decision records should be stored in a stable history format that can reconstruct why a simulated action occurred.

## 8. Evidence hierarchy

Prefer evidence in this order:

1. deterministic service/unit regression;
2. API integration test;
3. seeded simulator comparison with explicit configuration snapshot;
4. owner manual acceptance in PC Studio;
5. controlled model-junction demonstration.

Synthetic simulation results are evidence for the selected simulated conditions only. They are not calibrated public-road performance or safety evidence.

## 9. Explicitly out of scope

- direct public-road signal control;
- production traffic-cabinet integration;
- bypassing hardware safety systems;
- autonomous authority over public-road movements;
- safety certification claims;
- claiming unsupported perception such as emergency vehicle, wheelchair, mobility-aid, or fall recognition without an actual compatible perception source.
