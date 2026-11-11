# Patch 0_5_37 — Mirror 3D signal posts with camera views

Candidate `0_5_37`, previous `0_5_36`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

Camera B/C/D mirror the agents and image coordinates, but the two 3D signal posts previously remained at Camera A's fixed positions. Reuse the canonical source-point transform for both posts so they follow the same horizontal/vertical mirroring as the live scene. Add deterministic coverage for all four camera transforms and wiring to both rendered posts.

No backend, signal behavior, API, camera image, capture, region-editing, or ESP behavior changes. Run `python scripts/test_v0515_3d_simulation.py`, frontend typecheck/build, structure and offline regressions. On Windows run `& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate`; visually confirm all four views. Owner PASS is required before changing the accepted baseline.
