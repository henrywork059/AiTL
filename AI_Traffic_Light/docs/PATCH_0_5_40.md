# Patch 0_5_40 — Bounded camera upload integrity

Candidate `0_5_40`, previous `0_5_39`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

**Audit finding:** The feature branch's `upload_camera_frame()` used `await request.body()`, accumulating an unlimited HTTP upload before `CameraFrameService.store_upload()` could enforce its 8 MiB cap. This is a memory-exhaustion risk despite the existing size validation. The accepted main-side `0_5_29` change already implements the correct streaming bound; port only those necessary route lines instead of duplicating upload logic.

**Fix:** Read `request.stream()` incrementally, count bytes, raise the existing HTTP 413 `CAMERA_FRAME_TOO_LARGE` error at the first over-limit chunk, and only join the accepted chunks before passing them to the unchanged frame service. Preserve request IDs, API success/error envelopes, actual image validation, simulated signals and ESP transport.

**Validation:** `python scripts/test_v0540_camera_upload_stream_limit.py` tests chunk order, exact 8 MiB boundary, early abort and no service call on rejected data. Run focused existing camera regressions, structure, offline suite, frontend typecheck/build and owner Windows `& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate`. CI PASS does not imply owner PASS. Additional camera image-decoding hardening is separately scoped; do not claim it is implemented by this patch.
