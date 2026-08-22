# Local Testing Notes (V026)

V026 / `0_2_6` is the current candidate by explicit owner request. V025 / `0_2_5` is the previous unaccepted candidate. V024 / `0_2_4` remains the owner-confirmed passed baseline. Automated checks never promote a candidate.

## 1. Safe Windows update

Stop backend/frontend first. From the repository root:

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL"
git status --short
git pull --ff-only origin main
Get-Content .\AI_Traffic_Light\VERSION
```

Expected release fields:

```text
version: 0_2_6
previous_version: 0_2_5
passed_baseline: 0_2_4
```

Do not use `git clean -fd`. Preserve datasets, outputs, trained models, labels, runtime zones/settings/signal rules, `config/intersections.json`, occupancy/flow/signal history, and all experiment results.

## 2. Backend compile / structure / regression

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light"
$py = ".\apps\pc-studio\backend\.venv\Scripts\python.exe"
& $py -m pip install -r ".\apps\pc-studio\backend\requirements.txt"
& $py -m pip install -r ".\apps\pc-studio\backend\requirements-training.txt"
& $py -m compileall ".\apps\pc-studio\backend\app" ".\scripts"
& $py ".\scripts\check_structure.py"
& $py ".\scripts\test_network_simulation_experiments.py"
```

Then run the complete non-live regression set:

```powershell
$tests = Get-ChildItem ".\scripts\test_*.py" | Where-Object { $_.Name -ne "test_backend_smoke.py" }
foreach ($test in $tests) {
    Write-Host "`n===== RUNNING $($test.Name) =====" -ForegroundColor Cyan
    & $py $test.FullName
    if ($LASTEXITCODE -ne 0) { throw "TEST FAILED: $($test.Name)" }
}
```

Important inherited tests include `test_intersection_network.py`, `test_simulation_experiments.py`, `test_signal_scenarios.py`, `test_signal_rules_service.py`, camera/simulation, tracking/flow, persistence, dataset/training/model, frontend polling structure, and update-runner regressions.

`test_network_simulation_experiments.py` is the V026-focused regression. It checks deterministic seeded demand, separate A/B controller/runtime state, explicit transfer timing, persistence/list/get/delete/CSV, and invalid-link rejection.

## 3. Frontend release validation

V026 does not add a dedicated network-experiment page. The existing Simulation Lab UI remains the single-junction experiment surface, but frontend release metadata still changes to `0_2_6`.

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\apps\pc-studio\frontend"
npm ci
npm run typecheck
npm run build
```

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

Confirm health/smoke/template/version surfaces report `0_2_6` and retain request IDs.

## 5. Prepare a two-intersection topology

Keep the backend running. The example below creates two enabled intersections and one A→B link with a deterministic 7.5-second synthetic link travel time.

```powershell
$networkBody = @{
  config = @{
    schema_version = 1
    active_intersection_id = "intersection_a"
    intersections = @(
      @{ id="intersection_a"; label="Intersection A"; enabled=$true; source_ids=@("simulation_camera","camera_a"); zone_ids=@(); signal_profile="Normal" },
      @{ id="intersection_b"; label="Intersection B"; enabled=$true; source_ids=@("camera_b"); zone_ids=@(); signal_profile="Normal" }
    )
    links = @(
      @{ id="a_to_b"; enabled=$true; source_intersection_id="intersection_a"; destination_intersection_id="intersection_b"; source_approach="eastbound"; destination_approach="westbound"; travel_time_seconds=7.5 }
    )
  }
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Method Put -ContentType "application/json" -Body $networkBody -Uri "http://127.0.0.1:8000/api/traffic/network" | ConvertTo-Json -Depth 12
```

Confirm the saved topology contains the two intersections and enabled `a_to_b` link. This remains runtime config and must not be packaged in a source patch.

## 6. V026 network-experiment API acceptance

### 6.1 Run a deterministic network comparison

```powershell
$runBody = @{
  duration_seconds = 180
  density = "normal"
  seed = 26026
  sample_interval_seconds = 1
  profile = "Normal"
  label = "V026 acceptance"
  link_id = "a_to_b"
  transfer_share_percent = 70
} | ConvertTo-Json

$run1 = Invoke-RestMethod -Method Post -ContentType "application/json" -Body $runBody -Uri "http://127.0.0.1:8000/api/traffic/network-experiments"
$run1.data | ConvertTo-Json -Depth 15
```

