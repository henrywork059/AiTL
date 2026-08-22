# Patch 0_3_1 — persistent normalized decision evidence

## Release state

- version: `0_3_1` / V031
- previous version: `0_3_0` / V030
- owner-confirmed passed baseline remains: `0_2_4` / V024
- status: candidate

The owner explicitly requested V031 before separately accepting V030. Automated validation does not promote the passed baseline.

## Purpose

V030 completed the planned simulation-only capability stack for cooperation, pedestrian awareness, emergency priority, and regular vehicle classes. Those layers each already produced useful but differently-shaped detailed histories. V031 adds the next roadmap dependency: one stable evidence schema that can reconstruct **what happened, where, why, what context was used, what timing changed, and where the original detailed record lives**.

V031 does not add a new control mode or change protected signal ownership.

## Same-candidate repair after code review

The current V031 candidate was reviewed against GitHub `main` before acceptance. This repair keeps version `0_3_1` and fixes three correctness/traceability issues without promoting the baseline:

1. **Cross-layer pedestrian starvation arbitration** — once local pedestrian wait reaches `pedestrian_max_wait_seconds` and pedestrian service has not started, ordinary cooperation and regular vehicle-class priority are deferred. This prevents a same-tick vehicle extension from undoing the pedestrian service request. Emergency priority remains a separate higher-priority simulated advisory, while its active-crossing denial guard is unchanged.
2. **Complete timing reconstruction** — cooperation, pedestrian-awareness, vehicle-class, and emergency-priority detailed events now retain `previous_duration_seconds` and `effective_duration_seconds`; normalized evidence projects those values when present. Older stored runs may still expose `null` because the historical source event never stored them.
3. **Pedestrian decision semantics** — `pedestrian_service_pending` and `pedestrian_request_queued` normalize to `decision: defer`; applied pedestrian timing changes remain `grant`, while passive below-threshold observations remain `observe`.

The focused V031 regression includes a direct cross-layer test proving ordinary cooperation/class handlers are not invoked while the max-wait lock is active and that the lock releases once pedestrian WALK/CLEAR starts.

## Implemented

### Schema-v1 normalized decision ledger

Each newly persisted network experiment contains:

```text
decision_evidence.schema_version = 1
decision_evidence.record_count
decision_evidence.applied_count
decision_evidence.categories
decision_evidence.decisions
decision_evidence.records[]
```

Normalized trigger categories:

- `scenario`;
- `cooperation`;
- `pedestrian`;
- `vehicle_class`;
- `emergency_priority`;
- `emergency_lifecycle`.

Each record contains a deterministic evidence ID, mode/time/intersection/link identity, trigger/action/decision/applied fields, phase before action, timing delta and available before/after duration, relevant local/neighbour/pedestrian/vehicle-class/emergency context, provenance, reason, concise explanation, and `source_ref` back to the detailed history.

### Scenario evidence snapshots

V031 network simulation runtimes now capture a compact scenario snapshot whenever the active ranked scenario changes for a protected phase. The snapshot retains the winner ID, phase, action/reason, observations and available base/effective timing. This is evidence capture only and does not change arbitration.

### Preserve detailed histories

The normalized ledger is additive. Existing detailed fields such as `coordination_events`, `pedestrian_awareness_events`, `vehicle_class_priority_events`, `emergency_priority_events`, and `emergency_lifecycle_events` remain unchanged for compatibility and drill-down.

### Historical projection

`service.evidence(run_id)` returns a persisted V031 ledger when present. For older stored network runs that do not contain `decision_evidence`, V031 projects the schema from whatever detailed histories are available **without rewriting the historical JSON file**. Pre-V031 runs naturally cannot reconstruct scenario observation snapshots that were never stored.

### API / CSV

Added:

- `GET /api/traffic/network-experiments/{run_id}/evidence`;
- `GET /api/traffic/network-experiments/{run_id}/evidence.csv`.

The CSV keeps `X-Request-ID` and includes normalized identity, decision/action/timing/provenance/reason/explanation/context/source-reference columns.

### Repeatability

Individual evidence records intentionally do not embed the random experiment `run_id`. The enclosing experiment/endpoint already identifies the run; keeping volatile metadata out of records preserves seeded repeatability checks. Evidence IDs derive from stable mode/category/trigger/source references.

## Architecture

New service:

`apps/pc-studio/backend/app/services/decision_evidence.py`

It owns normalization/export only. It must not arbitrate scenarios, alter controller timing, mutate live runtime state, or reinterpret synthetic provenance as live perception.

## No new stable error code

Existing experiment read/write/delete error semantics are reused.

## Deliberately not implemented

- general N-intersection orchestration;
- new network experiment frontend/dashboard;
- live emergency or class recognition;
- physical/public-road signal authority;
- deletion/replacement of the detailed mode-specific histories;
- retroactive reconstruction of observations that older stored runs never captured.

## Validation focus

Owner acceptance should confirm:

1. all V027/V028/V029/V030 focused regressions still pass;
2. V031 evidence regression passes;
3. schema version is `1` and IDs are deterministic;
4. current V031 runs expose all applicable trigger categories;
5. scenario records include local observations when a ranked scenario is active;
6. evidence records include source references/provenance/reasons/explanations;
7. repeated seeded runs remain equal except normal run metadata;
8. older stored results can be projected on demand without being rewritten;
9. JSON and CSV evidence endpoints preserve standard API/request-ID behavior;
10. no evidence service changes protected signal timing or introduces a public-road control claim;
11. a max-wait pedestrian request cannot be undone by ordinary cooperation or class-priority extension before pedestrian service begins;
12. newly generated cooperation/pedestrian/class/emergency-priority evidence retains previous/effective timing when the controller supplies it, and pending/queued pedestrian requests normalize to `defer`.
