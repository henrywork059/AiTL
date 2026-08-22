# Start Here — Current V029 candidate

Root `VERSION` is authoritative. V029 / `0_2_9` is the current unaccepted candidate; V024 / `0_2_4` remains the owner-confirmed passed baseline. V028 is the previous candidate because the owner explicitly requested V029 before separately accepting V028.

## What V029 changes

V029 preserves the V028 deterministic two-intersection network benchmark and adds an explicit **simulation-only emergency-priority lifecycle**.

One `POST /api/traffic/network-experiments` run now contains six modes:

1. **Fixed**;
2. **Independent Adaptive**;
3. **Cooperative Adaptive**;
4. **Pedestrian-aware Cooperative**;
5. **Emergency Baseline Cooperative** — same pedestrian/cooperation logic plus the configured synthetic emergency event, but no emergency timing priority;
6. **Emergency-priority Cooperative** — receives the same emergency event and may apply bounded emergency timing priority.

The two emergency modes are the policy-isolation pair: they share the same base arrival plan and the same emergency vehicle/event. Their difference is emergency-priority behavior.

## Emergency event and evidence

The V029 event is explicitly configured/synthetic. It records:

- deterministic emergency event and vehicle IDs;
- emergency vehicle type: `ambulance`, `fire_engine`, or `police`;
- source/destination intersection and approach;
- selected directed link;
- activation time;
- `simulated_configured_emergency_event` provenance;
- `confidence: null` and `detector_claimed: false`;
- activation → source departure → downstream arrival → clear → recovery lifecycle evidence.

V029 does **not** claim that a camera or model recognized an emergency vehicle.

## Protected priority behavior

Emergency-priority Cooperative may:

- extend an active vehicle green, bounded by the configured phase maximum, maximum-cycle cap, and emergency extension cap;
- request earlier vehicle service by shortening only the **current** protected phase toward its configured minimum;
- prepare the downstream intersection when the emergency vehicle enters the configured lookahead window.

It does not skip phase order. An active simulated pedestrian crossing causes an explicit emergency-priority denial until that crossing clears through protected service.

Each evaluation records grant/deny/defer, action, phase, role, ETA, timing delta, reason, provenance, and intersection/link identity.

## V028 and earlier behavior retained

V029 retains:

- V028 pedestrian request-age, starvation-prevention and synthetic crossing-clearance evidence;
- V027 bounded neighbour-informed cooperation;
- V026 deterministic A→B vehicle transfer and per-intersection controllers;
- V025 ranked scenarios and single-junction Fixed-vs-Adaptive Simulation Lab;
- topology/source identity, structured decision context/provenance, occupancy/flow separation, dataset capture/labeling/training, model management, and ESP camera receiving.

## Current limitations

- The network benchmark selects one configured directed pair; it is not yet general N-intersection cooperative orchestration.
- Emergency events are simulation/configuration inputs, not live perception.
- The existing PC Studio Simulation Lab UI remains single-junction; V029 network/emergency evidence is backend/API/test-first.
- No physical/public-road traffic controller, cabinet, pre-emption interface, safety interlock bypass, or safety-certification claim exists.

## Validation starting point

Read:

1. `docs/PATCH_0_2_9.md`;
2. `docs/LOCAL_TESTING.md`;
3. `docs/TEST_READY_CHECKLIST.md`;
4. `docs/PROJECT_SCOPE.md`;
5. `docs/API_CONTRACTS.md`.

The focused regressions are:

```powershell
python .\scripts\test_network_simulation_experiments.py
python .\scripts\test_pedestrian_aware_network_simulation.py
python .\scripts\test_emergency_priority_network_simulation.py
```

Owner acceptance is still required before `passed_baseline` changes.

## Next invention direction

After V029 acceptance, the next high-value layer is broader **vehicle-class behavior and class-aware evidence**, followed by stronger persistent explainability and generalization beyond one selected two-intersection link.