Confirm:

1. `scenario.kind` is `two_intersection_network`.
2. `scenario.link.id` is `a_to_b` and its travel time is `7.5` seconds.
3. `fixed.intersections` and `adaptive.intersections` both contain `intersection_a` and `intersection_b`.
4. Each mode reports `cooperative_control_active: false` and `emergency_priority_active: false`.
5. Transfer counts are non-zero for this normal-density/180-second acceptance run.
6. At least one transfer event has `arrived_at_s`; for every arrived event, `arrived_at_s - departed_at_s` equals the configured link travel time (allow only normal displayed rounding).
7. Per-intersection waiting/queue/throughput/signal metrics exist.
8. Network metrics include transfers departed/arrived, transfer pipeline average/peak, corridor completion, end-to-end corridor travel, and aggregate vehicle wait/queue measures.
9. The response labels observations/transfers as synthetic experiment data rather than AI-detected live transfer.

### 6.2 Verify same-seed repeatability

Run exactly the same POST body again:

```powershell
$run2 = Invoke-RestMethod -Method Post -ContentType "application/json" -Body $runBody -Uri "http://127.0.0.1:8000/api/traffic/network-experiments"
```

The run IDs/creation timestamps will differ. Compare the scenario arrival plan and Fixed/Adaptive/comparison payloads; they should otherwise be repeatable for the same topology, policy, zones, seed, density, duration, interval, link, and transfer share.

The Fixed and Adaptive modes must use the **same exogenous arrival plan**. Confirm `scenario.arrival_plan.fingerprint_sha256` is stable across identical requests; the summary counts should also match. Their downstream transfer outcomes may differ because source service timing differs.

### 6.3 Persistence / retrieval / CSV / delete

```powershell
$runId = $run1.data.run_id
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/traffic/network-experiments?limit=20" | ConvertTo-Json -Depth 8
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/traffic/network-experiments/$runId" | ConvertTo-Json -Depth 15
Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/traffic/network-experiments/$runId/export.csv" -OutFile ".\v026_network_experiment.csv"
```

Confirm the CSV includes per-intersection queue/phase/service fields plus network transfer/pipeline/corridor fields, and the HTTP response contains `X-Request-ID`.

Restart the backend and confirm the stored `netexp_*` result can still be retrieved. Then delete one disposable run:

```powershell
Invoke-RestMethod -Method Delete -Uri "http://127.0.0.1:8000/api/traffic/network-experiments/$runId"
```

Deletion must not remove single-junction `exp_*` runs, zones, signal scenarios, topology config, captures, analytics, training results, or models.

### 6.4 Negative link check

Run with a missing/disabled `link_id`. Confirm the request fails with `ATL-TRAFFIC-013` (`TRAFFIC_NETWORK_INVALID`) and does not write a valid network experiment result.

## 7. Inherited single-junction acceptance

Re-run representative V025 checks:

- ranked scenario rank/arbitration, ALL/ANY, zone/class observations, persistence/cooldown, protected phase bounds, stale fallback, preview/history;
- topology/source identity and structured `decision_context`;
- single-junction Simulation Lab repeatability, persistence, CSV, and UI grouping;
- occupancy vs flow separation and tracking/counting lines;
- camera receiver/simulation, dataset capture/delete/label, training, model registry, settings/logs;
- atomic persistence and serial polling.

The existing `/api/traffic/experiments` endpoints must still work unchanged.

## 8. V026 interpretation / safety checks

Confirm the candidate does **not** claim any of the following:

- cooperative green-wave timing;
- neighbour-informed phase adjustment;
- emergency pre-emption;
- live measured vehicle transfer between configured cameras;
- calibrated public-road performance/safety.

V026 transfer events exist only inside the isolated synthetic network experiment. Live `config/intersections.json` links remain topology metadata.

## 9. Repository / ZIP checks

From the complete repository:

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL"
git diff --check
git status --short
```

From `AI_Traffic_Light`, validate the supplied ZIP:

```powershell
python .\scripts\validate_patch_zip.py <V026-patch.zip>
```

Compare ZIP members against the supplied manifest. Only explicit owner acceptance may change `passed_baseline`.
