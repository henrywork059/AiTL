# Local Testing Notes (V027)

V027 / `0_2_7` is the current candidate by explicit owner request. V026 / `0_2_6` is the previous unaccepted candidate. V024 / `0_2_4` remains the owner-confirmed passed baseline. Automated checks never promote a candidate.

## 1. Safe Windows update

Stop backend/frontend first. From the repository root:

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL"
git status --short
git pull --ff-only origin main
Get-Content .\AI_Traffic_Light\VERSION
```

Expected:

```text
version: 0_2_7
previous_version: 0_2_6
passed_baseline: 0_2_4
```

Do not use `git clean -fd`. Preserve datasets, outputs, models, labels, runtime zones/settings/signal rules, `config/intersections.json`, histories, and all experiment results.

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

Then run all non-live regression scripts:

```powershell
$tests = Get-ChildItem ".\scripts\test_*.py" | Where-Object { $_.Name -ne "test_backend_smoke.py" }
foreach ($test in $tests) {
    Write-Host "`n===== RUNNING $($test.Name) =====" -ForegroundColor Cyan
    & $py $test.FullName
    if ($LASTEXITCODE -ne 0) { throw "TEST FAILED: $($test.Name)" }
}
```

The V027-focused network regression must verify deterministic demand, separate A/B controller state, transfer timing, three-mode repeatability, coordination events/telemetry, persistence/list/get/delete/CSV, request validation, API request IDs, and invalid-link rejection.

## 3. Frontend validation

V027 does not add a dedicated network dashboard. Existing PC Studio Simulation Lab remains the single-junction surface; network cooperation is backend/API/test-first.

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

Confirm health/smoke/template/version surfaces report `0_2_7` and preserve request IDs.

## 5. Prepare a two-intersection topology

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

## 6. V027 cooperative network acceptance

### 6.1 Run the three-mode comparison

```powershell
$runBody = @{
  duration_seconds = 180
  density = "normal"
  seed = 27027
  sample_interval_seconds = 1
  profile = "Normal"
  label = "V027 acceptance"
  link_id = "a_to_b"
  transfer_share_percent = 70
  cooperation_lookahead_seconds = 12.0
  cooperation_max_extension_seconds = 5.0
  cooperation_min_incoming_vehicles = 1
} | ConvertTo-Json

$run1 = Invoke-RestMethod -Method Post -ContentType "application/json" -Body $runBody -Uri "http://127.0.0.1:8000/api/traffic/network-experiments"
$run1.data | ConvertTo-Json -Depth 18
```

Confirm:

1. `scenario.comparison` is `fixed`, `adaptive`, `cooperative`.
2. Fixed and Adaptive report `cooperative_control_active: false`; Cooperative reports `true`.
3. All three modes contain the same source/destination intersection IDs.
4. `scenario.arrival_plan.fingerprint_sha256` exists and is 64 hex characters.
5. Transfer events remain synthetic and arrived transfers obey the configured 7.5-second link travel time.
6. `cooperative.coordination_provenance` is `synthetic_predicted_arrivals`.
7. `cooperative.network_metrics.coordination.triggered` is non-zero for the acceptance run.
8. At least one coordination advisory is applied under this demand/settings combination.
9. Coordination events expose deterministic coordination ID, link/source/destination identity, provenance, incoming count, earliest ETA, action, reason, applied flag and timing delta.
10. Any vehicle-green extension stays within saved phase maximum and maximum-cycle bounds.
11. Any non-vehicle progression request only shortens the current phase toward its configured minimum; phase order is not skipped.
12. When local pedestrian demand is present during WALK/CLEAR, cooperation does not shorten that pedestrian phase and may record `protect_pedestrian_service`.
13. In the retained V027 three-mode cooperation checks, emergency priority remains inactive; V029 emergency modes are tested separately below.

Do **not** require Cooperative to beat Independent Adaptive on every metric. The acceptance condition is correct bounded neighbour-informed behavior and valid evidence, not guaranteed superiority.

### 6.2 Compare all three modes

Confirm:

- `comparison` remains the backward-compatible Adaptive-vs-Fixed structure;
- `comparisons.adaptive_vs_fixed` matches it;
- `comparisons.cooperative_vs_fixed` exists;
- `comparisons.cooperative_vs_adaptive` exists;
- cooperative comparison entries use `cooperative` values/direction labels rather than mislabeling them as Adaptive.

### 6.3 Same-seed repeatability

Run the exact POST body again:

```powershell
$run2 = Invoke-RestMethod -Method Post -ContentType "application/json" -Body $runBody -Uri "http://127.0.0.1:8000/api/traffic/network-experiments"
```

Ignoring run ID/creation timestamp, `scenario`, `fixed`, `adaptive`, `cooperative`, `comparison`, and `comparisons` should repeat exactly for the same topology, signal config, zones and request.

### 6.4 Persistence / retrieval / CSV / delete

```powershell
$runId = $run1.data.run_id
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/traffic/network-experiments?limit=20" | ConvertTo-Json -Depth 10
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/traffic/network-experiments/$runId" | ConvertTo-Json -Depth 18
Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/traffic/network-experiments/$runId/export.csv" -OutFile ".\v027_network_experiment.csv"
```

Confirm CSV contains Fixed, Adaptive and Cooperative fields, including `cooperative_coordination_action`, and the response preserves `X-Request-ID`.

Restart the backend and reopen the stored result. Delete one disposable run and confirm unrelated runtime data remains untouched.

### 6.5 Negative validation

Confirm these fail cleanly without storing a valid result:

- missing/disabled `link_id` → `ATL-TRAFFIC-013`;
- cooperation lookahead below 1 or above 60;
- max extension below 0 or above 20;
- min incoming vehicles below 1 or above 20.

## 7. Inherited regression

Re-run representative V026/V025/V024/V022/V021 checks: independent network transfer, ranked scenarios, protected phase timing, single-junction Simulation Lab, topology/decision context, occupancy vs flow, tracking/counting lines, camera receiver/simulation, dataset/training/models/settings/logs, atomic persistence and serial polling.

Existing `/api/traffic/experiments` behavior must remain unchanged.

## 8. Interpretation / safety

Confirm documentation/UI/API do not imply:

- live cross-camera identity matching;
- measured/learned road travel time;
- emergency priority;
- general N-intersection live cooperation;
- guaranteed cooperative performance improvement;
- public-road readiness, authority or safety certification.

V027 cooperation exists only in isolated synthetic network experiments.

## 9. Repository / ZIP checks

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL"
git diff --check
git status --short
```

