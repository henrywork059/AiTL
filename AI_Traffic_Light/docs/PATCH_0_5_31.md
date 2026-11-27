# Patch 0_5_31 — Align legacy camera-region structure regression

Candidate `0_5_31`, previous `0_5_30`, accepted baseline `0_5_0`. Branch `feature/interactive-3d-simulation`.

## Reason for follow-up

The `0_5_30` candidate CI passed Python compilation and repository structure checks but failed the offline regression `scripts/test_v0418_camera_region_ui.py`. That historical source-text test expected the old `_advance_vehicles_locked(step)` and `_advance_pedestrians_locked(step)` calls; the new shared-phase optimization correctly calls both helpers with `phase` as a second argument.

## Minimal correction

Update only the existing V0418 regression to inspect `_advance_simulation_locked` for the **single** `_simulation_signal_state_locked()["phase"]` read and the two calls that receive that same phase. The `0_5_30` simulation service changes are retained intact. This is a test-compatibility fix, not a new traffic-signal policy, runtime optimization, API change or physical controller feature.

## Evidence / acceptance

- Root `VERSION`, frontend version mirror, changelog, current handoff/testing/checklist are synchronized as one candidate release bundle.
- Focused: `python scripts/test_v0418_camera_region_ui.py`, `python scripts/test_camera_frame_service.py`, `python scripts/test_signal_rules_service.py`, `python scripts/test_camera_simulation_api.py`, `python scripts/test_v0515_3d_simulation.py`.
- Full GitHub candidate CI: Python compilation, structure, offline regressions, frontend TypeScript typecheck/build.
- Owner Windows acceptance: synthetic phase/agent safety, four simulated camera views, original image capture, unchanged physical ESP preview and explicit PASS. No measured performance speedup is claimed.

## Feature branch pull/test

From a clean repository root, keep `main` and `passed_baseline` untouched:

```powershell
git fetch origin
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```
