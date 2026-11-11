# Patch 0_5_35 — Distinct 3D vehicles and pedestrian reentry

Candidate `0_5_35`, previous `0_5_34`, accepted baseline `0_5_0`; branch `feature/interactive-3d-simulation`.

Use the existing source-of-truth synthetic simulator and CSS perspective component. Assign deterministic car, SUV, van and bus types with proportional widths at initialization; preserve agent count, directions, spacing, existing signal movement/queue logic and 2D capture semantics. Give each type distinct 3D cabin proportions, windows and lighting without adding a rendering dependency.

Refine pedestrian figures with varied hair/skin/clothing. Apply the established large-position-change reentry guard to canonical pedestrian Y before the camera transform, preventing the same off-screen respawn tween already fixed for vehicles. Normal movement must remain interpolated.

Regression: `python scripts/test_v0515_3d_simulation.py` (including Node wrap cases), `python scripts/test_v0418_camera_region_ui.py`, offline suite, structure and frontend typecheck/build. Windows owner check: `& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate` after pulling the feature branch. Verify safe vehicle/pedestrian phase behavior, all four camera views, region editor, original synthetic images, and physical camera. CI is not owner PASS.
