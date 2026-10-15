# Patch 0_5_5 — Fix obsolete camera/region regression expectations

Candidate `0_5_5`; previous candidate `0_5_4`; owner-accepted stable baseline `0_5_0`.

## Changes

- Refresh `test_camera_settings_page_structure.py`: verify paired simulation-camera save with `nextSimulationPair`, default-concealed simulator tools, filtered saved cameras, and effective ESP-only form selection. Continue checking camera API sharing, connection/stream workflow and source previews.
- Refresh `test_v0418_camera_region_ui.py`: verify camera-side toggle selection resets the old Region Editor polygon selection before switching camera sides, preventing edits against the wrong view.
- Production frontend/backend, saved cameras/regions, signal logic and hardware are deliberately unchanged. This candidate fixes obsolete assertions rather than rewriting functional code to match them.

## Validation

The next Windows updater run should include a **full** offline regression pass (omit `-ChangedTests`) and frontend typecheck/build, live backend smoke, and Region Editor/Camera Settings visual acceptance. Local runner and physical ESP testing remain pending; owner confirmation required before PASS.
