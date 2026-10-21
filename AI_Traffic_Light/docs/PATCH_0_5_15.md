# Patch 0_5_15 — Interactive 3D simulation previews

**Branch:** `feature/interactive-3d-simulation` | **Candidate:** `0_5_15` | **Previous:** `0_5_14` | **Accepted baseline:** `0_5_0`.

## Implemented

- All **live synthetic-camera 2D preview surfaces** now use the existing interactive 3D renderer: Camera Settings, Camera Sources, Crosswalk Side A/B previews, Crosswalk Region Editor, Camera AI Preview, and Dataset Capture.
- The 3D scene reads the actual running simulated vehicle and pedestrian coordinates plus virtual signal state through the existing read-only scene API. All saved simulation camera IDs (Pair 1 A/B, Pair 2 C/D) use their correct source orientation, with source-frame mirrors applied to agent coordinates.
- Camera AI Preview projects its existing 2D source-frame detection rectangles and physical-region polygons onto the simulated 3D ground plane. This is a visualization, **not** new 3D recognition or tracking; the actual AI counts and detector output are unchanged.
- Crosswalk Region Editor uses a 3D scene in a **fixed top-down coordinate-aligned edit mode**. The existing draggable quadrilateral vertices stay in the 1280×720 source-image coordinate system, preserving saved polygon geometry and accurate AI counting for both mirrored sides.
- Dataset Capture displays the live 3D synthetic scene while continuing to save the canonical synthetic 2D image for real detector training/labeling. The interface states this distinction explicitly.
- Reuse the same CSS perspective renderer, serial polling utility, backend service and camera registry. No new dependencies, controller, storage, signal-policy changes, or physical hardware outputs.

## Scope boundaries

This replaces **live simulated camera pictures**, not unrelated 2D charts/forms, Network topology diagrams, real ESP footage or already-captured training photographs. The latter are genuine source-image artifacts, not 3D model data. The simulated renderer offers interactive orbit, zoom and top view; its editor variant restricts projection to preserve exact polygon coordinates. Camera detection boxes are image-space overlays drawn on the world plane, not 3D bounding boxes. All simulated camera coordinates still originate from the 2D traffic simulation and are rendered in a synthetic 3D presentation, not a measured 3D digital twin.

## Validation / handoff

Focused source-level checks can verify every affected view, read-only API wiring, source mirror handling, editor alignment, and preservation of image/ESP paths. Full local Python regression suite, `npm run typecheck`, `npm run build`, Windows startup/smoke and visual region-drag checks must still be executed before owner PASS. Use `-SkipUpdate` when running the existing Windows helper on the feature branch; a normal helper call pulls `main` and will refuse the feature branch.
