# Patch 0_2_5 — Ranked Signal Scenarios + Simulation Lab + Network Foundation

## Release state

- Candidate: V025 / `0_2_5`.
- Previous version: V024 / `0_2_4`.
- Owner-confirmed passed baseline: V024 / `0_2_4`.
- V025 remains an unaccepted candidate until the owner explicitly promotes it.
- This network-foundation update is a **same-candidate V025 patch**. It does not create V026.

## Purpose

V025 now has three connected prototype goals:

1. user-defined ranked traffic scenarios;
2. isolated Fixed-vs-Adaptive Simulation Lab telemetry; and
3. a generic intersection/network identity layer plus structured live decision context for later multi-intersection work.

Nothing in this patch connects to physical/public-road traffic infrastructure.

## Same-candidate network foundation

### Generic intersection configuration

New backend service: `app/services/intersection_network.py`.

Runtime configuration lives at `config/intersections.json`, which is ignored by Git and excluded from source patch archives. The default remains one logical node:

```text
intersection_main
```

The schema is generic and does not assume exactly two intersections. Each intersection contains:

- stable `id`;
- human-readable `label`;
- enabled state;
- zero or more `source_ids`;
- zero or more `zone_ids` reserved for later per-intersection zone binding;
- saved signal-profile name.

Directed network links contain:

- stable link id;
- source/destination intersection ids;
- source/destination approach labels;
- enabled state;
- configured prototype travel-time estimate.

Validation rejects duplicate ids, a source id assigned to multiple intersections, missing link endpoints, self-links, malformed ids, oversized lists, and invalid travel-time values.

### Current runtime boundary

The existing V025 camera, tracker and live signal controller remain single-junction. Network configuration is therefore identity/topology metadata only in this patch.

It does **not** yet:

- run two live signal controllers at the same time;
- preserve independent tracker state for several simultaneous cameras;
- transfer simulated agents from one junction to another;
- predict incoming platoons;
- coordinate green windows;
- implement emergency priority/pre-emption.

The API explicitly reports `cooperative_control_active: false` and `emergency_priority_active: false` rather than implying these future capabilities are already active.

### New APIs

- `GET /api/traffic/network`
- `PUT /api/traffic/network`
- `POST /api/traffic/network/reset`
- `GET /api/traffic/network/context?intersection_id=...`

The existing standard response envelopes, request IDs, service ownership, logging, and atomic JSON persistence conventions are retained.

### Stable errors

- `ATL-TRAFFIC-013` — invalid intersection/network configuration or unavailable requested intersection;
- `ATL-TRAFFIC-014` — network configuration read failure;
- `ATL-TRAFFIC-015` — network configuration write failure.

## Structured live decision context

`GET /api/traffic/state` keeps the existing V025 fields and is enriched at the traffic API boundary with:

- `intersection_id`;
- `observation_provenance` — `ai_detection`, `simulation`, `manual_test`, or `unavailable`;
- `network_context` — configured intersection and inbound/outbound neighbours;
- `decision_context` — deterministic `decision_id`, trigger category, source/intersection identity, active ranked scenario and observed conditions when available, requested service, timing, pedestrian/vehicle context, neighbour context, explicit emergency-placeholder state, and a readable explanation.

This does not alter signal arbitration. `signal_rules.py`, its protected phase sequence, persistence/cooldown logic, ranked arbitration, and existing persisted signal-rule history remain unchanged.

`decision_context` is a live explanation projection; it is not a second decision engine and does not claim historical causal reconstruction. Existing `outputs/signal_rules/decision_history.jsonl` remains the authoritative persisted controller-event history.

## Ranked signal scenarios retained

Traffic Logic continues to store editable scenarios inside each signal profile. A scenario contains:

- stable `id` and editable `label`;
- enabled/disabled state;
- numeric `rank` where **1 is highest**;
- `match: all | any`;
- 1-8 trigger conditions;
- persistence and cooldown seconds;
- one bounded signal action;
- allowed protected target phases;
- optional requested service (`pedestrian | vehicle`).

Conditions may use validated controller metrics or class counts inside configured polygon zones. Multiple scenarios may trigger but only the highest-ranked eligible scenario executes. Missing/stale/phase-ineligible/cooldown scenarios do not block the next eligible one.

The protected order remains:

```text
vehicle green → vehicle yellow → all-red → pedestrian WALK → pedestrian CLEAR → all-red
```

## Simulation Lab retained

The existing V025 Fixed-vs-Adaptive Simulation Lab remains isolated from the live camera/controller runtime. It snapshots configured zones and computes synthetic per-zone/per-class observations so zone-based scenarios can participate in the Adaptive benchmark.

It still records:

- vehicle/pedestrian wait distributions;
- queue average/p95/peak/queue-seconds/active share;
- simultaneous queue time;
- vehicle/pedestrian/combined throughput;
- vehicle passages per green minute;
- phase time/share, transitions and cycles;
- clearance time/share;
- scenario application counts and timing extension/reduction totals;
- conflict-overlap diagnostic;
- paginated raw timeline samples.

The network foundation deliberately does not change the single-junction experiment model yet.

## Files added/changed by this same-candidate update

Backend:

- add `app/services/intersection_network.py`;
- add `app/services/decision_context.py`;
- update `app/routes/traffic.py`;
- update `app/models.py`;
- update `app/core/error_codes.py`.

