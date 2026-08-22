# Start Here — Current V031 candidate

Root `VERSION` is authoritative. V031 / `0_3_1` is the current unaccepted candidate; V024 / `0_2_4` remains the owner-confirmed passed baseline. V030 is the previous candidate because the owner explicitly requested V031 before separately accepting V030.

The current same-candidate repair adds explicit network-overlay arbitration, non-reapplying post-advisory snapshots, and protected-service request lifecycle metadata. The seven experiment modes remain ablation/comparison modes; no integrated class+emergency mode is claimed.

## What V031 changes

V031 keeps the seven V030 network modes and their protected timing behavior unchanged. It adds **persistent normalized explainability/evidence** so users and future agents do not need separate parsers for every scenario/cooperation/pedestrian/class/emergency history shape.

One `POST /api/traffic/network-experiments` run still contains:

1. Fixed;
2. Independent Adaptive;
3. Cooperative Adaptive;
4. Pedestrian-aware Cooperative;
5. Class-aware Cooperative;
6. Emergency Baseline Cooperative;
7. Emergency-priority Cooperative.

V031 adds `decision_evidence` to new stored runs. The schema-v1 ledger normalizes:

- ranked scenario evidence;
- neighbour cooperation;
- pedestrian service/clearance guards;
- vehicle-class priority;
- emergency priority;
- emergency lifecycle.

Each compact record includes deterministic identity, mode/time/intersection/link context, decision/action/applied fields, timing, reason, explanation, relevant context, provenance and a `source_ref` to the preserved detailed event history.

## Evidence API

New read surfaces:

```text
GET /api/traffic/network-experiments/{run_id}/evidence
GET /api/traffic/network-experiments/{run_id}/evidence.csv
```

Older stored network runs without a persisted V031 block are projected on demand from the detailed evidence they already contain. They are not silently rewritten. Pre-V031 scenario observations cannot be reconstructed if they were never stored.

## Scenario snapshots

For V031+ network runs, the isolated simulator records a scenario snapshot when the active ranked scenario changes for a protected phase. It includes winner/action/reason, local observations, phase and available base/effective timing. This is evidence capture only; arbitration remains owned by `signal_rules.py`.

## Retained V030 behavior

V031 retains:

- V030 regular class taxonomy/profiles/per-class metrics and Class-aware Cooperative mode;
- V029 matched configured emergency baseline/priority lifecycle and downstream preparation;
- V028 pedestrian request-age/starvation/clearance evidence;
- V027 bounded neighbour-informed cooperation;
- V026 deterministic A→B transfer and separate per-intersection controllers;
- V025 ranked scenarios and single-junction Simulation Lab;
- existing camera/dataset/training/model/zone/analytics workflows.

## Current limitations

- The normalized ledger is currently a network-experiment evidence surface, not a universal live-runtime audit database.
- Historical runs can only project fields that were actually persisted at the time.
- The benchmark still selects one directed two-intersection pair.
- PC Studio has no dedicated network/evidence dashboard yet; V031 remains backend/API/test-first.
- All class, cooperation, pedestrian and emergency network evidence remains synthetic simulation evidence.
- No physical/public-road signal controller, cabinet, pre-emption interface, safety-interlock bypass, or safety-certification claim exists.

## Validation starting point

Read:

1. `docs/PATCH_0_3_1.md`;
2. `docs/LOCAL_TESTING.md`;
3. `docs/TEST_READY_CHECKLIST.md`;
4. `docs/PROJECT_SCOPE.md`;
5. `docs/API_CONTRACTS.md`.

Focused regressions:

```powershell
python .\scripts\test_network_simulation_experiments.py
python .\scripts\test_pedestrian_aware_network_simulation.py
python .\scripts\test_emergency_priority_network_simulation.py
python .\scripts\test_vehicle_class_aware_network_simulation.py
python .\scripts\test_decision_evidence_network_simulation.py
```

Owner acceptance is still required before `passed_baseline` changes.

## Next invention direction

After V031 acceptance, the next dependency is generalizing the evidence-backed network simulation beyond one selected two-intersection link, followed by a compact network/evidence UI.
