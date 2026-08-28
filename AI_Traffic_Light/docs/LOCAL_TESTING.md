# Local Testing Notes (V032)

V032 / `0_3_2` is the current unaccepted candidate. V031 / `0_3_1` is the previous candidate and V024 / `0_2_4` remains the owner-confirmed passed baseline. Automated checks never promote a candidate.

## 1. Safe update

Stop backend/frontend first.

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL"
git status --short
git pull --ff-only origin main
Get-Content .\AI_Traffic_Light\VERSION
```

Expected after V032 is uploaded:

```text
version: 0_3_2
previous_version: 0_3_1
passed_baseline: 0_2_4
```

Do not use `git clean -fd`. Preserve datasets, outputs, models, labels, runtime config/history and local environments.

## 2. Backend dependencies / compile / structure

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light"
$py = ".\apps\pc-studio\backend\.venv\Scripts\python.exe"

& $py -m pip install -r ".\apps\pc-studio\backend\requirements.txt"
& $py -m pip install -r ".\apps\pc-studio\backend\requirements-training.txt"

& $py -m compileall ".\apps\pc-studio\backend\app" ".\scripts"
& $py ".\scripts\check_structure.py"
```

## 3. V032 focused test

```powershell
& $py ".\scripts\test_remote_camera_pull.py"
```

It must verify private-LAN host validation, frame ingestion through CameraFrameService, simulation pause/resume and worker shutdown.

## 4. Full non-live regression

```powershell
$tests = Get-ChildItem ".\scripts\test_*.py" |
    Where-Object { $_.Name -ne "test_backend_smoke.py" }

foreach ($test in $tests) {
    Write-Host "`n===== RUNNING $($test.Name) =====" -ForegroundColor Cyan
    & $py $test.FullName
    if ($LASTEXITCODE -ne 0) { throw "TEST FAILED: $($test.Name)" }
}
```

This includes inherited camera/simulation, dataset/training/inference, zones, occupancy/tracking/flow, signal rules, single-junction experiments and V027–V031 network/evidence tests.

## 5. Frontend

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\apps\pc-studio\frontend"
npm ci
npm run typecheck
npm run build
npm run dev
```

Camera Sources should show an ESP IP field, source ID field, Connect/Reconnect/Disconnect controls, remote status and the existing simulation controls.

## 6. Backend + smoke

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

Health/smoke/version surfaces should report `0_3_2` and preserve request IDs.

## 7. Physical ESP32-CAM acceptance

Use the already-working stock Arduino `CameraWebServer` sketch.

1. Open Serial Monitor at 115200.
2. Record the ESP IP from `Camera Ready! Use 'http://...'`.
3. Verify in a browser:
   - `http://<ESP-IP>/capture`
   - `http://<ESP-IP>:81/stream`
4. Open PC Studio → Camera Sources.
5. Enter the ESP IP (no `http://`) and keep source ID `esp32_cam_01`.
6. Press Connect.
7. Confirm remote status becomes connected and ESP frame count increases.
8. Confirm `/api/camera/status` shows the physical ESP source and a fresh frame.
9. Open Live AI. If a model is loaded, confirm inference uses the physical camera image.
10. Open Dataset Capture and save a physical ESP frame.
11. Start built-in simulation. Confirm remote status reports paused for simulation and synthetic frames take over.
12. Stop simulation. Confirm physical ESP frames resume without reconnecting.
13. Disconnect. Confirm the worker stops; the last frame may remain visible until stale/replaced.
14. Try `8.8.8.8`; connection must be rejected as an invalid camera source.

## 8. Regression semantics

Confirm existing raw upload still works:

```text
POST /api/camera/frame?source_id=<id>
```

Confirm simulation, dataset, inference, zones, traffic logic, analytics and network experiments show no regression.

## 9. Repository / packaging

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL"
git diff --check
git status --short
```

Patch archives must contain only changed source/docs/tests under `AI_Traffic_Light/` and exclude datasets, outputs, models, environments, node_modules, dist and caches.

Only explicit owner acceptance may change `passed_baseline`.
