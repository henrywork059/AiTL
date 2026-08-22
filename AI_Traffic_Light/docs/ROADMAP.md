# Roadmap

Root `VERSION` defines the active candidate. This roadmap records dependency order, not acceptance state.

## 0_3_1 — persistent normalized decision evidence candidate

V031 consolidates existing V030 evidence without adding another signal-control mode:

- schema-versioned normalized decision/event ledger;
- scenario, cooperation, pedestrian, regular vehicle-class, emergency-priority and emergency-lifecycle trigger categories;
- deterministic evidence IDs and stable source references;
- local/neighbour/pedestrian/class/emergency context where available;
- action, grant/deny/defer/observe decision, timing before/after, reason and concise explanation;
- explicit provenance;
- JSON/CSV evidence surfaces;
- on-demand projection for older stored network runs without rewriting them;
- detailed legacy histories retained for drill-down/backward compatibility.

## Priority 1 — generalize network orchestration

After the selected two-intersection evidence is stable:

- support multiple simultaneous directed links/intersections;
- generic N-intersection run selection and topology validation;
- richer arrival prediction and travel-time uncertainty;
- network/corridor objectives alongside local objectives;
- multi-link emergency route context;
- multi-link class-aware objectives only where explicitly configured;
- keep V031 evidence schema generic enough that records do not depend on A/B-only assumptions.

## Priority 2 — compact PC Studio network experiment UI

Expose the backend experiment/evidence work without turning the frontend into an unbounded telemetry dump:

- network run setup and topology/link selection;
- per-mode/per-intersection summary tabs;
- pairwise comparison panels;
- normalized evidence filters by mode/category/intersection/decision/provenance;
- drill-down from V031 normalized records to detailed raw histories;
- CSV export access;
- strong synthetic/prototype-only labeling.

## Priority 3 — live-evidence strengthening

Only after compatible perception sources exist should the project explore live emergency recognition, reliable live class/pedestrian identity, or live multi-source retention/tracking. Any such source must expose explicit provenance/confidence and be evaluated separately from deterministic simulation evidence.

## Explicitly outside scope

Physical/public-road signal control, traffic-cabinet/pre-emption integration, bypassing safety systems, production autonomous authority, and safety certification remain outside this project.
