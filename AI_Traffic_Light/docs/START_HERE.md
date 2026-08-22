# Start Here — Current V028 candidate

Root `VERSION` is authoritative. V028 / `0_2_8` is the current unaccepted candidate; V024 / `0_2_4` remains the owner-confirmed passed baseline. V027 is the previous candidate because the owner explicitly requested V028 before separately accepting V027.

## What V028 changes

V028 preserves/restores the intended V027 bounded cooperative two-intersection simulator and adds a fourth **Pedestrian-aware Cooperative** mode.

One `network-experiments` run now compares the same seeded demand across:

1. **Fixed** — configured normal timing only;
2. **Independent Adaptive** — local ranked scenarios, no neighbour influence;
3. **Cooperative Adaptive** — V027 predicted A→B arrivals can request bounded downstream timing changes;
4. **Pedestrian-aware Cooperative** — the same cooperation plus explicit local pedestrian service/clearance guards.

## Pedestrian-aware evidence

The fourth mode adds:

- oldest/max observed pedestrian wait;
- request start/fulfillment lifecycle;
- service-session count and fulfillment-time distribution;
- synthetic crossing occupancy after service;
- maximum-wait starvation prevention;
- bounded pedestrian WALK/CLEAR clearance reserve;
- structured pedestrian-awareness events with simulation provenance;
- Pedestrian-aware Cooperative vs Cooperative comparisons so the new layer can be evaluated separately.

When oldest waiting time reaches the configured threshold, the guard may request pedestrian service and shorten only the **current protected phase** toward its configured minimum. It never skips protected phases. When synthetic crossing occupancy is active during WALK/CLEAR, it may extend that phase only inside saved phase and cycle maxima.

V028 also strengthens cooperation: neighbour coordination must not shorten pedestrian WALK/CLEAR while either waiting demand **or active crossing occupancy** exists.

## Important preflight correction

During V028 preparation, GitHub `main` was internally inconsistent: `VERSION`, V027 docs/models/tests described Cooperative Adaptive, but `network_simulation_experiments.py` was still the V026 independent implementation. The V028 patch therefore carries the complete intended V027 cooperative service forward and layers V028 behavior on it.

## Preserved capability

V028 retains ranked scenarios, protected signal timing, the single-junction Fixed-vs-Adaptive Simulation Lab, intersection/topology identity, structured decision context/provenance, occupancy/flow separation, dataset capture/labeling/training, model management, and ESP camera receiving.

## Interpretation limits

- Network transfer, cooperation, pedestrian demand and crossing occupancy in this experiment are synthetic.
- `pedestrian_crossing_clearance_seconds` is a configurable simulator assumption, not a measured walking-speed model.
- Per-frame person counts remain occupancy observations, not unique throughput.
- Emergency priority remains inactive.
- The existing PC Studio Simulation Lab UI remains single-junction; V028 network evidence is backend/API/test-first.
- No V028 output controls physical/public-road signal infrastructure.

## Recommended validation order

Run the normal complete regression plus:

```powershell
& $py .\scripts\test_network_simulation_experiments.py
& $py .\scripts\test_pedestrian_aware_network_simulation.py
```

Then run `check_structure.py`, live backend smoke, frontend typecheck/build, and the manual checks in `TEST_READY_CHECKLIST.md`.

## Next dependency

After V028 acceptance, the next planned invention layer is a **simulated/configured emergency-priority lifecycle** with protected grant/deny/recovery and downstream preparation. Do not claim live emergency recognition unless a compatible perception source is deliberately added.
