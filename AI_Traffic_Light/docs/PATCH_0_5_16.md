# Patch 0_5_16 — Crosswalk 3D regression assertion repair

**Branch:** `feature/interactive-3d-simulation` | **Candidate:** `0_5_16` | **Previous:** `0_5_15` | **Accepted baseline:** `0_5_0`.

## Failure observed

The user's Windows `update_test_run.ps1 -SkipUpdate` run on `0_5_15` passed compilation, project structure and the preceding backend/camera regressions but stopped at `scripts/test_crosswalks_frontend_structure.py` line 50. Its legacy assertion required a 2D MJPEG query parameter (`source_id=${encodeURIComponent(sourceId)}`) that was deliberately removed when simulated Region Editor previews switched to `SimulationCamera3D`.

## Minimal fix

Only update that stale structure test: check the conditional use of the selected 3D simulation source, the aligned Edit regions mode, and retention of MJPEG for physical ESP cameras. Do not restore the obsolete 2D URL or change runtime modules, camera AI, Region Editor, traffic signals, or network coordination.

## Validation

The updated assertions were checked against the current source; focused Crosswalk test wiring was verified at 12/12 source-level checks. Full Python regression execution, frontend TypeScript/Vite build, smoke/startup and live visual behavior on Windows still require owner verification. This is a **candidate**, not a PASS or accepted baseline.

**User test (PowerShell at repository root):** fetch and fast-forward the feature branch, then run `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -SkipUpdate`. Preserve the feature branch; do not run the `main`-pulling default updater.
