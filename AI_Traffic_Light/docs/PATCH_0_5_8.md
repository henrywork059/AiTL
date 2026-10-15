# Patch 0_5_8 — AI pages and drag-connected crossing network

**Candidate:** `0_5_8`; **previous:** `0_5_7`; **owner-accepted baseline:** `0_5_0`.

## Changes

- Camera Settings and Camera Diagnostics now precede the **AI** group in navigation.
- The existing `live_ai` route is shown as **Camera AI Preview**, displaying only real camera/model inference. Without a camera, it shows a no-frame message rather than mock counts. The former model-management sidebar and implicit model auto-loading are replaced with read-only preview status and a session confidence slider.
- The existing `model_registry` route becomes **AI Models** in the AI group. Reuse existing model registry and inference endpoints to list, load, set default and delete model runs; also support unload. Persistent default confidence is saved through the existing `/api/settings/runtime` PUT. No new model storage or speculative controls.
- Network edge connections are created by dragging from a numbered label on one crossing to a numbered label on another. A temporary line follows the pointer and valid targets highlight; release on an invalid point cancels. Keyboard activation of two edge labels provides an accessible alternative. Saved lines attach to actual edge label centers. The existing crossing-title dragging, Save network action, backend schema, validation, and existing saved connections remain intact.
- No new dependencies; no backend/firmware/signal-control changes. Frontend grouping reuses existing routes and components.

## Validate

Run `& ".\AI_Traffic_Light\scripts\update_test_run.ps1"` from the repository root with **full tests**. Verify sidebar order, AI preview real/no-camera states, model selection/default/confidence persistence, Network edge-to-edge drag/cancel/keyboard/save-reload, existing physical/simulated camera flows and junction advanced configuration. Frontend TypeScript/Vite build, Windows runtime and owner PASS are pending.
