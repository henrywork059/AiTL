# Start Here — Current V025 candidate

The current candidate is V025 / `0_2_5`. V024 / `0_2_4` is the previous version and is now the owner-confirmed passed baseline. V025 remains unaccepted until the owner explicitly promotes it.

## What V025 adds

### Ranked signal scenarios

- replace the fixed adaptive-rule editing surface with user-defined ranked scenarios;
- scenario conditions can use controller metrics or detected class counts inside a selected polygon zone;
- scenarios can combine 1–8 conditions with ALL/ANY matching;
- rank `1` is highest; multiple scenarios may trigger but only the highest-ranked eligible scenario executes each evaluation;
- explicit winner/suppressed/inactive/unavailable explanations with observed condition values;
- bounded actions, persistence, cooldown, requested pedestrian/vehicle service, protected phase targets, stale fallback, and inherited timing/cycle guards;
- migrate older V023/V024 saved rule configs into editable scenarios;
- compact Traffic Logic tabs: Live Decision / Signal Timing / Scenario Rules / Test & Safety / History.

### Simulation Lab

- isolated deterministic Fixed-vs-Adaptive comparisons using the same requested profile, density, duration, seed and configured zone snapshot;
- synthetic per-zone/per-class observations so zone-based scenarios can participate in Adaptive benchmarking;
- richer wait, queue, throughput, signal-use, scenario-application, clearance, and simulator conflict-overlap telemetry;
- bounded persisted experiment history plus aligned Fixed/Adaptive sample CSV export;
- one-page grouped controls, stored-run selection, tabs, toggle buttons, dropdowns, and paginated raw data;
- no mutation of the live Camera Sources simulation or live signal-controller runtime while an experiment runs.

## Inherited V024/V022/V021 capabilities

V024 maintenance hardening remains in place: shared atomic persistence for migrated JSON state, synchronized zone/model-registry transitions, serial App-level polling, and the Material-derived PC Studio design system.

V022 cross-frame tracking/counting-line flow and V021 occupancy analytics remain available. Occupancy, flow, live signal history, and V025 experiment telemetry remain separate data categories.

## Recommended local test order

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light"
$py = ".\apps\pc-studio\backend\.venv\Scripts\python.exe"
& $py -m compileall ".\apps\pc-studio\backend\app" ".\scripts"
& $py ".\scripts\check_structure.py"
& $py ".\scripts\test_signal_rules_service.py"
& $py ".\scripts\test_signal_scenarios.py"
& $py ".\scripts\test_simulation_experiments.py"
& $py ".\scripts\test_atomic_json_store.py"
& $py ".\scripts\test_frontend_polling_structure.py"
```

Then run the complete non-live `scripts/test_*.py` regression set, start the backend, run `test_backend_smoke.py`, and run frontend `npm ci`, `npm run typecheck`, and `npm run build`.

See `LOCAL_TESTING.md` and `TEST_READY_CHECKLIST.md` for the full V025 acceptance sequence.

## Interpretation limitations

Zone/class scenario values are per-frame detector observations, not throughput. Missing/deleted zones make the referencing scenario unavailable until edited.

Simulation Lab is a synthetic local A/B benchmark, not a calibrated traffic microsimulator or safety evaluation. Same-seed comparisons are repeatable, but policy-dependent movement can change later recycled-agent timing inside each mode. Interpret results as evidence for the selected simulated conditions only.

The current model is not claimed to detect wheelchairs/mobility assistance or falls. Those conditions remain explicit Test-mode inputs until a compatible perception source is deliberately added.

## Safety boundary

AiTL remains a supervised local simulation/computer-vision prototype. No signal scenario, timing adjustment, experiment result, detection, tracking, or analytics output is connected to physical/public-road traffic infrastructure.
