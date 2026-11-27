# Patch 0_5_29 — Simulation camera mirror-render optimization

**Candidate:** `0_5_29` | **Previous:** `0_5_28` | **Accepted baseline:** `0_5_0` | **Branch:** `feature/interactive-3d-simulation`

## Code optimization

The simulation renderer already produces a 1280 × 720 BGR canvas before encoding the canonical PNG. Previously, the first request for each of the three alternate simulated cameras decoded this same PNG independently to produce the flipped view. `CameraFrameService` now retains and reuses the rendered canvas for these views, eliminating up to three redundant decodes per tick when all three alternate views are requested.

The render cache is bounded to one current tick (approximately 2.6 MiB) and cleared on simulation reset, stop and resume. Existing view-specific PNG caching remains intact. The canonical image, flipped pixel orientation, frame metadata, 3D scene coordinates, AI input contract, routes, safety phases, real ESP streaming and physical-output restrictions are unchanged. Runtime performance improvement has not been benchmarked.

## Tests and acceptance

- `python scripts/test_camera_frame_service.py`: prohibit `cv2.imdecode` during first-time mirrored view generation, check exact expected flipped pixels and verify cache release.
- `python scripts/test_camera_simulation_api.py` and `python scripts/test_v0515_3d_simulation.py`: camera control/3D scene regressions.
- Candidate CI: Python compilation, structure/version validation, full offline regression suite, frontend typecheck and build.
- Owner Windows/hardware: check all four synthetic views, pause/resume and density changes, captured source images and unchanged ESP preview. Explicit PASS is necessary to accept the candidate.

## Feature-branch pull and test

The normal runner updates `main`, so from a **clean** local repository root:

```powershell
git fetch origin
git switch feature/interactive-3d-simulation
git pull --ff-only origin feature/interactive-3d-simulation
& ".\AI_Traffic_Light\scripts\update_test_run.ps1" -SkipUpdate
```

No merge to `main`, hardware actuation or accepted-baseline promotion is included.
