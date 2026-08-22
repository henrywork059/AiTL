# Roadmap

Root `VERSION` defines the active candidate. This roadmap records dependency order, not acceptance state.

## 0_3_0 — vehicle-class-aware cooperative network candidate

V030 adds the first explicit regular vehicle-class evidence layer on top of V029:

- regular taxonomy `car | bus | truck | motorcycle | bicycle | other` plus separate V029 `emergency` special class;
- deterministic `legacy`, `mixed_urban`, and `freight_heavy` synthetic class profiles;
- unknown/unmapped regular labels fall back to `other`;
- per-class arrival/transfer/service/wait/queue evidence;
- seventh `class_aware_cooperative` mode;
- configurable selected class, weight, minimum waiting threshold, and bounded extension;
- neutral weight `1.0` / disabled priority causes no class timing effect;
- active pedestrian WALK/CLEAR protection;
- structured class-priority events and matched Class-aware-vs-Pedestrian-aware comparison;
- explicit synthetic provenance, with no live class-accuracy claim.

## Priority 1 — persistent explainability/evidence

Consolidate scenario, cooperation, pedestrian, vehicle-class, and emergency evidence into a stable persistent decision/event record that can reconstruct:

- decision/event ID;
- intersection ID;
- trigger category;
- local observations;
- neighbour/predicted-arrival context;
- pedestrian/emergency/vehicle-class context;
- action and timing before/after;
- grant/deny/suppression reason;
- provenance and concise explanation.

The consolidated format should avoid duplicating mode-specific evidence while preserving the current detailed event histories.

## Priority 2 — generalize network orchestration

After the selected two-intersection evidence is stable:

- support multiple simultaneous directed links/intersections;
- richer arrival prediction and travel-time uncertainty;
- network/corridor objectives alongside local objectives;
- multi-link emergency route context;
- multi-link class-aware objectives only where explicitly configured;
- compact PC Studio network experiment UI;
- live multi-source retention/tracking only as a separate prototype step.

## Priority 3 — live-evidence strengthening

Only after compatible perception sources exist should the project explore live emergency recognition or reliable live class/pedestrian identity. Any such source must expose explicit provenance/confidence and be evaluated separately from deterministic simulation evidence.

## Explicitly outside scope

Physical/public-road signal control, traffic-cabinet/pre-emption integration, bypassing safety systems, production autonomous authority, and safety certification remain outside this project.
