# Local Testing Notes (V022)

V022 / `0_2_2` is the current candidate, explicitly requested after V021 / `0_2_1`. V021 is the previous candidate and was not separately promoted; the owner-confirmed passed baseline remains V017 / `0_1_7`. Automated checks do not promote V022.

## 1. Update safely

Stop the backend/frontend first. From the repository root:

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL"
git status --short
git pull --ff-only origin main
Get-Content .\AI_Traffic_Light\VERSION
```

Expected release fields:

```text
version: 0_2_2
previous_version: 0_2_1
passed_baseline: 0_1_7
```

Do not run `git clean -fd`. Preserve untracked datasets, captures, labels, models, occupancy history, flow history, settings, and other runtime data.

## 2. Backend environment and compilation

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light"
$py = ".\apps\pc-studio\backend\.venv\Scripts\python.exe"
& $py -m pip install -r ".\apps\pc-studio\backend\requirements.txt"
& $py -m pip install -r ".\apps\pc-studio\backend\requirements-training.txt"
& $py -m compileall ".\apps\pc-studio\backend\app" ".\scripts"
& $py ".\scripts\check_structure.py"
```

## 3. Backend service/regression tests

Run all non-live test scripts so V022 is checked together with inherited camera, dataset, training, inference, settings, model, traffic, and simulation behavior:

```powershell
$tests = Get-ChildItem ".\scripts\test_*.py" |
    Where-Object { $_.Name -ne "test_backend_smoke.py" }

foreach ($test in $tests) {
    Write-Host "`n===== RUNNING $($test.Name) =====" -ForegroundColor Cyan
    & $py $test.FullName
    if ($LASTEXITCODE -ne 0) { throw "TEST FAILED: $($test.Name)" }
}
```

V022-specific focused scripts include:

```powershell
& $py ".\scripts\test_object_tracking_flow.py"
& $py ".\scripts\test_traffic_history_service.py"
& $py ".\scripts\test_zone_traffic_services.py"
```

## 4. Start backend and run non-destructive live smoke

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

The smoke test checks standard request IDs/envelopes, version agreement, occupancy history, tracking status, flow query, occupancy CSV, and flow CSV. It does not clear runtime histories.

## 5. Frontend validation

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\apps\pc-studio\frontend"
npm ci
npm run typecheck
npm run build
npm run dev
```

Open the Vite URL, normally `http://localhost:5173/`.

## 6. V022 manual tracking/flow checks

1. Confirm visible project/version surfaces report `0_2_2`.
2. Start signal-aware Simulation and load a trained model that detects the synthetic people/vehicles.
3. In Live AI, verify detections can show a `track_id`. Follow several objects for consecutive frames and confirm the ID is stable while the tracker keeps a match.
4. In Zone Editor create a `counting_line`; click exactly two distinct points. Save, navigate away, return, and confirm it persists.
5. Create at least two counting lines at different locations. Confirm they render as lines rather than polygons and remain analytics-only.
6. Open Traffic Analytics → Flow / Tracks. Let simulation/inference run long enough for objects to cross the configured lines.
7. Verify unique vehicle/person passage totals increase when tracked objects cross a line, not on every frame they remain visible.
8. Repeatedly refresh/poll while a source frame is unchanged or simulation is paused. Confirm the same frame does not generate duplicate line events.
9. Verify line direction values match the observed movement: left/right or top/bottom according to the track's dominant motion.
10. Select an existing polygon region such as a pedestrian waiting/counting region. Verify entries/exits appear and exit events contain dwell time.
11. For `pedestrian_waiting`, confirm the flow summary can show average prototype pedestrian wait duration after tracked people exit that zone.
12. Switch Flow scope between all events, individual lines, and individual regions; verify summaries/charts/event rows follow the selected scope.
13. Use the class filter and verify person/vehicle-class event results change appropriately.
14. Export flow CSV and confirm event IDs, timestamps, track IDs, classes, event types, line/region IDs, direction, and dwell fields are represented.
15. Use Clear flow after confirmation. Verify only `outputs/traffic_flow/` event history is cleared; occupancy history, captures, labels, zones, models, training runs, and settings remain intact.
16. Switch back to Occupancy mode. Confirm V021 occupancy charts still represent sampled detections present at each timestamp and do not become unique passage counts.
17. Restart the backend. Confirm persisted flow events still load but active track IDs begin a new tracking session; continuity across restart is intentionally not claimed.
18. Stress the tracker with Busy simulation and note any ID loss/swap under occlusion as a prototype limitation rather than treating it as certified measurement accuracy.

## 7. Inherited regression checks

- Watch at least one complete V021 signal cycle: vehicles obey lanes/stop lines; pedestrians wait/use the zebra crossing; pause freezes scene/signal.
- Recheck camera receiver/simulation density/pause.
- Recheck camera-backed Zone Editor and Live AI saved-zone overlay/Show zones.
- Recheck capture/delete/manual labels/managed dataset.
- Recheck training convergence, patience early stopping, model registry/default/delete, confidence controls, Settings, and Logs.
- Confirm detection/tracking/traffic outputs remain simulation/analytics information only and do not control physical public-road infrastructure.

## 8. Repository/change hygiene

From the complete Git repository:

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL"
git status --short
git diff --check
```

Untracked `datasets/`, `outputs/`, trained models, labels, caches, and local runtime files are not source-patch failures. Do not delete runtime data just to obtain a clean `git status`.

## 9. Patch ZIP validation

From `AI_Traffic_Light`:

```powershell
python .\scripts\validate_patch_zip.py <path-to-v022-patch.zip>
```

Also compare the ZIP manifest with the intended changed-file list. The ZIP validator checks path/integrity/exclusion rules but cannot prove that every included source file actually changed.

Only the owner can mark V022 passed after the required manual checks.
