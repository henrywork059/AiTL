# Start Here — current V025 candidate

Read root `VERSION` first. At this documentation update, V025 / `0_2_5` remains the current unaccepted candidate and V024 / `0_2_4` is the owner-confirmed passed baseline. If `VERSION` differs, follow `VERSION`.

## What the current V025 candidate contains

### Ranked signal scenarios

- editable scenarios with rank `1` highest;
- controller-metric or zone/class-count conditions;
- ALL/ANY matching;
- one highest-ranked eligible winner per evaluation;
- bounded actions, persistence, cooldown, protected target phases, requested service;
- explicit winner/suppressed/inactive/unavailable reasons and observed values;
- migration of older rule configuration into scenarios.

### Simulation Lab

- isolated deterministic Fixed-vs-Adaptive comparison using selected profile/density/duration/seed;
- zone snapshot and synthetic zone/class observations;
- wait, queue, throughput, phase use, scenario application, timing adjustment, clearance, and conflict diagnostic telemetry;
- persisted runs, reopen/delete, CSV export;
- grouped/paginated one-page presentation;
- no mutation of the live camera/controller runtime.

### Same-candidate network/explanation foundation

- persistent generic intersection identities and directed neighbour links;
- source-to-intersection resolution;
- topology context API;
- explicit observation provenance;
- structured live decision context with scenario/timing/pedestrian/vehicle/neighbour context;
- explicit flags showing cooperative control and emergency priority are not active yet.

This foundation does **not** yet provide multi-intersection timing coordination, vehicle transfer between intersections, predicted arrivals, emergency pre-emption, or multiple simultaneously active live controllers.

## Planned invention direction

`PROJECT_SCOPE.md` records five planned capability areas and their evidence boundaries:

1. multi-intersection cooperation — highest next architecture priority;
2. emergency priority;
3. stronger pedestrian-aware control;
4. different vehicle-class handling;
5. explainable decisions.

The current network/explanation work is foundation for those features, not a claim that all five are complete.

## Key documents

- `DOCUMENTATION_MAP.md` — which file is authoritative for what;
- `PROJECT_SCOPE.md` — implemented/foundation/planned capability status;
- `ARCHITECTURE.md` / `CODE_STRUCTURE.md` — system/module ownership;
- `PC_STUDIO_FUNCTION_LIST.md` — current functional catalog;
- `LOCAL_TESTING.md` / `TEST_READY_CHECKLIST.md` — current candidate validation;
- `PATCH_0_2_5.md` — V025 change record.

## Recommended validation order

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light"
$py = ".\apps\pc-studio\backend\.venv\Scripts\python.exe"
& $py -m compileall ".\apps\pc-studio\backend\app" ".\scripts"
& $py ".\scripts\check_structure.py"
```

Then run the current focused/inherited backend regressions listed in `LOCAL_TESTING.md`, live smoke with the backend running, and frontend `npm ci`, `npm run typecheck`, `npm run build`.

## Interpretation limitations

- zone/class values are per-frame detector observations, not throughput;
- occupancy and track-derived flow are distinct;
- configured network links are metadata, not measured transfers;
- Simulation Lab is synthetic local evidence, not a calibrated road microsimulator/safety evaluation;
- mobility/fall/emergency recognition must not be claimed unless an actual compatible perception source is implemented.

## Safety boundary

AiTL remains a supervised local simulation/computer-vision prototype. No detection, ranked scenario, timing adjustment, network link, explanation, or experiment output is connected to physical/public-road signal infrastructure.
