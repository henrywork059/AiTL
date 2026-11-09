# Patch 0_5_19 — Distinct ambulance observation confirmation

**Branch:** `feature/interactive-3d-simulation` | **Candidate:** `0_5_19` | **Previous:** `0_5_18` | **Accepted baseline:** `0_5_0`.

Emergency route confirmation now uses fresh, region-eligible ambulance detections from actual camera source frames. A frame is counted once using source ID, source frame number, frame timestamp and active model. Two distinct positive frames must span at least 1,000 ms by their observation timestamps. Repeated polling, a change from an unrelated camera, and synchronized views of the same event cannot manufacture confirmation.

Evidence is discarded when observations are unavailable or stale, camera coverage is incomplete, the active model changes, or the same source reports a newer negative frame. Source frames must include a valid non-negative frame number. Existing route opt-in, movement conflict checks, 30-second request expiry, protected pedestrian/amber/all-red transitions, and `hardware_actuation_enabled: false` are preserved.

## Validation

The deterministic emergency regressions use fixed service clocks and timestamped source frames; no sleeps or physical output are involved. Run `python scripts/test_v0519_emergency_evidence.py` and `python scripts/test_v0512_emergency_corridor.py`, plus the repository runner on Windows:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

Windows startup, owner-side regression runner, any connected ESP/camera observation, and owner PASS remain pending. Do not merge into `main` or change the accepted baseline without explicit owner confirmation.
