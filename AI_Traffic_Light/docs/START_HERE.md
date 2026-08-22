# Start Here — Current V030 candidate

Root `VERSION` is authoritative. V030 / `0_3_0` is the current unaccepted candidate; V024 / `0_2_4` remains the owner-confirmed passed baseline. V029 is the previous candidate because the owner explicitly requested V030 before separately accepting V029.

## What V030 changes

V030 preserves the V029 deterministic two-intersection cooperation, pedestrian-aware, and matched emergency-priority benchmark and adds explicit **simulation-only regular vehicle-class behavior/evidence**.

One `POST /api/traffic/network-experiments` run now contains seven modes:

1. **Fixed**;
2. **Independent Adaptive**;
3. **Cooperative Adaptive**;
4. **Pedestrian-aware Cooperative**;
5. **Class-aware Cooperative** — same cooperation/pedestrian layer plus configured regular-class timing advisory;
6. **Emergency Baseline Cooperative**;
7. **Emergency-priority Cooperative**.

Class-aware Cooperative vs Pedestrian-aware Cooperative is the V030 policy-isolation pair. The V029 emergency pair remains separate.

## Vehicle-class taxonomy and demand

Regular simulator classes are:

`car`, `bus`, `truck`, `motorcycle`, `bicycle`, `other`.

`emergency` remains a separate V029 special simulator class. Unknown/unmapped regular labels normalize to `other`.

Class profiles:

- `legacy` — car/bus mix compatible with the earlier simulator;
- `mixed_urban` — broader urban class mix;
- `freight_heavy` — greater truck share.

These are seeded synthetic inputs with `synthetic_vehicle_class_demand` provenance. They are not camera/model accuracy claims.

## Bounded class-aware behavior

Class-aware Cooperative can be enabled/disabled and configured with one selected regular class, a weight, minimum waiting count, and maximum extension.

- weight `1.0` is neutral;
- weight above `1.0` may extend active vehicle green inside phase/cycle/class caps;
- it may request earlier protected vehicle service by shortening only the current phase toward its configured minimum;
- it never skips protected phase order;
- active pedestrian WALK/CLEAR with local waiting/crossing demand is protected.

Each event records class, waiting count, oldest wait, weight, weighted demand, phase, action, timing delta, reason, role/intersection, and synthetic provenance.

## V029 and earlier behavior retained

V030 retains:

- V029 matched configured emergency-event baseline/priority lifecycle and downstream preparation;
- V028 pedestrian request-age, starvation-prevention and synthetic crossing-clearance evidence;
- V027 bounded neighbour-informed cooperation;
- V026 deterministic A→B transfer and separate per-intersection controllers;
- V025 ranked scenarios and single-junction Fixed-vs-Adaptive Simulation Lab;
- topology/source identity, structured decision context/provenance, occupancy/flow separation, dataset/training/model and ESP camera workflows.

## Current limitations

- Class labels generated for V030 experiments are synthetic, not live perception.
- The class policy is a configurable prototype weighting layer, not a claim that buses/trucks/etc. should receive real-world priority.
- The network benchmark still selects one configured directed pair.
- Existing PC Studio Simulation Lab UI remains single-junction; V030 network class evidence is backend/API/test-first.
- No physical/public-road signal controller, cabinet, pre-emption interface, safety interlock bypass, or safety-certification claim exists.

## Validation starting point

Read:

1. `docs/PATCH_0_3_0.md`;
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
```

Owner acceptance is still required before `passed_baseline` changes.

## Next invention direction

After V030 acceptance, the next high-value layer is **persistent consolidated explainability/evidence**, followed by generalization beyond one selected two-intersection link.
