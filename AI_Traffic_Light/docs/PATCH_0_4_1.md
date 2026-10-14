# Patch 0_4_1 — Crosswalk edges, mirrored simulation pair and page cleanup

Previous release: `0_4_0` (owner-accepted stable baseline). Candidate: `0_4_1` (awaiting PASS).

- Crosswalks: direction-neutral labels 1–4 on schematic; `Assign simulation pair` saves and assigns Side A/Side B. Two MJPEG previews show original and vertically flipped synthetic frames; region editing can select either.
- Cameras: saving simulation adds `simulation_camera` and `simulation_camera_b` atomically and idempotently. Selecting B affects the shared inference/capture source; two camera registrations represent a single synchronized simulation scene, **not** simultaneous two-camera inference.
- Junction Network: edge controls sit outside card bounds; drag remembers the header-pointer offset, preventing initial cursor-centering.
- Navigation: stable Dashboard, Camera Settings and Crosswalks; legacy Camera Sources and Zone Editor hidden but code retained; empty Zones page available; names and redundant status clutter simplified.
- Existing ESP transport and traffic signal policy not changed.

## Validation

Changed regression tests cover pair creation, persistence, vertical flip, preview source, crosswalk structure, navigation, and pointer-offset controls. The complete Windows runner, frontend build and physical ESP behavior need owner validation. Use the existing one-line command:

```powershell
& ".\\AI_Traffic_Light\\scripts\\update_test_run.ps1" -ChangedTests
```
