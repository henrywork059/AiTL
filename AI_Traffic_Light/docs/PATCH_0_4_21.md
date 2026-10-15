# Patch 0_4_21 — Add second saved simulation camera pair

Candidate `0_4_21`; previous candidate `0_4_20`; owner-accepted baseline `0_4_14`.

## Minimal architecture extension

The original synchronized simulated Pair 1 (`simulation_camera` + `simulation_camera_b`) is unchanged. New Pair 2 (`simulation_camera_c` + `simulation_camera_d`) can be saved from Camera Settings when Pair 1 exists. All four saved identities use the same existing camera registry, selection API, per-source MJPEG, and crosswalk-camera dropdowns.

`POST /api/camera/remote/simulation` defaults to Pair 1 for compatibility; optional `?pair=2` creates Pair 2. Deleting a simulation camera deletes **only its pair**, and does not disable a different still-selected simulation pair. Frame rendering caches each output view by source ID, keeping the same frame number and safety-controlled simulation clock.

Camera C is a horizontally mirrored view of the original synthetic scene; D is the vertical mirror of C. This provides distinct perspectives but is **not a second independent simulated crossing, traffic model or controller**. No road-signal policy or camera ESP transport changes.

## Test and recovery notes

Existing `test_remote_camera_multi.py` now tests Pair 2 creation/reload/selection, deleting either pair without disrupting the other and preserving saved ESP cameras. `test_camera_frame_service.py` verifies all four source views. `test_v0421_second_simulation_pair.py` checks API and frontend wiring. All still require actual Windows execution.

Use the existing no-manual-edit runner:

```powershell
& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -ChangedTests
```
