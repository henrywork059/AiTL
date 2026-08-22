# Local Testing Notes (V025)

V025 / `0_2_5` is the current candidate. V024 / `0_2_4` is the previous version and is now the owner-confirmed passed baseline. Automated checks do not promote V025.

## Quick Windows workflow

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light"
.\scripts\update_test_run.ps1
```

The V024 helper remains the normal update → test → run path: it protects tracked work, fast-forwards `main`, synchronizes dependencies, runs backend/frontend validation and live smoke, then launches PC Studio without deleting runtime data.

## 1. Safe update

Stop backend/frontend. From the repository root:

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL"
git status --short
git pull --ff-only origin main
Get-Content .\AI_Traffic_Light\VERSION
```

Expected:

```text
version: 0_2_5
previous_version: 0_2_4
passed_baseline: 0_2_4
```

Do not use `git clean -fd`. Preserve runtime datasets, outputs, models, labels, zones, settings, `config/signal_rules.json`, `config/intersections.json`, occupancy/flow/signal history, and `outputs/simulation_experiments/`.

## 2. Backend compile/structure/regression

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light"
$py = ".\apps\pc-studio\backend\.venv\Scripts\python.exe"
& $py -m pip install -r ".\apps\pc-studio\backend\requirements.txt"
& $py -m pip install -r ".\apps\pc-studio\backend\requirements-training.txt"
& $py -m compileall ".\apps\pc-studio\backend\app" ".\scripts"
& $py ".\scripts\check_structure.py"

$tests = Get-ChildItem ".\scripts\test_*.py" | Where-Object { $_.Name -ne "test_backend_smoke.py" }
foreach ($test in $tests) {
    Write-Host "`n===== RUNNING $($test.Name) =====" -ForegroundColor Cyan
    & $py $test.FullName
    if ($LASTEXITCODE -ne 0) { throw "TEST FAILED: $($test.Name)" }
}
```

V025-focused regressions:

```powershell
& $py ".\scripts\test_signal_scenarios.py"
& $py ".\scripts\test_simulation_experiments.py"
& $py ".\scripts\test_intersection_network.py"
```

`test_signal_scenarios.py` verifies zone/class conditions, ALL matching, rank arbitration, unavailable-zone fallback, observed values, bounded phase adjustment, and preview behavior. `test_simulation_experiments.py` verifies same-seed repeatability, Fixed/Adaptive mode separation, adaptive scenario activity including zone-based scenarios, telemetry invariants, stored-run list/get/delete, and CSV export.

`test_intersection_network.py` verifies generic three-intersection topology, directed neighbour context, source-id resolution, numeric-leading camera-source compatibility, atomic persistence, duplicate-source rejection, missing/self-link rejection, and structured live decision-context construction without enabling cooperation/emergency behavior.

Retain the V024/V023 regressions including `test_atomic_json_store.py`, `test_frontend_polling_structure.py`, `test_signal_rules_service.py`, camera/simulation tests, tracking/flow tests, dataset/training/model tests, and all other `scripts/test_*.py` tests.

## 3. Frontend

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\apps\pc-studio\frontend"
npm ci
npm run typecheck
npm run build
npm run dev
```

This same-candidate network foundation is backend/API-first; no new dedicated frontend network editor is expected in this patch.

## 4. Backend + live smoke

