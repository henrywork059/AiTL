# Patch 0_5_18 — Interactive 3D status panel nullability

**Branch:** `feature/interactive-3d-simulation` | **Candidate:** `0_5_18` | **Previous:** `0_5_17` | **Accepted baseline:** `0_5_0`.

## Confirmed issue

Frontend typecheck reported three TS18047 errors because the status panel checked `activeScene` but read countdown and object totals from the separately nullable `scene` variable.

## Minimal repair

Read those values from `activeScene`, the exact scene already guarded by the panel's conditional. This is a null-safety correction with no backend, signal-policy, camera-input, or physical-output change.

## Validation

Run frontend `npm run typecheck` and `npm run build`, then the focused 3D simulation, camera-frame/API, Crosswalk and project-structure regressions. Windows startup, live camera/region editing, physical ESP preview, and owner PASS remain required. Do not merge into `main` or change `passed_baseline` without explicit owner PASS.

**Windows command (PowerShell at repository root):** `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate`
