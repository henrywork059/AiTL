# Local Testing Notes (V024)

V024 / `0_2_4` is the current candidate. V023 / `0_2_3` is the previous candidate; V022 / `0_2_2` remains the owner-confirmed passed baseline because V023 was not explicitly accepted. Automated checks do not promote V024.

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
version: 0_2_4
previous_version: 0_2_3
passed_baseline: 0_2_2
```

Do not use `git clean -fd`. Preserve runtime datasets, outputs, models, labels, zones, settings, `config/signal_rules.json`, and all analytics histories.

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

V024-focused maintenance scripts:

```powershell
& $py ".\scripts\test_atomic_json_store.py"
& $py ".\scripts\test_frontend_polling_structure.py"
& $py ".\scripts\test_runtime_settings_logs.py"
& $py ".\scripts\test_zone_traffic_services.py"
& $py ".\scripts\test_model_registry_service.py"
```

V023 signal-rule regression retained:

```powershell
& $py ".\scripts\test_signal_rules_service.py"
```

## 3. Frontend

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL\AI_Traffic_Light\apps\pc-studio\frontend"
npm ci
npm run typecheck
npm run build
npm run dev
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

## 5. V024 manual maintenance + inherited signal-rule checks


1. Confirm visible version is `0_2_4`, previous version is `0_2_3`, and `passed_baseline` is `0_2_2`.
2. Save Settings, restart backend, and confirm the values persist.
3. Save/reset zones and confirm geometry persists; successful operations should not leave shared fixed `.tmp` files.
4. Set/refresh a default model and confirm registry metadata persists. Only test model deletion with a disposable run you intend to remove.
5. Keep Camera Sources / Live AI open during normal use; App-level camera/live-context polling should continue without stacked request bursts if one backend response is slow.
6. Navigate away from Live AI and confirm those page-dependent top-level polls stop.

Then run the inherited V023 functional checks:
7. Start Simulation and open Traffic Logic.
8. Watch a full default cycle and confirm protected order: vehicle green → yellow → all-red → WALK → CLEAR → all-red.
9. Normal Timing: change a base duration, Save, and verify the next/current protected phase uses the saved timing without rapidly skipping phases.
10. Navigate away/restart backend; verify saved signal rules persist.
11. Try invalid timing (`yellow min` below protected lower bound or min > base/max); Save must fail without replacing saved valid config.
12. Fixed mode: adaptive observations/rules do not change configured normal timing.
13. Adaptive mode + loaded model/zones: heavy vehicle queue can extend vehicle green after persistence delay, bounded by max/cycle limits.
14. Heavy/long-wait pedestrian demand can reduce vehicle green, never below configured minimum or time already served.
15. Let observations become unavailable/stale; verify status explains fallback and normal configured timing is used.
16. Confirm short detection dropouts do not immediately erase demand and one-frame spikes do not immediately trigger persistent rules.
17. Confirm cooldown prevents the same adjustment from being repeatedly added every poll.
18. Confirm rule list distinguishes active, suppressed, inactive, and unavailable states with reasons.
19. Test mode: manual waiting pedestrian/vehicle counts affect rules; switching out of Test mode removes manual-only mobility/incident sources.
20. Mobility assistance is clearly labelled Test/manual unless a compatible perception source exists.
21. Trigger Person fallen / incident in Test mode; signal becomes simulated all-red and synthetic vehicles do not proceed.
22. Clear Incident; controller resumes from a protected phase with a fresh timer rather than skipping through elapsed phases.
23. Reset Adaptive State clears pending/cooldown/hysteresis/incident runtime state without deleting saved rules.
24. Use preview buttons; results change without changing the active simulator state.
25. Enable dry-run and verify rule evaluation remains visible while adaptive adjustments do not alter active duration.
26. Decision History records phase/rule/config/reset/incident events; Clear History removes only `outputs/signal_rules/` history.
27. Clear signal history does not delete occupancy/flow history, captures, labels, zones, settings, models, or training data.
28. Recheck Simulation pause: scene and signal clock stay frozen.
29. Recheck V022 tracking/counting-line flow and V021 occupancy analytics.
30. Recheck capture/delete/label/training/model/settings/logs inherited behavior.
31. Confirm no feature connects to physical/public-road traffic-light control.

## 6. Repository/ZIP checks

```powershell
Set-Location "W:\Code Project\AiTL Ptoject\AiTL"
git diff --check
git status --short
```

From `AI_Traffic_Light`, validate the supplied ZIP with `python .\scripts\validate_patch_zip.py <zip>`. Compare its member list with the supplied manifest. Only explicit owner acceptance may promote V024.
