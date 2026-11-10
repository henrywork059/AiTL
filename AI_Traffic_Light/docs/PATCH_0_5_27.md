# Patch 0_5_27 — Prevent stale inference publication after stop

Candidate `0_5_27`, previous `0_5_26`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

A slow model inference may outlive the existing two-second stop join; `stop()` clears cached results before this model call finishes. Without a shutdown check, the still-running worker could repopulate stale per-camera detections and publish them to Crosswalk simulation controllers after stop. Retain the prior worker ownership guard and reject these late results when the stop event is already set. A second check prevents observation publication as shutdown begins.

Test: `python scripts/test_v0527_late_inference_shutdown.py` (deterministic blocked model); V0526, V0525, V0524 and inference regressions, structure/CI and owner Windows/ESP validation. No signal policy, AI model, API envelope, data persistence or physical-output changes. This is an unaccepted candidate until explicit owner PASS.
