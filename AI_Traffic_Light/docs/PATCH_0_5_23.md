# Patch 0_5_23 — Accessible 3D view controls

Candidate `0_5_23`, previous `0_5_22`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

The existing 3D viewport supports keyboard orbit/tilt, zoom and view reset with a visible focus indicator. This is a view-only enhancement: simulator agents, image-coordinate regions, AI detections and ESP camera feeds are untouched.

Focused source regression: `scripts/test_v0523_3d_keyboard.py`. Existing 3D simulation and camera source regressions plus TypeScript/build are required. The user must validate keyboard focus, pointer orbit and the Region Editor on Windows. No hardware behavior is affected.