Repository/runtime handling:

- update `config/.gitignore` for runtime `intersections.json`;
- add `scripts/test_intersection_network.py`.

Documentation/release state:

- `VERSION`;
- `CHANGELOG.md`;
- `README.md`;
- `docs/API_CONTRACTS.md`;
- `docs/ERROR_CODES.md`;
- `docs/ARCHITECTURE.md`;
- this patch note.

## Limitations

- The live receiver still keeps one latest uploaded frame; simultaneous multi-camera retention is not implemented.
- The current tracker still owns one active track set and resets when source identity changes.
- The live signal controller remains one runtime controller.
- `zone_ids` and link travel times are configuration metadata for future work; they do not currently alter signal logic.
- No emergency-vehicle perception or emergency pre-emption exists.
- Decision provenance identifies the current evidence source but does not improve detector accuracy.
- Existing detector/class-label limitations, lightweight tracking limitations, and Simulation Lab calibration limitations remain.
- No result establishes public-road performance or safety.

## Primary acceptance checks for the network-foundation update

1. Start PC Studio/backend normally and confirm inherited V025 pages/functions still load.
2. `GET /api/traffic/network` should return one default `intersection_main`, no links, and `cooperative_control_active: false`.
3. Save three intersections (A/B/C) and at least two directed links through `PUT /api/traffic/network`; confirm the same generic schema accepts more than two nodes.
4. Map `camera_a` to A and `camera_b` to B. Confirm a duplicate source mapping is rejected with `ATL-TRAFFIC-013`.
5. Confirm a link to a nonexistent intersection and a self-link are rejected with `ATL-TRAFFIC-013`.
6. Reload/restart the backend and confirm the network configuration persists from `config/intersections.json`.
7. `GET /api/traffic/network/context?intersection_id=intersection_b` should show both inbound/outbound neighbours when configured.
8. Start camera Simulation mode. `GET /api/traffic/state` should include `intersection_id`, `network_context`, `decision_context`, and explicit `observation_provenance`.
9. When `simulation_camera` is mapped to A, confirm `/api/traffic/state.intersection_id` resolves to A.
10. Trigger a V025 ranked scenario and confirm `decision_context.scenario` contains the winner and observed condition values without changing the existing winner/action behavior.
11. Confirm `decision_context.emergency_context.active` is false and the note states emergency recognition/pre-emption is not implemented.
12. Confirm `decision_context.cooperative_control_active` is false.
13. Re-run existing ranked-scenario, signal-rules, simulation-experiment, camera simulation, tracking/flow, occupancy, dataset/training/inference/model/settings/log regressions.
14. Confirm the V025 Simulation Lab remains deterministic for the same seed/config and still does not reset the live simulation.
15. Confirm no feature controls physical/public-road traffic infrastructure.

## Safety

All signal scenarios, topology links, neighbour context, decision explanations, comparisons and phase outputs remain local prototype/simulation information. Physical/public-road traffic control remains disabled and outside project scope.

## Same-candidate documentation hardening update

This follow-up does not change V025 behavior or promote the candidate. It improves repository guidance after a documentation audit found durable guides that still contained obsolete early/V024-era "current state" text.

### Documentation authority changes

- added `docs/DOCUMENTATION_MAP.md` to define authority order and distinguish current-state, durable, and historical documents;
- added `docs/PROJECT_SCOPE.md` to classify implemented/foundation/simulation-only/planned/out-of-scope capabilities and record evidence gates for the five planned invention capability areas;
- rewrote `HUMAN_GUIDE.md`, `DEVELOPMENT_WORKFLOW.md`, and `VERSIONING.md` so they no longer own hard-coded current release snapshots;
- strengthened `AGENTS.md`, `AI_AGENT_GUIDE.md`, and `AI_AGENT_CHECKLIST.md` around release-state authority, capability-claim discipline, documentation anti-drift, network architecture, provenance, and exact test evidence;
- refreshed `START_HERE.md`, `ROADMAP.md`, `PC_STUDIO_FUNCTION_LIST.md`, `ARCHITECTURE.md`, and README so current network-foundation status and planned dependency order are explicit.
- refreshed `DATA_FORMAT.md`, `DEBUGGING_AND_LOGGING.md`, and `GUI_PLAN.md` to remove early-placeholder assumptions and document V025 data/provenance/network/explanation semantics.
- refreshed the PC Studio backend/frontend READMEs to remove V024-era labels/rule terminology and document current scenario, Simulation Lab, network-foundation, polling, data-semantic, and architecture ownership.

### Planned capability documentation

The repository now explicitly records these planned invention capability families:

1. multi-intersection cooperation;
2. emergency priority;
3. stronger pedestrian-aware control;
4. different vehicle classes;
5. explainable decisions.

The docs distinguish current foundations from completed behavior. In particular, configured network links are not described as active cooperation and emergency priority remains planned.

### Documentation policy

Long-lived guides should remain version-agnostic. Current candidate facts belong in root `VERSION`, `START_HERE.md`, the current `PATCH_*`, `LOCAL_TESTING.md`, `TEST_READY_CHECKLIST.md`, and `CHANGELOG.md`. Historical patch/changelog facts remain historical and should not be rewritten merely because they contain old version strings.
