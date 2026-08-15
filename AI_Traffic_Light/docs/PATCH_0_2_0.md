# Patch 0_2_0 — Camera-aligned zones and capture lifecycle

## Baseline and version

- New candidate: V020 / `0_2_0`.
- Previous version: `0_1_7`.
- Passed baseline: `0_1_7` (owner-confirmed working before this patch).

## Implemented changes

### Capture deletion

- Added `DELETE /api/dataset/captures/{capture_id}`.
- Dataset Capture can delete the latest capture.
- Dataset Review can delete the selected capture.
- Deletion removes the raw image, paired metadata, and optional manual-label document.
- Removal is staged through same-filesystem renames before final cleanup to reduce partial-delete risk.
- Managed YOLO dataset status is returned after deletion so a previous build can be marked stale.
- Added stable `ATL-DATASET-007` for deletion failures.

### Camera-aligned Zone Editor

- Zone Editor now uses the current `/api/camera/frame` receiver/simulation image as its background.
- Camera status is polled while Zone Editor is active.
- The camera image maps into the existing validated 1280×720 zone reference coordinates, preserving the current traffic-counting contract.

### Live AI zone overlay

- Persisted zone polygons are scaled from 1280×720 reference coordinates into the active camera/detection frame resolution.
- Live AI adds a **Show zones** visibility toggle.
- Zone overlays and YOLO boxes share the same non-interactive SVG overlay so they remain aligned with the displayed frame.

### Compact simulated traffic signal

- Live AI now shows a small traffic signal in the top-right corner of the image.
- It reflects the current simulation-only phase (`vehicle_green`, `vehicle_yellow`, pedestrian phases, or all-red).
- It is a visualization only and is not connected to real traffic hardware.

## Compatibility

V017 convergence monitoring, patience-based early stopping, persistent settings, real logs, persistent zones, live zone counting, Traffic Logic, capture/label/train, Model Registry, and live inference remain in scope.

## Validation focus

Run `scripts/test_dataset_capture_delete.py`, the existing camera/training/zone/settings/API tests, structure check, frontend TypeScript/build checks, and the manual V020 checklist in `docs/TEST_READY_CHECKLIST.md`.
