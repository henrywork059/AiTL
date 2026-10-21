# Patch 0_5_15 — Interactive 3D simulation-camera preview

**Branch:** `feature/interactive-3d-simulation` | **Candidate:** `0_5_15` | **Previous:** `0_5_14` | **Accepted baseline:** `0_5_0`.

## Implemented

- Replace the selected simulated camera's MJPEG display in **Camera Settings → Selected camera live preview** with an interactive 3D perspective of the **same running simulation agents**. The Camera Sources simulation preview also uses this view while simulation tools are visible.
- A read-only scene projection on the existing CameraFrameService returns current vehicle positions/sizes/directions, pedestrian positions, phase, signal indications, frame number, density and paused status for each of the four saved simulation camera IDs. It does not copy simulation state into a second controller.
- New `GET /api/camera/simulation/scene?source_id=...` uses the normal request-ID envelope; invalid physical/unknown source IDs yield 422, stopped simulation yields 409.
- Browser preview uses a self-contained CSS 3D/perspective scene with orbit drag, touch, wheel zoom, zoom slider, top view and reset. Four source IDs get different default vantage angles. It refreshes through the existing single-flight polling utility.
- Preserve underlying 2D simulation PNG/MJPEG, AI/capture frames, camera AI inference, all real ESP camera previews, signal safety logic, and camera-aligned Crosswalk Region Editor images. No new frontend dependency or data storage.

## Scope/limitations

This is **interactive 3D presentation of the live 2D-world simulator**. It is not a photorealistic engine or calibrated 3D reconstruction of physical cameras. A/B/C/D are preset viewing angles of the shared simulation world; their rendered pixels are **not** interchangeable with the existing mirrored 2D frame coordinates. Therefore region editing and image-coordinate AI overlays deliberately remain on canonical 2D images. No real hardware light actuation.

## Validation

Run `python scripts/test_v0515_3d_simulation.py`, existing camera frame/multi-camera tests, frontend TypeScript/Vite build and normal Windows owner runner on the feature branch without checking out main. Confirm Camera Settings selects Pair 1 and Pair 2, the 3D view moves/pauses with simulation, scene orientation/reset/zoom works, and ESP & region editor still show normal 2D images. Windows app validation and owner PASS are pending.