Backend terminal:

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\apps\pc-studio\backend"
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Second terminal:

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light"
.\apps\pc-studio\backend\.venv\Scripts\python.exe .\scripts\test_backend_smoke.py
```

## 5. V025 ranked scenario acceptance

1. Confirm visible version is `0_2_5`, previous version is `0_2_4`, and `passed_baseline` is `0_2_4`.
2. Open Traffic → **Traffic Logic**. Confirm tabs are Live Decision / Signal Timing / Scenario Rules / Test & Safety / History.
3. In Scenario Rules, create a scenario using **Zone / class count**: choose a vehicle queue zone, class `car`, comparison `>`, threshold `2`, rank `1`, action Extend current phase by `4s`, target Vehicle green, requested service Vehicle. Save.
4. Make the live/simulation observation satisfy the condition. Live Decision should show the scenario as the winner and show the observed car count beside the condition.
5. Create a second simultaneously true scenario at rank `2`. Confirm rank `1` wins and rank `2` says it was suppressed by the higher-ranked winner.
6. Swap the ranks, Save, and confirm the other scenario wins. Rank `1` is always highest; duplicate saved ranks are rejected so arbitration remains unambiguous.
7. Edit the higher-ranked scenario to reference a nonexistent/deleted zone. Confirm it becomes **unavailable** and does not block the next eligible scenario.
8. Add a two-condition scenario. In ALL mode, both conditions must match. In ANY mode, either matching condition is enough.
9. Confirm persistence prevents immediate one-frame activation and cooldown prevents repeated adjustment after application.
10. Configure a triggered scenario whose target-phase checkboxes exclude the current phase. It should be suppressed for phase applicability and the next eligible scenario may win.
11. Confirm Fixed mode executes no adaptive scenario, while Adaptive mode uses live observations. Test mode additionally permits the explicit mobility/fall flags.
12. Confirm Signal Timing still rejects invalid protected minimum/order values and scenario actions never jump directly between conflicting movement phases.
13. Use Test & Safety preview/current observation and confirm preview does not mutate the running controller.
14. Confirm History records scenario application details including scenario id/label/rank/action and phase timing change.
15. Restart backend and confirm saved scenario definitions persist in `config/signal_rules.json`. An older V023/V024 config without `scenarios` should load through migration rather than fail.
16. Confirm zone/class counts are described as per-frame observations, not throughput.

## 6. Same-candidate intersection/network foundation acceptance

The following examples use PowerShell's `Invoke-RestMethod`. Keep the backend running on port 8000.

1. Read defaults:

```powershell
$network = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/traffic/network"
$network.data | ConvertTo-Json -Depth 8
```

Confirm `active_intersection_id` is `intersection_main`, one default intersection exists, links are empty, and `cooperative_control_active` is `false`.

2. Save a generic three-intersection topology:

```powershell
$body = @{
  config = @{
    schema_version = 1
    active_intersection_id = "intersection_a"
    intersections = @(
      @{ id="intersection_a"; label="Intersection A"; enabled=$true; source_ids=@("simulation_camera","camera_a"); zone_ids=@(); signal_profile="Normal" },
      @{ id="intersection_b"; label="Intersection B"; enabled=$true; source_ids=@("camera_b"); zone_ids=@(); signal_profile="Normal" },
      @{ id="intersection_c"; label="Intersection C"; enabled=$true; source_ids=@(); zone_ids=@(); signal_profile="Normal" }
    )
    links = @(
      @{ id="a_to_b"; enabled=$true; source_intersection_id="intersection_a"; destination_intersection_id="intersection_b"; source_approach="eastbound"; destination_approach="westbound"; travel_time_seconds=12.5 },
      @{ id="b_to_c"; enabled=$true; source_intersection_id="intersection_b"; destination_intersection_id="intersection_c"; source_approach="southbound"; destination_approach="northbound"; travel_time_seconds=18 }
    )
  }
} | ConvertTo-Json -Depth 10
Invoke-RestMethod -Method Put -ContentType "application/json" -Body $body -Uri "http://127.0.0.1:8000/api/traffic/network"
```

Confirm three intersections are accepted; the schema is not hard-coded to exactly two.

3. Read B's neighbour context:

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/traffic/network/context?intersection_id=intersection_b" | ConvertTo-Json -Depth 10
```

Confirm both A and C appear with inbound/outbound direction metadata and configured travel times.

