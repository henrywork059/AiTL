# Patch 0_5_36 — Layout regression compatibility

Candidate `0_5_36`, previous `0_5_35`, accepted baseline `0_5_0`, branch `feature/interactive-3d-simulation`.

V0535 introduced car/SUV/van/bus actors, but the old `test_simulation_frame_layout.py` asserted that every synthetic vehicle was a car, failing offline CI before frontend checks. Replace only that obsolete assertion with a four-class set check. Keep existing source-frame pixel, no-metadata and no-signal-lamp checks unchanged. No application, API, signal or hardware code changed.

Validation: `python scripts/test_simulation_frame_layout.py`, `python scripts/test_v0515_3d_simulation.py`, `python scripts/test_v0418_camera_region_ui.py`, structure/full offline CI, TypeScript typecheck and build. Windows owner validation: `& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate`; CI PASS does not imply owner PASS.
