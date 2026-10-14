# PATCH_0_3_25 — Startup regression assertion repair

Version: `0_3_25`  
Previous candidate: `0_3_24`  
Passed baseline: `0_3_11` (unchanged)

## Scope

- Correct Camera Settings and Crosswalks static regressions to check membership of required page IDs in `CAMERA_POLL_PAGES` instead of assuming specific adjacency with Dataset Capture.
- Preserve camera settings, simulation, crosswalk region editor, junction-edge mapping, runtime data, frontend/backend services and updater unchanged.

## Verification

- Confirmed old adjacency assertions fail against current `App.tsx`, while independent membership checks succeed and both Camera Settings/Crosswalks routes remain wired.
- Owner still needs to run both edited regressions and Windows `update_test_run.ps1 -ChangedTests` launcher, then check the Camera Settings, Crosswalks and Junction Network UI before PASS.