4. Negative tests: try assigning `camera_a` to two intersections, linking to a nonexistent node, and creating a self-link. Each should fail with `ATL-TRAFFIC-013` and should not replace the last valid config.

5. Restart the backend and confirm the valid topology persists under `config/intersections.json`.

6. Start Camera Sources simulation and query:

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/traffic/state" | ConvertTo-Json -Depth 12
```

Confirm `intersection_id` resolves from `simulation_camera`, `observation_provenance` is `simulation`, and `network_context`/`decision_context` are present.

7. Trigger a ranked scenario. Confirm `decision_context.scenario.id/label/conditions` reflects the current winner and observed values while existing Traffic Logic winner/timing behavior is unchanged.

8. Confirm `decision_context.emergency_context.active` and `decision_context.cooperative_control_active` are both false. No network link should change another signal phase in V025.

9. `POST /api/traffic/network/reset` should restore `intersection_main` without deleting zones, signal scenarios, captures, analytics, models, or Simulation Lab runs.

## 7. V025 Simulation Lab acceptance

1. Open Traffic → **Simulation Lab**.
2. At a normal desktop window size, confirm setup controls, stored-run controls, tabs, and the selected data panel stay inside one workspace page. The page must not render all metric groups as a long vertical dashboard.
3. Confirm setup controls include Density, Duration, Signal profile, Seed, Sample interval, optional Run label, and Run comparison.
4. Start/observe the normal Camera Sources simulation, note its current scene/phase, then run a Simulation Lab comparison. Confirm the live simulation is not reset or switched.
5. Run Normal profile / Normal density / 300 seconds / seed `25025` twice. Values inside Fixed, Adaptive, and Comparison should repeat for identical configuration even though run IDs/timestamps differ.
6. Create/save a zone-based scenario whose condition can occur in the synthetic junction, then run Simulation Lab. Confirm the stored experiment scenario metadata includes the zone snapshot and Adaptive scenario-application telemetry can include that scenario.
7. Summary: confirm compact cards show Fixed, Adaptive, and percent/absolute change with preferred-direction semantics.
8. Waiting & queues: confirm average/median/p95/max wait, queue average/p95/peak, queue-seconds, queue-active percentage, and simultaneous queue time are available.
9. Throughput: confirm total and per-minute vehicle/pedestrian service, combined service rate, and vehicle passages per green minute.
10. Signal behavior: confirm phase utilization, transitions/cycles, clearance time, adaptive scenario application counts, timing extension/reduction totals, and conflict-overlap diagnostic.
11. Raw samples: switch Fixed/Adaptive toggle; change 25/50/100 row selection; use Previous/Next. The table should stay internally scrollable/paginated instead of growing the page.
12. Stored run dropdown: select an older result and confirm all tabs update to that run.
13. Export CSV and confirm aligned `fixed_*` and `adaptive_*` queue/service/phase/scenario columns exist (compatibility field names may still use `active_rules`).
14. Restart PC Studio/backend and confirm stored experiment JSON is still selectable.
15. Delete one disposable run. Confirm only that experiment result is removed; occupancy/flow history, signal scenario config/history, captures, zones, settings, models, and training data remain.
16. Confirm the page describes experiment data as local simulation results, not proof of general/public-road performance or safety.

## 8. Inherited functional checks

Re-run representative V024 acceptance checks: persistence, zone/model registry synchronization, serial polling, protected signal phase order, camera simulation behavior, occupancy vs flow separation, tracking/counting lines, capture/delete/label/training/models/settings/logs. Also re-run `test_signal_rules_service.py` to confirm the migrated default scenarios preserve inherited V023 controller behavior. Confirm no feature connects to physical/public-road traffic-light control.

## 9. Repository/ZIP checks

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL"
git diff --check
git status --short
```

From `AI_Traffic_Light`, validate the supplied ZIP with `python .\scripts\validate_patch_zip.py <zip>` and compare its member list with the supplied manifest. Only explicit owner acceptance may promote V025.