From `AI_Traffic_Light`:

```powershell
python .\scripts\validate_patch_zip.py <V027-patch.zip>
```

Compare ZIP members with the supplied manifest. Only explicit owner acceptance may change `passed_baseline`.

## V028 focused pedestrian-aware network test

```powershell
& $py .\scripts\test_pedestrian_aware_network_simulation.py
```

Then run the inherited V027 network regression as well. For API acceptance, run one `POST /api/traffic/network-experiments` with a configured two-intersection link and confirm four modes share the same arrival fingerprint; `pedestrian_aware_cooperative` should contain pedestrian-awareness events/metrics and `comparisons.pedestrian_aware_cooperative_vs_cooperative`. Verify emergency priority remains false in the four retained pre-emergency modes; then run the V029 emergency checks below.

## V029 focused emergency-priority network test

Run from `AI_Traffic_Light/`:

```powershell
python .\scripts\test_network_simulation_experiments.py
python .\scripts\test_pedestrian_aware_network_simulation.py
python .\scripts\test_emergency_priority_network_simulation.py
```

The V029 focused regression must confirm:

- the retained V027 cooperation and V028 pedestrian-aware regressions still pass;
- the real emergency-priority method stays inside phase minimum/maximum/cycle bounds;
- active simulated pedestrian crossing occupancy yields an explicit emergency-priority denial;
- protected progression requests do not skip phase order;
- one configured emergency event is identical in `emergency_baseline_cooperative` and `emergency_priority_cooperative`;
- the emergency baseline reports `emergency_priority_active: false`;
- the priority mode reports priority evaluations/grants and downstream preparation;
- lifecycle evidence contains activation, source departure and downstream arrival, and contains clear/recovery when the event completes during the run;
- same seed/config repeats all six mode results exactly except run metadata;
- CSV contains emergency status/role/decision/action/ETA/applied columns.

### API acceptance example

Use a duration comfortably longer than the emergency activation time:

```powershell
$body = @{
  duration_seconds = 180
  density = "normal"
  seed = 29029
  sample_interval_seconds = 2
  profile = $null
  label = "V029 emergency acceptance"
  link_id = "A_to_B"
  transfer_share_percent = 70
  cooperation_lookahead_seconds = 12
  cooperation_max_extension_seconds = 5
  cooperation_min_incoming_vehicles = 1
  pedestrian_max_wait_seconds = 30
  pedestrian_crossing_clearance_seconds = 6
  pedestrian_clearance_reserve_seconds = 3
  emergency_event_enabled = $true
  emergency_event_at_seconds = 45
  emergency_vehicle_type = "ambulance"
  emergency_priority_lookahead_seconds = 20
  emergency_priority_max_extension_seconds = 8
} | ConvertTo-Json

$run = Invoke-RestMethod -Method Post -ContentType "application/json" -Body $body -Uri "http://127.0.0.1:8000/api/traffic/network-experiments"
$run.data.scenario | ConvertTo-Json -Depth 12
$run.data.emergency_baseline_cooperative.network_metrics.emergency | ConvertTo-Json -Depth 8
$run.data.emergency_priority_cooperative.network_metrics.emergency | ConvertTo-Json -Depth 8
$run.data.comparisons.emergency_priority_vs_emergency_baseline | ConvertTo-Json -Depth 12
```

Acceptance checks:

1. `scenario.comparison` contains six modes in the documented order.
2. The two emergency modes contain equal `emergency_event` objects.
3. Event provenance is `simulated_configured_emergency_event`; `detector_claimed` is false and confidence is null.
4. Baseline priority counts remain zero.
5. Priority mode records grant/deny/defer events as applicable and downstream preparation before B arrival when inside lookahead.
6. No timing event violates configured phase/cycle bounds or skips protected phase order.
7. Active crossing denial can be reproduced by the focused regression even if the selected random API run does not naturally align the emergency with a crossing.
8. If both matched emergency vehicles clear, the emergency comparison exposes available source/destination/total-travel deltas; otherwise it explicitly marks those deltas unavailable.
9. Stored run read/list/delete/CSV remain functional.
10. No live emergency recognition or public-road-control claim appears in the UI/API/docs.

After focused checks, run the normal complete-repository validation including Python compilation, backend tests, live API smoke, frontend typecheck/build, `scripts/check_structure.py`, and `git diff --check`.
