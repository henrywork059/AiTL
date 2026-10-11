# PATCH_0_3_18 — Dedicated Camera Settings page

Version: `0_3_18`  
Previous candidate: `0_3_17`  
Passed baseline: `0_3_11` (unchanged, pending owner PASS)

## Scope

- New dedicated navigation route for camera setup and monitoring. Saved ESP32-CAM profiles are added by LAN IP and source ID, selected with a dropdown, previewed through the existing backend MJPEG relay, and configured with saved OV2640 and target FPS settings.
- Camera Sources remains the simulation/legacy input surface. Physical stream controls and camera diagnostics are shown in Camera Settings.
- Live preview restarts its browser connection on source switch and never presents a simulation/stale frame as live ESP input.
- No new API, device firmware, dependency, registry, AI inference pipeline, or public-road signal control.

## Risks and verification

- Check UI source switching during background streams and simulation activation, offline ESP state, settings persistence, and stream stop/restart.
- Static wiring regression: `python scripts/test_camera_settings_page_structure.py`.
- Owner runs Windows `scripts/update_test_run.ps1` and confirms real camera streaming. Agent-side GitHub edit does not establish hardware PASS.
